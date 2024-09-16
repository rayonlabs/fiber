import time
from fastapi import APIRouter, Depends

from fiber.miner.core.configuration import Config
from fiber.miner.dependencies import get_config, blacklist_low_stake, verify_nonce, verify_signature
from fiber.miner.core.models.encryption import PublicKeyResponse, SymmetricKeyExchange
from fiber.miner.security.encryption import get_symmetric_key_b64_from_payload
from cryptography.fernet import Fernet


async def get_public_key(config: Config = Depends(get_config)):
    public_key = config.encryption_keys_handler.public_bytes.decode()
    return PublicKeyResponse(
        public_key=public_key,
        timestamp=time.time(),
        hotkey=config.keypair.ss58_address,
    )


async def exchange_symmetric_key(
    payload: SymmetricKeyExchange,
    config: Config = Depends(get_config),
):
    base64_symmetric_key = get_symmetric_key_b64_from_payload(payload, config.encryption_keys_handler.private_key)
    fernet = Fernet(base64_symmetric_key)
    config.encryption_keys_handler.add_symmetric_key(
        uuid=payload.symmetric_key_uuid,
        hotkey_ss58_address=payload.ss58_address,
        fernet=fernet,
    )

    return {"status": "Symmetric key exchanged successfully"}


def factory_router() -> APIRouter:
    router = APIRouter(tags=["Handshake"])
    router.add_api_route("/public-encryption-key", get_public_key, methods=["GET"])
    router.add_api_route(
        "/exchange-symmetric-key",
        exchange_symmetric_key,
        methods=["POST"],
        dependencies=[
            Depends(blacklist_low_stake),
            Depends(verify_signature),
            Depends(verify_nonce),
        ],
    )
    return router
