from typing import TypedDict
from pydantic import BaseModel
from cryptography.fernet import Fernet

class Node(BaseModel):
    hotkey: str
    coldkey: str
    node_id: int
    incentive: float
    netuid: int
    stake: float
    trust: float
    vtrust: float
    updated: float
    ip: str
    ip_type: int
    port: int
    protocol: int = 4
    fernet: Fernet | None = None
    symmetric_key_uuid: str | None = None

    model_config = {
        "arbitrary_types_allowed": True
    }

class ParamWithTypes(TypedDict):
    name: str
    type: str