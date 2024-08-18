import json
from typing import Any

import httpx
from fiber import constants as bcst
from cryptography.fernet import Fernet
from fiber.chain_interactions.models import Node
from fiber.logging_utils import get_logger

import aiohttp
from typing import AsyncGenerator

logger = get_logger(__name__)


def _get_headers(
    symmetric_key_uuid: str, validator_ss58_address: str
) -> dict[str, str]:
    return {
        # TODO: Evauluate content type
        "Content-Type": "application/octet-stream",
        bcst.SYMMETRIC_KEY_UUID: symmetric_key_uuid,
        bcst.SS58_ADDRESS: validator_ss58_address,
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
    symmetric_key_uuid: str,
    endpoint: str,
    timeout: int = 10,
):
    headers = _get_headers(symmetric_key_uuid, validator_ss58_address)
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
    fernet: Fernet,
    symmetric_key_uuid: str,
    endpoint: str,
    payload: dict[str, Any],
    timeout: int = 10,
) -> httpx.Response:
    headers = _get_headers(symmetric_key_uuid, validator_ss58_address)
    encrypted_payload = fernet.encrypt(json.dumps(payload).encode())
    response = await httpx_client.post(
        data=encrypted_payload,
        timeout=timeout,
        headers=headers,
        url=server_address + endpoint,
    )
    return response


async def make_streamed_post(
    session: aiohttp.ClientSession,
    server_address: str,
    validator_ss58_address: str,
    fernet: Fernet,
    symmetric_key_uuid: str,
    endpoint: str,
    payload: dict[str, Any],
    timeout: int = 10,
) -> AsyncGenerator[str, None]:
    headers = _get_headers(symmetric_key_uuid, validator_ss58_address)

    encrypted_payload = fernet.encrypt(json.dumps(payload).encode())

    try:
        async with session.post(
            url=server_address + endpoint,
            data=encrypted_payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            response.raise_for_status()
            async for line in response.content.iter_any():
                yield line.decode("utf-8")
    except aiohttp.ClientResponseError as e:
        logger.error(f"Client Response Error details: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise