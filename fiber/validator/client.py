import json
from typing import Any

import httpx
from fiber import constants as bcst
from cryptography.fernet import Fernet


def get_encrypted_payload(
    server_address: str,
    validator_ss58_address: str,
    fernet: Fernet,
    endpoint: str,
    payload: dict[str, Any],
    symmetric_key_uuid: str,
    timeout: int = 10,
) -> dict[str, Any]:
    encrypted_payload = fernet.encrypt(json.dumps(payload).encode())
    payload = {
        "url": f"{server_address}/{endpoint}",
        "data": encrypted_payload,
        "headers": {
            "Content-Type": "application/octet-stream",
            bcst.SYMMETRIC_KEY_UUID: symmetric_key_uuid,
            bcst.SS58_ADDRESS: validator_ss58_address,
        },
        "timeout": timeout,
    }
    return payload


async def make_non_streamed_post(httpx_client: httpx.AsyncClient, payload: dict[str, Any]):
    async with httpx_client.post(**payload) as response:
        return response


async def make_streamed_post(httpx_client: httpx.AsyncClient, payload: dict[str, Any]):
    async with httpx_client.stream(**payload) as response:
        async for chunk in response.aiter_lines():
            yield chunk
