from typing import Any
from substrateinterface import SubstrateInterface
import scalecodec

from tenacity import retry, stop_after_attempt, wait_exponential

from fiber.chain_interactions import models
from fiber.chain_interactions import chain_utils as chain_utils
from fiber import constants as fcst

import netaddr
from scalecodec.utils.ss58 import ss58_encode
from fiber.chain_interactions import type_registries


def _normalise_u16_float(x: int) -> float:
    return float(x) / float(fcst.U16_MAX)


def _rao_to_tao(rao: float | int) -> float:
    return int(rao) / 10**9


def _get_node_from_neuron_info(neuron_info_decoded: dict) -> models.Node:
    neuron_info_copy = neuron_info_decoded.copy()
    stake_dict = {
        ss58_encode(coldkey, fcst.SS58_FORMAT): _rao_to_tao(stake) for coldkey, stake in neuron_info_copy["stake"]
    }

    return models.Node(
        hotkey=ss58_encode(neuron_info_copy["hotkey"], fcst.SS58_FORMAT),
        coldkey=ss58_encode(neuron_info_copy["coldkey"], fcst.SS58_FORMAT),
        node_id=neuron_info_copy["uid"],
        netuid=neuron_info_copy["netuid"],
        stake=sum(stake_dict.values()),
        incentive=neuron_info_copy["incentive"],
        trust=_normalise_u16_float(neuron_info_copy["trust"]),
        vtrust=_normalise_u16_float(neuron_info_copy["validator_trust"]),
        ip=str(netaddr.IPAddress(int(neuron_info_copy["axon_info"]["ip"]))),
        ip_type=neuron_info_copy["axon_info"]["ip_type"],
        port=neuron_info_copy["axon_info"]["port"],
        protocol=neuron_info_copy["axon_info"]["protocol"],
    )


def _get_nodes_from_vec8(vec_u8: bytes) -> list[models.Node]:
    decoded_neuron_infos = chain_utils.create_scale_object_from_scale_encoding(
        vec_u8, fcst.NEURON_INFO_LITE, is_vec=True
    )
    if decoded_neuron_infos is None:
        return []

    nodes = []
    for decoded_neuron in decoded_neuron_infos:
        node = _get_node_from_neuron_info(decoded_neuron)
        if node is not None:
            nodes.append(node)
    return nodes


def _encode_params(
    substrate_interface: SubstrateInterface,
    call_definition: list[models.ParamWithTypes],
    params: list[Any] | dict[str, Any],
) -> str:
    """Returns a hex encoded string of the params using their types."""
    param_data = scalecodec.ScaleBytes(b"")

    for i, param in enumerate(call_definition["params"]):  # type: ignore
        scale_obj = substrate_interface.create_scale_object(param["type"])
        if isinstance(params, list):
            param_data += scale_obj.encode(params[i])
        else:
            if param["name"] not in params:
                raise ValueError(f"Missing param {param['name']} in params dict.")

            param_data += scale_obj.encode(params[param["name"]])

    return param_data.to_hex()


def _execute_rpc_request(
    substrate_interface: SubstrateInterface,
    method: str,
    data: str,
    block: int | None = None,
) -> dict[str, Any]:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def make_substrate_call() -> dict[str, Any]:
        block_hash = None if block is None else substrate_interface.get_block_hash(block)
        params = [method, data, block_hash] if block_hash else [method, data]

        return substrate_interface.rpc_request(
            method="state_call",
            params=params,
        )

    return make_substrate_call()


def _query_runtime_api(
    substrate_interface: SubstrateInterface,
    runtime_api: str,
    method: str,
    params: list[int] | dict[str, int] | None,
    block: int | None = None,
) -> str | None:
    type_registry = type_registries.get_type_registry()

    call_definition = type_registry["runtime_api"][runtime_api]["methods"][method]

    json_result = _execute_rpc_request(
        substrate_interface=substrate_interface,
        method=f"{runtime_api}_{method}",
        data=(
            "0x"
            if params is None
            else _encode_params(substrate_interface=substrate_interface, call_definition=call_definition, params=params)
        ),
        block=block,
    )

    if json_result is None:
        return None

    return_type = call_definition["type"]

    as_scale_bytes = scalecodec.ScaleBytes(json_result["result"])

    scale_object = chain_utils.create_scale_object_from_scale_bytes(return_type, as_scale_bytes)

    if scale_object.data.to_hex() == "0x0400":
        return None

    return scale_object.decode()


def get_nodes_for_netuid(
    substrate_interface: SubstrateInterface, netuid: int, block: int | None = None
) -> list[models.Node]:
    hex_bytes_result = _query_runtime_api(
        substrate_interface=substrate_interface,
        runtime_api="NeuronInfoRuntimeApi",
        method="get_neurons_lite",
        params=[netuid],
        block=block,
    )
    if hex_bytes_result.startswith("0x"):
        bytes_result = bytes.fromhex(hex_bytes_result[2:])
    else:
        bytes_result = bytes.fromhex(hex_bytes_result)

    nodes = _get_nodes_from_vec8(bytes_result)
    return nodes
