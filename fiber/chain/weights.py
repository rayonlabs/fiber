import time
from functools import wraps
from typing import Any, Callable

from scalecodec import ScaleType
from substrateinterface import Keypair, SubstrateInterface
from tenacity import retry, stop_after_attempt, wait_exponential

from fiber import constants as fcst
from fiber.chain.chain_utils import format_error_message
from fiber.chain.interface import get_substrate
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)
def _query_subtensor(
    substrate: SubstrateInterface,
    name: str,
    block: int | None = None,
    params: int | None = None,
) -> ScaleType:
    try:
        return substrate.query(
            module="SubtensorModule",
            storage_function=name,
            params=params,  # type: ignore
            block_hash=(None if block is None else substrate.get_block_hash(block)),  # type: ignore
        )
    except Exception:
        # Should prevent SSL errors
        substrate = get_substrate(subtensor_address=substrate.url)
        raise


def _get_hyperparameter(
    substrate: SubstrateInterface,
    param_name: str,
    netuid: int,
    block: int | None = None,
) -> list[int] | int | None:
    subnet_exists = getattr(
        _query_subtensor(substrate, "NetworksAdded", block, [netuid]),  # type: ignore
        "value",
        False,
    )
    if not subnet_exists:
        return None
    return getattr(
        _query_subtensor(substrate, param_name, block, [netuid]),  # type: ignore
        "value",
        None,
    )


def _blocks_since_last_update(substrate: SubstrateInterface, netuid: int, node_id: int) -> int | None:
    current_block = substrate.get_block_number(None)  # type: ignore
    last_updated = _get_hyperparameter(substrate, "LastUpdate", netuid)
    assert not isinstance(last_updated, int), "LastUpdate should be a list of ints"
    if last_updated is None:
        return None
    return current_block - int(last_updated[node_id])


def _min_interval_to_set_weights(substrate: SubstrateInterface, netuid: int) -> int:
    weights_set_rate_limit = _get_hyperparameter(substrate, "WeightsSetRateLimit", netuid)
    assert isinstance(weights_set_rate_limit, int), "WeightsSetRateLimit should be an int"
    return weights_set_rate_limit


def _normalize_and_quantize_weights(node_ids: list[int], node_weights: list[float]) -> tuple[list[int], list[int]]:
    if len(node_ids) != len(node_weights) or any(uid < 0 for uid in node_ids) or any(weight < 0 for weight in node_weights):
        raise ValueError("Invalid input: length mismatch or negative values")
    if not any(node_weights):
        return [], []
    scaling_factor = fcst.U16_MAX / max(node_weights)

    node_weights_formatted = []
    node_ids_formatted = []
    for node_id, node_weight in zip(node_ids, node_weights):
        if node_weight > 0:
            node_ids_formatted.append(node_id)
            node_weights_formatted.append(round(node_weight * scaling_factor))

    return node_ids_formatted, node_weights_formatted


def _log_and_reraise(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Exception in {func.__name__}: {str(e)}")
            raise

    return wrapper


def _can_set_weights(substrate: SubstrateInterface, netuid: int, validator_node_id: int) -> bool:
    blocks_since_update = _blocks_since_last_update(substrate, netuid, validator_node_id)
    min_interval = _min_interval_to_set_weights(substrate, netuid)
    if min_interval is None:
        return True
    return blocks_since_update is not None and blocks_since_update > min_interval


def _send_weights_to_chain(
    substrate: SubstrateInterface,
    keypair: Keypair,
    node_ids: list[int],
    node_weights: list[float],
    netuid: int,
    version_key: int = 0,
    wait_for_inclusion: bool = False,
    wait_for_finalization: bool = False,
) -> tuple[bool, str | None]:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.5, min=2, max=5),
        reraise=True,
    )
    @_log_and_reraise
    def _set_weights():
        with substrate as si:
            rpc_call = si.compose_call(
                call_module="SubtensorModule",
                call_function="set_weights",
                call_params={
                    "dests": node_ids,
                    "weights": node_weights,
                    "netuid": netuid,
                    "version_key": version_key,
                },
            )
            extrinsic_to_send = si.create_signed_extrinsic(call=rpc_call, keypair=keypair, era={"period": 5})

            response = si.submit_extrinsic(
                extrinsic_to_send,
                wait_for_inclusion=wait_for_inclusion,
                wait_for_finalization=wait_for_finalization,
            )

            if not wait_for_finalization and not wait_for_inclusion:
                return True, "Not waiting for finalization or inclusion."
            response.process_events()

            if response.is_success:
                return True, "Successfully set weights."

            return False, format_error_message(response.error_message)

    return _set_weights()


def set_node_weights(
    substrate: SubstrateInterface,
    keypair: Keypair,
    node_ids: list[int],
    node_weights: list[float],
    netuid: int,
    validator_node_id: int,
    version_key: int = 0,
    wait_for_inclusion: bool = False,
    wait_for_finalization: bool = False,
    max_attempts: int = 1,
) -> bool:
    node_ids_formatted, node_weights_formatted = _normalize_and_quantize_weights(node_ids, node_weights)

    # Fetch a new substrate object to reset the connection
    substrate = get_substrate(subtensor_address=substrate.url)

    weights_can_be_set = False
    for attempt in range(1, max_attempts + 1):
        if not _can_set_weights(substrate, netuid, validator_node_id):
            logger.info(logger.info(f"Skipping attempt {attempt}/{max_attempts}. Too soon to set weights. Will wait 30 secs..."))
            time.sleep(30)
            continue
        else:
            weights_can_be_set = True
            break

    if not weights_can_be_set:
        logger.error("No attempt to set weightsmade. Perhaps it is too soon to set weights!")
        return False

    logger.info("Attempting to set weights...")
    success, error_message = _send_weights_to_chain(
        substrate,
        keypair,
        node_ids_formatted,
        node_weights_formatted,
        netuid,
        version_key,
        wait_for_inclusion,
        wait_for_finalization,
    )

    if not wait_for_finalization and not wait_for_inclusion:
        logger.info("Not waiting for finalization or inclusion to set weights. Returning immediately.")
        return success

    if success:
        if wait_for_finalization:
            logger.info("✅ Successfully set weights and finalized")
        elif wait_for_inclusion:
            logger.info("✅ Successfully set weights and included")
        else:
            logger.info("✅ Successfully set weights")
    else:
        logger.error(f"❌ Failed to set weights: {error_message}")

    substrate.close()
    return success
