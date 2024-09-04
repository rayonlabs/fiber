from functools import lru_cache

import httpx

from fiber.chain_interactions.metagraph import Metagraph
from fiber.miner.security import nonce_management
from dotenv import load_dotenv
import os
from fiber.miner.core.models.config import Config
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import TypeVar
from fiber.miner.security import key_management
from fiber.miner.core import miner_constants as mcst
from fiber.chain_interactions import chain_utils
from fiber.chain_interactions import interface
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

load_dotenv()


def _derive_key_from_string(input_string: str, salt: bytes = b"salt_") -> str:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(input_string.encode()))
    return key.decode()


@lru_cache
def factory_config() -> Config:
    nonce_manager = nonce_management.NonceManager()

    wallet_name = os.getenv("WALLET_NAME", "default")
    hotkey_name = os.getenv("HOTKEY_NAME", "default")
    netuid = os.getenv("NETUID")
    subtensor_network = os.getenv("SUBTENSOR_NETWORK")
    subtensor_address = os.getenv("SUBTENSOR_ADDRESS")
    load_old_nodes = bool(os.getenv("LOAD_OLD_NODES", True))
    min_stake_threshold = int(os.getenv("MIN_STAKE_THRESHOLD", 1_000))
    refresh_nodes = os.getenv("REFRESH_NODES", "true").lower() == "true"

    assert netuid is not None, "Must set NETUID env var please!"

    if refresh_nodes:
        substrate_interface = interface.get_substrate_interface(subtensor_network, subtensor_address)
        metagraph = Metagraph(
            substrate_interface=substrate_interface,
            netuid=netuid,
            load_old_nodes=load_old_nodes,
        )
    else:
        metagraph = Metagraph(substrate_interface=None, netuid=netuid, load_old_nodes=load_old_nodes)

    keypair = chain_utils.load_hotkey_keypair(wallet_name, hotkey_name)

    storage_encryption_key = os.getenv("STORAGE_ENCRYPTION_KEY")
    if storage_encryption_key is None:
        storage_encryption_key = _derive_key_from_string(mcst.DEFAULT_ENCRYPTION_STRING)

    encryption_keys_handler = key_management.EncryptionKeysHandler(
        nonce_manager, storage_encryption_key, hotkey=hotkey_name
    )

    return Config(
        encryption_keys_handler=encryption_keys_handler,
        keypair=keypair,
        metagraph=metagraph,
        min_stake_threshold=min_stake_threshold,
        httpx_client=httpx.AsyncClient(),
    )
