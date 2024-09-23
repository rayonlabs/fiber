import asyncio

from fiber.chain import chain_utils, interface, metagraph, weights
from fiber.chain.fetch_nodes import get_nodes_for_netuid
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


async def metagraph_example():
    substrate = interface.get_substrate(subtensor_network="test")

    # First option: use the Metagraph class
    mg = metagraph.Metagraph(substrate=substrate, netuid=176)
    mg.sync_nodes()
    logger.info(f"Found nodes: {mg.nodes}")

    # OR - use the fetch_nodes function
    nodes = get_nodes_for_netuid(substrate=substrate, netuid=176)
    logger.info(f"Found nodes: {nodes}")


async def set_weights_example():
    substrate = interface.get_substrate(subtensor_network="test")
    nodes = get_nodes_for_netuid(substrate=substrate, netuid=176)
    keypair = chain_utils.load_hotkey_keypair(wallet_name="default", hotkey_name="default")
    validator_node_id = substrate.query("SubtensorModule", "Uids", [176, keypair.ss58_address]).value
    version_key = substrate.query("SubtensorModule", "WeightVersion", [176]).value
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


async def main():
    await metagraph_example()
    await set_weights_example()


if __name__ == "__main__":
    asyncio.run(main())
