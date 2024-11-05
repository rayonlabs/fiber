from pydantic import BaseModel


class NodeWithFernet(BaseModel):
    hotkey: str
    coldkey: str
    node_id: int
    incentive: float
    netuid: int
    stake: float
    trust: float
    vtrust: float
    last_updated: float
    ip: str
    ip_type: int
    port: int
    protocol: int = 4
