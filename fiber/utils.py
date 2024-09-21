import base64
import json

from cryptography.fernet import Fernet

from fiber.logging_utils import get_logger

logger = get_logger(__name__)


def fernet_to_symmetric_key(fernet: Fernet) -> str:
    return base64.urlsafe_b64encode(fernet._signing_key + fernet._encryption_key).decode()


def construct_message_from_payload(body: str | bytes | dict) -> str | None:
    try:
        if isinstance(body, dict):
            return json.dumps(body, sort_keys=True, separators=(",", ":"))
        elif isinstance(body, bytes):
            body_str = body.decode()
        else:
            assert isinstance(body, str)
            body_str = body

        try:
            json_body = json.loads(body_str)
            return json.dumps(json_body, sort_keys=True, separators=(",", ":"))
        except json.JSONDecodeError:
            return body_str
    except Exception as e:
        logger.error(f"Error constructing message from payload: {str(e)}")
        return None
