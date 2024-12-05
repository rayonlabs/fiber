from substrateinterface import SubstrateInterface
from websockets.sync import client as ws_client
from websockets.sync.client import ClientConnection

from fiber import constants as fcst
from fiber.chain import chain_utils, type_registries
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


def _get_chain_endpoint(subtensor_network: str | None, subtensor_address: str | None) -> str:
    if subtensor_network is None and subtensor_address is None:
        raise ValueError("subtensor_network and subtensor_address cannot both be None")

    if subtensor_address is not None:
        logger.info(f"Using chain address: {subtensor_address}")
        return subtensor_address

    if subtensor_network not in fcst.SUBTENSOR_NETWORK_TO_SUBTENSOR_ADDRESS:
        raise ValueError(f"Unrecognized chain network: {subtensor_network}")

    subtensor_address = fcst.SUBTENSOR_NETWORK_TO_SUBTENSOR_ADDRESS[subtensor_network]
    logger.info(f"Using the chain network: {subtensor_network} and therefore chain address: {subtensor_address}")
    return subtensor_address

def get_substrate_from_websocket(websocket: ClientConnection) -> SubstrateInterface:
    address = chain_utils.websocket_to_url(websocket)
    return get_substrate(subtensor_address=address)


def get_substrate(
    subtensor_network: str | None = fcst.FINNEY_NETWORK,
    subtensor_address: str | None = None,
) -> SubstrateInterface:
    if subtensor_address is None and subtensor_network is None:
        raise ValueError("subtensor_address and subtensor_network cannot both be None")

    subtensor_address = _get_chain_endpoint(subtensor_network, subtensor_address)

    logger.info(f"Connecting to websocket with address: {subtensor_address}")

    websocket = ws_client.connect(
        subtensor_address,
        open_timeout=10,
        max_size=2**32,
    )

    type_registry = type_registries.get_type_registry()
    substrate = SubstrateInterface(
        ss58_format=42,
        use_remote_preset=True,
        websocket=websocket,
        type_registry=type_registry,
    )
    logger.info(f"Connected to {subtensor_address}")

    return substrate
