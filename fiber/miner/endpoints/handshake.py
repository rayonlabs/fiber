import time
from fastapi import APIRouter, Depends, HTTPException

from fiber.miner.core.configuration import Config
from fiber.miner.core.dependencies import get_config, blacklist_low_stake
from fiber.miner.core.models.encryption import PublicKeyResponse, SymmetricKeyExchange
from fiber.miner.security import signatures
from fiber.miner.security.encryption import get_symmetric_key_b64_from_payload


async def get_public_key(config: Config = Depends(get_config)):
    return PublicKeyResponse(
        public_key=config.encryption_keys_handler.public_bytes.decode(),
        timestamp=time.time(),
        hotkey=config.keypair.ss58_address,
        signature=signatures.sign_message(
            config.keypair,
            signatures.construct_public_key_message_to_sign(),
        ),
    )


async def exchange_symmetric_key(
    payload: SymmetricKeyExchange, config: Config = Depends(get_config), _=Depends(blacklist_low_stake)
):
    if not signatures.verify_signature(
        message=signatures.construct_public_key_message_to_sign(),
        ss58_address=payload.ss58_address,
        signature=payload.signature,
    ):
        raise HTTPException(status_code=401, detail="Oi, invalid signature, you're not who you said you were!")
    if config.encryption_keys_handler.nonce_manager.nonce_is_valid(payload.nonce):
        raise HTTPException(
            status_code=401, detail="Oi, I've seen that nonce before. Don't send me the nonce more than once"
        )

    base64_symmetric_key = get_symmetric_key_b64_from_payload(payload, config.encryption_keys_handler.private_key)
    config.encryption_keys_handler.add_symmetric_key(
        payload.symmetric_key_uuid, payload.ss58_address, base64_symmetric_key
    )

    return {"status": "Symmetric key exchanged successfully"}


def factory_router() -> APIRouter:
    router = APIRouter(tags=["Handshake"])
    router.add_api_route("/public-encryption-key", get_public_key, methods=["GET"])
    router.add_api_route("/exchange-symmetric-key", exchange_symmetric_key, methods=["POST"])
    return router
