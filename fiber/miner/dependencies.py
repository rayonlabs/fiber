from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from fiber import constants as cst, utils
from fiber.logging_utils import get_logger
from fiber.miner.core import configuration
from fiber.miner.core.models.config import Config
from fiber.chain import signatures

logger = get_logger(__name__)


def get_config() -> Config:
    return configuration.factory_config()


async def verify_signature(request: Request, config: Config = Depends(get_config)):
    hotkey = request.headers.get("hotkey")
    if not hotkey:
        logger.debug("Hotkey header missing in verify_signature")
        raise HTTPException(status_code=400, detail="Hotkey header missing")

    signature = request.headers.get("signature")
    if not signature:
        logger.debug("Signature header missing")
        raise HTTPException(status_code=400, detail="Signature header missing")

    if not signatures.verify_signature(
        message=utils.construct_message_from_payload(await request.body()),
        ss58_address=hotkey,
        signature=signature,
    ):
        raise HTTPException(
            status_code=401,
            detail="Oi, invalid signature, you're not who you said you were!",
        )


async def blacklist_low_stake(request: Request, config: Config = Depends(get_config)):
    metagraph = config.metagraph

    hotkey = request.headers.get("hotkey")
    if not hotkey:
        logger.debug("Hotkey header missing in blacklist_low_stake")
        raise HTTPException(status_code=400, detail="Hotkey header missing")

    node = metagraph.nodes.get(hotkey)
    if not node:
        raise HTTPException(status_code=403, detail="Hotkey not found in metagraph")

    if node.stake < config.min_stake_threshold:
        logger.debug(f"Node {hotkey} has insufficient stake of {node.stake} - minimum is {config.min_stake_threshold}")
        raise HTTPException(status_code=403, detail=f"Insufficient stake of {node.stake} ")


async def verify_nonce(request: Request, config: Config = Depends(get_config)):
    nonce = request.headers.get(cst.NONCE)
    if not nonce:
        logger.debug("Nonce header missing!")
        raise HTTPException(status_code=400, detail="Nonce header missing")

    hotkey = request.headers.get(cst.HOTKEY)
    signature = request.headers.get(cst.SIGNATURE)

    if not signature:
        logger.debug("Signature header missing!")
        raise HTTPException(status_code=400, detail="Signature header missing")

    if not hotkey:
        logger.debug("Hotkey header missing!")
        raise HTTPException(status_code=400, detail="Hotkey header missing")

    if not signatures.verify_signature(
        message=nonce,
        ss58_address=hotkey,
        signature=signature,
    ):
        logger.debug("Badly signed nonce!")
        raise HTTPException(
            status_code=401,
            detail="Oi, invalid signature, you're not who you said you were!",
        )

    if not config.encryption_keys_handler.nonce_manager.nonce_is_valid(nonce):
        logger.debug("Nonce is not valid!")
        raise HTTPException(
            status_code=401,
            detail="Oi, that nonce is not valid!",
        )


class NoncePayload(BaseModel):
    nonce: str
