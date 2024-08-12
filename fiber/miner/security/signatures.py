from substrateinterface import Keypair

 
def sign_message(keypair: Keypair, message: str) -> str:
    return f"0x{keypair.sign(message).hex()}"


def verify_signature(message: str, signature: str, ss58_address: str) -> bool:
    try:
        keypair = Keypair(ss58_address=ss58_address)
        return keypair.verify(data=message, signature=signature)
    except ValueError:
        return False

def construct_public_key_message_to_sign(*args) -> str:
    return "TODO: FIX THIS"