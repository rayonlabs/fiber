import asyncio

from fiber.chain import interface, metagraph
from fiber.chain.fetch_nodes import get_nodes_for_netuid
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


async def main():
    substrate = interface.get_substrate(subtensor_network="test")

    # First option: use the Metagraph class
    mg = metagraph.Metagraph(substrate=substrate, netuid=176)
    mg.sync_nodes()
    logger.info(f"Found nodes: {mg.nodes}")

    # OR - use the fetch_nodes function
    nodes = get_nodes_for_netuid(substrate=substrate, netuid=176)
    logger.info(f"Found nodes: {nodes}")


if __name__ == "__main__":
    asyncio.run(main())
