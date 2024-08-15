import json
from typing import Any

import httpx
from fiber import constants as bcst
from cryptography.fernet import Fernet


def construct_server_address(
    ip: str,
    port: int,
    ip_type: int,
    protocol: int,
    replace_with_docker_localhost: bool = False,
) -> str:
    """
    Currently just supports http4.
    """
    if ip == "0.0.0.1" and replace_with_docker_localhost:
        # CHAIN DOES NOT ALLOW 127.0.0.1 TO BE POSTED. IS THIS
        # A REASONABLE WORKAROUND FOR LOCAL DEV?
        return f"http://host.docker.internal:{port}"
    return f"http://{ip}:{port}"


def get_encrypted_payload(
    validator_ss58_address: str,
    fernet: Fernet,
    symmetric_key_uuid: str,
    endpoint: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    encrypted_payload = fernet.encrypt(json.dumps(payload).encode())

    headers = {
        # TODO: Evauluate content type
        "Content-Type": "application/octet-stream",
        bcst.SYMMETRIC_KEY_UUID: symmetric_key_uuid,
        bcst.SS58_ADDRESS: validator_ss58_address,
    }

    return encrypted_payload, headers


async def make_non_streamed_post(
    httpx_client: httpx.AsyncClient,
    server_address: str,
    validator_ss58_address: str,
    fernet: Fernet,
    symmetric_key_uuid: str,
    endpoint: str,
    payload: dict[str, Any],
    timeout: int = 10,
):
    encrypted_payload, headers = get_encrypted_payload(
        validator_ss58_address=validator_ss58_address,
        fernet=fernet,
        symmetric_key_uuid=symmetric_key_uuid,
        endpoint=endpoint,
        payload=payload,
    )
    response = await httpx_client.post(
        data=encrypted_payload,
        timeout=timeout,
        headers=headers,
        server_address=server_address,
    )
    return response


async def make_streamed_post(
    httpx_client: httpx.AsyncClient,
    server_address: str,
    validator_ss58_address: str,
    fernet: Fernet,
    symmetric_key_uuid: str,
    endpoint: str,
    payload: dict[str, Any],
    timeout: int = 10,
):
    encrypted_payload, headers = get_encrypted_payload(
        server_address=server_address,
        validator_ss58_address=validator_ss58_address,
        fernet=fernet,
        symmetric_key_uuid=symmetric_key_uuid,
        endpoint=endpoint,
        payload=payload,
    )
    response = httpx_client.stream(
        data=encrypted_payload,
        headers=headers,
        timeout=timeout,
        server_address=server_address,
    )
    async for chunk in response.aiter_lines():
        yield chunk
