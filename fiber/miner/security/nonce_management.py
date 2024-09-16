import time
from fiber.miner.core import miner_constants as mcst


class NonceManager:
    def __init__(self) -> None:
        self._nonces: dict[str, float] = {}
        self.TTL: int = 60 * 2

    def add_nonce(self, nonce: str) -> None:
        self._nonces[nonce] = time.time() + self.TTL

    def nonce_is_valid(self, nonce: str) -> bool:
        # Check for collision
        if nonce in self._nonces:
            return False
    
        # If nonce isn't the right format, don't add it to self._nonces to prevent abuse
        try:
            if int(nonce) > 10 ** 10:
                raise ValueError()
        except ValueError:
            return False

        # Nonces, even invalid ones, can only be used once.
        self.add_nonce(nonce)

        # Check for recency
        current_time_ns = time.time_ns()
        try:
            timestamp_ns = int(nonce.split("_")[0])
        except (ValueError, IndexError):
            return False

        if current_time_ns - timestamp_ns >  mcst.NONCE_WINDOW_NS:
            return False  # What an Old Nonce

        if timestamp_ns - current_time_ns > mcst.NONCE_WINDOW_NS:
            return False  # That nonce is from the distant future, and will be suspectible to replay attacks

        return True

    def cleanup_expired_nonces(self) -> None:
        current_time = time.time()
        expired_nonces: list[str] = [nonce for nonce, expiry_time in self._nonces.items() if current_time > expiry_time]
        for nonce in expired_nonces:
            del self._nonces[nonce]
