from typing import TypedDict
from pydantic import BaseModel


class Node(BaseModel):
    hotkey: str
    coldkey: str
    node_id: int
    incentive: float
    netuid: int
    stake: float
    trust: float
    vtrust: float
    ip: str
    ip_type: int
    port: int
    protocol: int = 4


class ParamWithTypes(TypedDict):
    name: str
    type: str