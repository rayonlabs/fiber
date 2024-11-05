import json
from typing import Any, AsyncGenerator

import httpx

from fiber import Keypair, utils
from fiber import constants as cst
from fiber.chain import signatures
from fiber.chain.models import Node
from fiber.logging_utils import get_logger
from fiber.validator.generate_nonce import generate_nonce

logger = get_logger(__name__)


def _get_headers(validator_ss58_address: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        cst.VALIDATOR_HOTKEY: validator_ss58_address,
    }


def get_headers_with_nonce(
    payload_str: str,
    validator_ss58_address: str,
    miner_ss58_address: str,
    keypair: Keypair,
) -> dict[str, str]:
    nonce = generate_nonce()
    message = utils.construct_header_signing_message(nonce=nonce, miner_hotkey=miner_ss58_address, payload_str=payload_str)
    header_hash = signatures.get_header_hash(message)
    signature = signatures.sign_message(keypair, header_hash)
    # To verify this:
    # Check you can get the header hash from the headers and payload body
    # Then check the hash matches the signature
    return {
        "Content-Type": "application/octet-stream",
        cst.VALIDATOR_HOTKEY: validator_ss58_address,
        cst.MINER_HOTKEY: miner_ss58_address,
        cst.NONCE: nonce,
        cst.SIGNATURE: signature,
        cst.HEADER_HASH: header_hash,
    }


def construct_server_address(
    node: Node,
    replace_with_docker_localhost: bool = False,
    replace_with_localhost: bool = False,
) -> str:
    """
    Currently just supports http4.
    """
    if node.ip == "0.0.0.1":
        # CHAIN DOES NOT ALLOW 127.0.0.1 TO BE POSTED. IS THIS
        # A REASONABLE WORKAROUND FOR LOCAL DEV?
        if replace_with_docker_localhost:
            return f"http://host.docker.internal:{node.port}"
        elif replace_with_localhost:
            return f"http://localhost:{node.port}"
    return f"http://{node.ip}:{node.port}"


async def make_non_streamed_get(
    httpx_client: httpx.AsyncClient,
    server_address: str,
    validator_ss58_address: str,
    endpoint: str,
    timeout: float = 10,
):
    headers = _get_headers(validator_ss58_address)
    logger.debug(f"headers: {headers}")
    response = await httpx_client.get(
        timeout=timeout,
        headers=headers,
        url=server_address + endpoint,
    )
    return response


async def make_non_streamed_post(
    httpx_client: httpx.AsyncClient,
    server_address: str,
    validator_ss58_address: str,
    miner_ss58_address: str,
    keypair: Keypair,
    endpoint: str,
    payload: dict[str, Any],
    timeout: float = 10,
) -> httpx.Response:
    payload_str = json.dumps(payload)
    headers = get_headers_with_nonce(payload_str, validator_ss58_address, miner_ss58_address, keypair)

    response = await httpx_client.post(
        content=payload_str.encode(),  # NOTE: can this be content?
        timeout=timeout,
        headers=headers,
        url=server_address + endpoint,
    )
    return response


async def make_streamed_post(
    httpx_client: httpx.AsyncClient,
    server_address: str,
    validator_ss58_address: str,
    miner_ss58_address: str,
    keypair: Keypair,
    endpoint: str,
    payload: dict[str, Any],
    timeout: float = 10,
) -> AsyncGenerator[bytes, None]:
    payload_str = json.dumps(payload)
    headers = get_headers_with_nonce(payload_str, validator_ss58_address, miner_ss58_address, keypair)

    async with httpx_client.stream(
        method="POST",
        url=server_address + endpoint,
        content=payload_str.encode(),  # NOTE: can this be content?
        headers=headers,
        timeout=timeout,
    ) as response:
        try:
            response.raise_for_status()
            async for line in response.aiter_lines():
                yield line
        except httpx.HTTPStatusError as e:
            await response.aread()
            logger.error(f"HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except Exception:
            # logger.error(f"Unexpected error: {str(e)}")
            # logger.exception("Full traceback:")
            raise
