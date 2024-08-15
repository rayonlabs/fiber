from fiber.miner.core import configuration
from fiber.miner.core.models.config import Config
from fastapi import Depends, Request, HTTPException


def get_config() -> Config:
    return configuration.factory_config()


async def blacklist_low_stake(request: Request, config: Config = Depends(get_config)):
    metagraph = config.metagraph

    hotkey = request.headers.get("hotkey")
    if not hotkey:
        raise HTTPException(status_code=400, detail="Hotkey header missing")

    node = metagraph.nodes.get(hotkey)
    if not node:
        raise HTTPException(status_code=403, detail="Hotkey not found in metagraph")

    if node.stake <= config.min_stake_threshold:
        raise HTTPException(status_code=403, detail="Insufficient stake")
