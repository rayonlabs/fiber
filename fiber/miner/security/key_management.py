import base64
from datetime import datetime
import json
import os
import threading
import time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.fernet import Fernet
from fiber.miner.core.models.encryption import SymmetricKeyInfo
from fiber.miner.security.nonce_management import NonceManager
from fiber.miner.core import miner_constants as mcst


class EncryptionKeysHandler:
    def __init__(self, nonce_manager: NonceManager, storage_encryption_key: str):
        self.nonce_manager = nonce_manager
        self.asymmetric_fernet = Fernet(storage_encryption_key)
        self.symmetric_keys_fernets: dict[str, dict[str, SymmetricKeyInfo]] = {}
        self.load_asymmetric_keys()
        self.load_symmetric_keys()

        self._running: bool = True
        self._cleanup_thread: threading.Thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_thread.start()

    def add_symmetric_key(self, uuid: str, hotkey: str, fernet: Fernet) -> None:
        symmetric_key_info = SymmetricKeyInfo.create(fernet)
        if hotkey not in self.symmetric_keys_fernets:
            self.symmetric_keys_fernets[hotkey] = {}
        self.symmetric_keys_fernets[hotkey][uuid] = symmetric_key_info

    def get_symmetric_key(self, hotkey: str, uuid: str) -> SymmetricKeyInfo | None:
        return self.symmetric_keys_fernets.get(hotkey, {}).get(uuid)

    def save_symmetric_keys(self) -> None:
        serializable_keys = {
            hotkey: {
                uuid: {
                    "key": base64.urlsafe_b64encode(
                        key_info.fernet._signing_key + key_info.fernet._encryption_key
                    ).decode(),
                    "expiration_time": key_info.expiration_time.isoformat(),
                }
                for uuid, key_info in keys.items()
            }
            for hotkey, keys in self.symmetric_keys_fernets.items()
        }
        json_data = json.dumps(serializable_keys)
        encrypted_data = self.asymmetric_fernet.encrypt(json_data.encode())

        with open(mcst.SYMMETRIC_KEYS_FILENAME, "wb") as file:
            file.write(encrypted_data)

    def load_symmetric_keys(self) -> None:
        if os.path.exists(mcst.SYMMETRIC_KEYS_FILENAME):
            with open(mcst.SYMMETRIC_KEYS_FILENAME, "rb") as f:
                encrypted_data = f.read()

            decrypted_data = self.asymmetric_fernet.decrypt(encrypted_data)
            loaded_keys: dict[str, dict[str, str]] = json.loads(decrypted_data.decode())

            self.symmetric_keys_fernets = {
                hotkey: {
                    uuid: SymmetricKeyInfo(Fernet(key_data["key"]), datetime.fromisoformat(key_data["expiration_time"]))
                    for uuid, key_data in keys.items()
                }
                for hotkey, keys in loaded_keys.items()
            }

    def _clean_expired_keys(self) -> None:
        for hotkey in list(self.symmetric_keys_fernets.keys()):
            self.symmetric_keys_fernets[hotkey] = {
                uuid: key_info
                for uuid, key_info in self.symmetric_keys_fernets[hotkey].items()
                if not key_info.is_expired()
            }
            if not self.symmetric_keys_fernets[hotkey]:
                del self.symmetric_keys_fernets[hotkey]

    def _periodic_cleanup(self) -> None:
        while self._running:
            self._clean_expired_keys()
            self.nonce_manager.cleanup_expired_nonces()
            time.sleep(65)

    def load_asymmetric_keys(self) -> None:
        # TODO: Allow this to be passed in via env too
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()
        self.public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def close(self) -> None:
        self.save_symmetric_keys()
