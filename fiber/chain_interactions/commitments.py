from enum import Enum
from typing import TypeAlias

from pydantic import BaseModel
from scalecodec import ScaleType
from substrateinterface import SubstrateInterface, Keypair
from tenacity import retry, stop_after_attempt, wait_exponential

from fiber.chain_interactions.chain_utils import format_error_message, load_hotkey_keypair
from fiber.chain_interactions.interface import get_substrate_interface
from fiber.constants import FINNEY_TEST_NETWORK


class DataFieldType(Enum):
    RAW = "Raw"
    BLAKE_TWO_256 = "BlakeTwo256"
    SHA_256 = "Sha256"
    KECCAK_256 = "Keccak256"
    SHA_THREE_256 = "ShaThree256"


CommitmentDataField: TypeAlias = tuple[DataFieldType, bytes] | None


class CommitmentQuery(BaseModel):
    fields: list[CommitmentDataField]
    block: int
    deposit: int


class RawCommitment(BaseModel):
    data: bytes
    block: int
    deposit: int


def _serialize_field(field: CommitmentDataField):
    if not field:
        return {str(None): b''}

    data_type, data = field

    if data_type == DataFieldType.RAW:
        serialized_data_type = DataFieldType.RAW.value + str(len(data))
    else:
        serialized_data_type = data_type.value

    return {serialized_data_type: data}


def _deserialize_field(field: dict[str, bytes | str]) -> CommitmentDataField:
    data_type, data = field.items().__iter__().__next__()

    if data_type == str(None):
        return None

    if data_type.startswith(DataFieldType.RAW.value):
        expected_length = int(data_type[len(DataFieldType.RAW.value):])
        data_type = DataFieldType.RAW.value
        data = bytes.fromhex(data[2:])

        if len(data) != expected_length:
            raise ValueError(f"Got commitment raw field expecting {expected_length} data but got {len(data)} data")

    return DataFieldType(data_type), data


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)
def _query_commitment(
    substrate: SubstrateInterface,
    netuid: int,
    hotkey: str,
    block: int | None = None,
) -> ScaleType:
    return substrate.query(
        module="Commitments",
        storage_function="CommitmentOf",
        params=[netuid, hotkey],
        block_hash=(None if block is None else substrate.get_block_hash(block)),  # type: ignore
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1.5, min=2, max=5),
    reraise=True,
)
def set_commitment(
    substrate_interface: SubstrateInterface,
    keypair: Keypair,
    netuid: int,
    fields: list[CommitmentDataField],
    wait_for_inclusion: bool = False,
    wait_for_finalization: bool = False,
) -> tuple[bool, str | None]:
    """
    Commit custom fields to the chain
    Arguments:
        fields: A list of fields as data type to value tuples, for example (DataFieldType.RAW, b'hello world')
    """

    mapped_fields = [[
        _serialize_field(field)
        for field in fields
    ]]

    call = substrate_interface.compose_call(
        call_module="Commitments",
        call_function="set_commitment",
        call_params={
            "netuid": netuid,
            "info": {
                "fields": mapped_fields,
            },
        },
    )

    extrinsic_to_send = substrate_interface.create_signed_extrinsic(call=call, keypair=keypair)

    response = substrate_interface.submit_extrinsic(
        extrinsic_to_send,
        wait_for_inclusion=wait_for_inclusion,
        wait_for_finalization=wait_for_finalization,
    )

    if not wait_for_finalization and not wait_for_inclusion:
        return True, "Not waiting for finalization or inclusion."

    response.process_events()

    if response.is_success:
        return True, "Successfully submitted commitment."

    return False, format_error_message(response.error_message)


def query_commitment(
    substrate: SubstrateInterface,
    netuid: int,
    hotkey: str,
    block: int | None = None,
) -> CommitmentQuery | None:
    """
    Query fields commited to the chain via set_commitment
    return: None if no commitment has been made previously, otherwise CommitmentQuery
    """

    value = _query_commitment(
        substrate,
        netuid,
        hotkey,
        block,
    ).value

    if not value:
        return None

    fields: list[dict[str, bytes]] = value["info"]["fields"]
    mapped_fields = [_deserialize_field(field) for field in fields]

    return CommitmentQuery(
        fields=mapped_fields,
        block=value["block"],
        deposit=value["deposit"],
    )


def publish_raw_commitment(
    substrate_interface: SubstrateInterface,
    keypair: Keypair,
    netuid: int,
    data: bytes,
    wait_for_inclusion: bool = False,
    wait_for_finalization: bool = True,
):
    """
    Helper function for publishing a single raw byte-string to the chain using only one commitment field
    """

    return set_commitment(
        substrate_interface,
        keypair,
        netuid,
        [(DataFieldType.RAW, data)],
        wait_for_inclusion,
        wait_for_finalization
    )


def get_raw_commitment(
    substrate: SubstrateInterface,
    netuid: int,
    hotkey: str,
    block: int | None = None,
) -> RawCommitment | None:
    """
    Helper function for getting single field raw byte-string value after publishing with publish_raw_commitment
    returns: None if publish_raw_commitment has not been called before
    raises: ValueError if set_commitment has been called before with a different data-type
    """

    commitment = query_commitment(substrate, netuid, hotkey, block)
    if commitment and len(commitment.fields):
        field = commitment.fields[0]
    else:
        field = None

    if not field:
        return None

    data_type, data = field

    if data_type != DataFieldType.RAW:
        raise ValueError(
            f"Commitment for {hotkey} in netuid {netuid} is of type {data_type.value} and not {DataFieldType.RAW.value}"
        )

    return RawCommitment(
        data=data,
        block=commitment.block,
        deposit=commitment.deposit,
    )


if __name__ == '__main__':
    keypair = load_hotkey_keypair("wombo-test-wallet", "1")
    subtrate = get_substrate_interface(FINNEY_TEST_NETWORK)

    print(get_raw_commitment(subtrate, 159, keypair.ss58_address))
