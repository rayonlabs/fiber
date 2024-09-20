import base64
import os
import time

import httpx
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.bindings._rust import openssl as rust_openssl
from cryptography.hazmat.primitives.asymmetric import rsa
from substrateinterface import Keypair

from fiber import constants as bcst
from fiber.logging_utils import get_logger
from fiber.miner.core.models import encryption
from fiber.miner.security import signatures
from fiber.validator.generate_nonce import generate_nonce
from fiber.validator.security.encryption import public_key_encrypt

logger = get_logger(__name__)


async def perform_handshake(
    httpx_client: httpx.AsyncClient,
    server_address: str,
    keypair: Keypair,
) -> tuple[str, str]:
    public_key_encryption_key = await get_public_encryption_key(httpx_client, server_address)

    symmetric_key: bytes = os.urandom(32)
    symmetric_key_uuid: str = os.urandom(32).hex()

    await send_symmetric_key_to_server(
        httpx_client,
        server_address,
        keypair,
        public_key_encryption_key,
        symmetric_key,
        symmetric_key_uuid,
    )

    symmetric_key_str = base64.b64encode(symmetric_key).decode()

    return symmetric_key_str, symmetric_key_uuid


async def get_public_encryption_key(httpx_client: httpx.AsyncClient, server_address: str, timeout: int = 3) -> rsa.RSAPublicKey:
    response = await httpx_client.get(url=f"{server_address}/{bcst.PUBLIC_ENCRYPTION_KEY_ENDPOINT}", timeout=timeout)
    logger.debug(f"Response from {server_address} for {bcst.PUBLIC_ENCRYPTION_KEY_ENDPOINT}: {response.json()}")
    response.raise_for_status()
    data = encryption.PublicKeyResponse(**response.json())
    public_key_pem = data.public_key.encode()
    public_key_encryption_key = rust_openssl.keys.load_pem_public_key(public_key_pem, backend=default_backend())
    assert isinstance(public_key_encryption_key, rsa.RSAPublicKey), "Expected an RSA public key"

    return public_key_encryption_key


async def send_symmetric_key_to_server(
    httpx_client: httpx.AsyncClient,
    server_address: str,
    keypair: Keypair,
    public_key_encryption_key: rsa.RSAPublicKey,
    symmetric_key: bytes,
    symmetric_key_uuid: str,
    timeout: int = 3,
) -> bool:
    payload = {
        "encrypted_symmetric_key": base64.b64encode(public_key_encrypt(public_key_encryption_key, symmetric_key)).decode("utf-8"),
        "symmetric_key_uuid": symmetric_key_uuid,
        "ss58_address": keypair.ss58_address,
        "timestamp": time.time(),
        "nonce": generate_nonce(),
    }

    signature = signatures.sign_message(keypair, signatures.construct_message_from_payload(payload))

    headers = {"hotkey": keypair.ss58_address, "signature": signature}

    response = await httpx_client.post(
        f"{server_address}/{bcst.EXCHANGE_SYMMETRIC_KEY_ENDPOINT}",
        json=payload,
        timeout=timeout,
        headers=headers,
    )
    logger.debug(f"Response from {server_address} for {bcst.EXCHANGE_SYMMETRIC_KEY_ENDPOINT}: {response.json()}")
    response.raise_for_status()
    return response.status_code == 200
