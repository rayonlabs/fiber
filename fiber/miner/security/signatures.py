import json
from substrateinterface import Keypair
from fiber.logging_utils import get_logger


logger = get_logger(__name__)


def sign_message(keypair: Keypair, message: str) -> str:
    return f"0x{keypair.sign(message).hex()}"


def verify_signature(message: str | None, signature: str, ss58_address: str) -> bool:
    if message is None:
        return False
    try:
        keypair = Keypair(ss58_address=ss58_address)
        return keypair.verify(data=message, signature=signature)
    except ValueError:
        return False


def construct_message_from_payload(body: str | bytes | dict) -> str:
    try:
        if isinstance(body, dict):
            return json.dumps(body, sort_keys=True, separators=(",", ":"))
        elif isinstance(body, bytes):
            body_str = body.decode()
        else:
            body_str = body

        try:
            json_body = json.loads(body_str)
            return json.dumps(json_body, sort_keys=True, separators=(",", ":"))
        except json.JSONDecodeError:
            return body_str
    except Exception as e:
        logger.error(f"Error constructing message from payload: {str(e)}")
        return None
