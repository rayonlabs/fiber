from enum import Enum
from typing import TypedDict, TypeAlias

from cryptography.fernet import Fernet
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
    last_updated: float
    ip: str
    ip_type: int
    port: int
    protocol: int = 4
    fernet: Fernet | None = None
    symmetric_key_uuid: str | None = None

    model_config = {"arbitrary_types_allowed": True}


class ParamWithTypes(TypedDict):
    name: str
    type: str


class CommitmentDataFieldType(Enum):
    RAW = "Raw"
    BLAKE_TWO_256 = "BlakeTwo256"
    SHA_256 = "Sha256"
    KECCAK_256 = "Keccak256"
    SHA_THREE_256 = "ShaThree256"


CommitmentDataField: TypeAlias = tuple[CommitmentDataFieldType, bytes] | None


class CommitmentQuery(BaseModel):
    fields: list[CommitmentDataField]
    block: int
    deposit: int


class RawCommitmentQuery(BaseModel):
    data: bytes
    block: int
    deposit: int
