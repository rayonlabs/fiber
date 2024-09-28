import base64
from typing import Any

from cryptography.fernet import Fernet

from fiber import SubstrateInterface
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


def fernet_to_symmetric_key(fernet: Fernet) -> str:
    return base64.urlsafe_b64encode(fernet._signing_key + fernet._encryption_key).decode()


def construct_header_signing_message(nonce: str, miner_hotkey: str, symmetric_key_uuid: str) -> str:
    return f"{nonce}:{miner_hotkey}:{symmetric_key_uuid}"


def query_substrate(
    substrate: SubstrateInterface, module: str, method: str, params: list[Any], return_value: bool = True
) -> tuple[SubstrateInterface, Any]:
    try:
        query_result = substrate.query(module, method, params)

        return_val = query_result.value if return_value else query_result

        return substrate, return_val
    except Exception as e:
        logger.error(f"Query failed with error: {e}. Reconnecting and retrying.")

        substrate = SubstrateInterface(url=substrate.url)

        query_result = substrate.query(module, method, params)

        return_val = query_result.value if return_value else query_result

        return substrate, return_val
