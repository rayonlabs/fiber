import asyncio

from fiber.chain import chain_utils, interface, metagraph, post_ip_to_chain, weights
from fiber.chain.fetch_nodes import get_nodes_for_netuid
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


async def metagraph_example():
    substrate = interface.get_substrate(subtensor_network="test")

    # First option: use the Metagraph class
    mg = metagraph.Metagraph(substrate=substrate, netuid=176)
    mg.sync_nodes()
    logger.info(f"Found nodes: {mg.nodes}")

    # OR - use the fetch_nodes function [this is better :P]
    nodes = get_nodes_for_netuid(substrate=substrate, netuid=176)
    logger.info(f"Found nodes: {nodes}")


async def set_weights_example():
    substrate = interface.get_substrate(subtensor_network="test")
    nodes = get_nodes_for_netuid(substrate=substrate, netuid=176)
    keypair = chain_utils.load_hotkey_keypair(wallet_name="default", hotkey_name="default")
    validator_node_id = substrate.query("SubtensorModule", "Uids", [176, keypair.ss58_address]).value
    version_key = substrate.query("SubtensorModule", "WeightsVersionKey", [176]).value
    weights.set_node_weights(
        substrate=substrate,
        keypair=keypair,
        node_ids=[node.node_id for node in nodes],
        node_weights=[node.incentive for node in nodes],
        netuid=176,
        validator_node_id=validator_node_id,
        version_key=version_key,
        wait_for_inclusion=True,
        wait_for_finalization=True,
    )

# NOTE this is also a script in /scropts/post_ip_to_chain and you can use it on the cli with fiber-post-ip
async def post_ip_to_chain_example():
    chain_endpoint = None
    subtensor_network = "test"
    wallet_name = "default"
    wallet_hotkey = "default"
    netuid = 176
    external_ip = "0.0.0.1"
    external_port = 8080

    substrate = interface.get_substrate(subtensor_address=chain_endpoint, subtensor_network=subtensor_network)
    keypair = chain_utils.load_hotkey_keypair(wallet_name=wallet_name, hotkey_name=wallet_hotkey)
    coldkey_keypair_pub = chain_utils.load_coldkeypub_keypair(wallet_name=wallet_name)

    success = post_ip_to_chain.post_node_ip_to_chain(
        substrate=substrate,
        keypair=keypair,
        netuid=netuid,
        external_ip=external_ip,
        external_port=external_port,
        coldkey_ss58_address=coldkey_keypair_pub.ss58_address,
    )
    logger.info(f"Post IP to chain: {success}!")


async def main():
    await metagraph_example()
    await set_weights_example()
    await post_ip_to_chain_example()

if __name__ == "__main__":
    asyncio.run(main())
