from dataclasses import dataclass

import httpx
from substrateinterface import Keypair

from fiber.chain.metagraph import Metagraph


@dataclass
class Config:
    keypair: Keypair
    metagraph: Metagraph
    min_stake_threshold: float
    httpx_client: httpx.AsyncClient
