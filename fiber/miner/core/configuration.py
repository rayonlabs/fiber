from functools import lru_cache

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

# TODO: Have this path passed in?
load_dotenv()


def _derive_key_from_string(input_string: str, salt: bytes = b"salt_") -> bytes:
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
    chain_network = os.getenv("CHAIN_NETWORK")
    chain_address = os.getenv("CHAIN_ADDRESS")
    load_old_nodes = bool(os.getenv("LOAD_OLD_NODES", True))
    min_stake_threshold = int(os.getenv("MIN_STAKE_THRESHOLD", 1_000))

    substrate_interface = interface.get_substrate_interface(chain_network, chain_address)
    metagraph = Metagraph(substrate_interface=substrate_interface, netuid=netuid, load_old_nodes=load_old_nodes)

    if netuid is None:
        raise ValueError("Must set NETUID env var please x)")

    keypair = chain_utils.load_hotkey_keypair(wallet_name, hotkey_name)

    storage_encryption_key = os.getenv("STORAGE_ENCRYPTION_KEY")
    if storage_encryption_key is None:
        storage_encryption_key = _derive_key_from_string(mcst.DEFAULT_ENCRYPTION_STRING)

    encryption_keys_handler = key_management.EncryptionKeysHandler(nonce_manager, storage_encryption_key)

    return Config(
        encryption_keys_handler=encryption_keys_handler,
        keypair=keypair,
        metagraph=metagraph,
        min_stake_threshold=min_stake_threshold,
    )
