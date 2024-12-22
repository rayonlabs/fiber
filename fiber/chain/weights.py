from functools import wraps
from typing import Any, Callable

from bittensor_commit_reveal import get_encrypted_commit
from substrateinterface import Keypair, SubstrateInterface
from tenacity import retry, stop_after_attempt, wait_exponential

from fiber import constants as fcst
from fiber.chain.chain_utils import format_error_message, query_substrate
from fiber.chain.interface import get_substrate
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


def _log_and_reraise(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Exception in {func.__name__}: {str(e)}")
            raise

    return wrapper


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


def blocks_since_last_update(substrate: SubstrateInterface, netuid: int, node_id: int) -> int:
    substrate, current_block = query_substrate(substrate, "System", "Number", [], return_value=True)
    substrate, last_updated_value = query_substrate(substrate, "SubtensorModule", "LastUpdate", [netuid], return_value=False)
    updated: int = current_block - last_updated_value[node_id].value
    return updated


def min_interval_to_set_weights(substrate: SubstrateInterface, netuid: int) -> int:
    substrate, weights_set_rate_limit = query_substrate(
        substrate, "SubtensorModule", "WeightsSetRateLimit", [netuid], return_value=True
    )
    assert isinstance(weights_set_rate_limit, int), "WeightsSetRateLimit should be an int"
    return weights_set_rate_limit


def can_set_weights(substrate: SubstrateInterface, netuid: int, validator_node_id: int) -> bool:
    blocks_since_update = blocks_since_last_update(substrate, netuid, validator_node_id)
    min_interval = min_interval_to_set_weights(substrate, netuid)
    if min_interval is None:
        return True

    can_set_weights = blocks_since_update is not None and blocks_since_update >= min_interval
    if not can_set_weights:
        logger.error(
            f"It is too soon to set weights! {blocks_since_update} blocks since last update, {min_interval} blocks required."
        )
    return can_set_weights


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
    def _send_weights():
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

    return _send_weights()


def _send_commit_reveal_weights_to_chain(
    substrate: SubstrateInterface,
    keypair: Keypair,
    commit: bytes,
    reveal_round: int,
    netuid: int,
    wait_for_inclusion: bool = False,
    wait_for_finalization: bool = False,
) -> tuple[bool, str | None]:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.5, min=2, max=5),
        reraise=True,
    )
    @_log_and_reraise
    def _send_commit_reveal_weights():
        call = substrate.compose_call(
            call_module="SubtensorModule",
            call_function="commit_crv3_weights",
            call_params={
                "netuid": netuid,
                "commit": commit,
                "reveal_round": reveal_round,
            },
        )
        extrinsic = substrate.create_signed_extrinsic(
            call=call,
            keypair=keypair,
        )

        response = substrate.submit_extrinsic(
            extrinsic=extrinsic,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=wait_for_finalization,
        )

        if not wait_for_finalization and not wait_for_inclusion:
            return True, "Not waiting for finalization or inclusion."

        response.process_events()
        if response.is_success:
            return True, None
        else:
            return False, format_error_message(response.error_message)

    return _send_commit_reveal_weights()


def _set_weights_without_commit_reveal(
    substrate: SubstrateInterface,
    keypair: Keypair,
    node_ids: list[int],
    node_weights: list[float],
    netuid: int,
    version_key: int = 0,
    wait_for_inclusion: bool = False,
    wait_for_finalization: bool = False,
) -> bool:
    logger.info(f"Setting weights for subnet {netuid} with version key {version_key} - no commit reveal...")
    success, error_message = _send_weights_to_chain(
        substrate,
        keypair,
        node_ids,
        node_weights,
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


def _set_weights_with_commit_reveal(
    substrate: SubstrateInterface,
    keypair: Keypair,
    node_ids: list[int],
    node_weights: list[float],
    netuid: int,
    version_key: int = 0,
    wait_for_inclusion: bool = False,
    wait_for_finalization: bool = False,
) -> bool:
    substrate, current_block = query_substrate(substrate, "System", "Number", [], return_value=True)

    substrate, tempo = query_substrate(substrate, "SubtensorModule", "Tempo", [netuid], return_value=True)
    substrate, subnet_reveal_period_epochs = query_substrate(
        substrate, "SubtensorModule", "RevealPeriodEpochs", [netuid], return_value=True
    )

    # Encrypt `commit_hash` with t-lock and `get reveal_round`
    commit_for_reveal, reveal_round = get_encrypted_commit(
        uids=node_ids,
        weights=node_weights,
        version_key=version_key,
        tempo=tempo,
        current_block=current_block,
        netuid=netuid,
        subnet_reveal_period_epochs=subnet_reveal_period_epochs,
    )

    logger.info(f"Committing weights hash {commit_for_reveal.hex()} for subnet {netuid} with " f"reveal round {reveal_round}...")
    success, error_message = _send_commit_reveal_weights_to_chain(
        substrate,
        keypair,
        commit_for_reveal,
        reveal_round,
        netuid,
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


def set_node_weights(
    substrate: SubstrateInterface,
    keypair: Keypair,
    node_ids: list[int],
    node_weights: list[float],
    netuid: int,
    validator_node_id: int,
    version_key: int = 0,
    max_attempts: int = 3,  # DEPRECATED
    wait_for_inclusion: bool = False,
    wait_for_finalization: bool = False,
) -> bool:
    node_ids_formatted, node_weights_formatted = _normalize_and_quantize_weights(node_ids, node_weights)

    # Fetch a new substrate object to reset the connection
    substrate = get_substrate(subtensor_address=substrate.url)

    if not can_set_weights(substrate, netuid, validator_node_id):
        return False

    # NOTE: Sadly this can't be an argument of the function, the hyperparam must be set on chain
    # For it to function properly
    substrate, commit_reveal_enabled = query_substrate(
        substrate,
        "SubtensorModule",
        "CommitRevealWeightsEnabled",
        [netuid],
        return_value=True,
    )

    logger.info(f"Commit reveal enabled hyperparameter is set to {commit_reveal_enabled}")

    if commit_reveal_enabled is False:
        return _set_weights_without_commit_reveal(
            substrate,
            keypair,
            node_ids_formatted,
            node_weights_formatted,
            netuid,
            version_key,
            wait_for_inclusion,
            wait_for_finalization,
        )

    elif commit_reveal_enabled is True:
        return _set_weights_with_commit_reveal(
            substrate,
            keypair,
            node_ids_formatted,
            node_weights_formatted,
            netuid,
            version_key,
            wait_for_inclusion,
            wait_for_finalization,
        )

    else:
        raise ValueError(f"Commit reveal enabled hyperparameter is set to {commit_reveal_enabled}, which is not a valid value")
