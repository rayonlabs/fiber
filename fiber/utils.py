import base64
from cryptography.fernet import Fernet


def fernet_to_symmetric_key(fernet: Fernet) -> str:
    return base64.urlsafe_b64encode(fernet._signing_key + fernet._encryption_key).decode()
