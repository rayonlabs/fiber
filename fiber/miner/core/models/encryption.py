from datetime import datetime, timedelta
from pydantic import BaseModel
from dataclasses import dataclass
from cryptography.fernet import Fernet


@dataclass
class SymmetricKeyInfo:
    fernet: Fernet
    expiration_time: datetime

    @classmethod
    def create(cls, fernet: Fernet, ttl_seconds: int = 60 * 60 * 5):  # 5 hours
        return cls(fernet, datetime.now() + timedelta(seconds=ttl_seconds))

    def is_expired(self) -> bool:
        return datetime.now() > self.expiration_time


class SymmetricKeyExchange(BaseModel):
    encrypted_symmetric_key: str
    symmetric_key_uuid: str
    ss58_address: str
    timestamp: float
    nonce: str
    signature: str


class PublicKeyResponse(BaseModel):
    public_key: str
    timestamp: float
    hotkey: str
    signature: str
