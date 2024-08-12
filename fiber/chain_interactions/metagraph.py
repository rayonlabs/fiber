"""
Module which syncs the nodes from the metagraph, returns the object and stores
it in hotkey: node

Can then be used to blacklist and verify
"""

import threading
from fiber.chain_interactions import fetch_nodes
import json
from fiber.chain_interactions import models
from substrateinterface import SubstrateInterface
from fiber.logging_utils import get_logger
from fiber import constants as fcst

logger = get_logger(__name__)


class Metagraph:
    """
    A class which handles the syncing of nodes from the metagraph.
    The metagraph refers to the nodes (miners & validators) for a particular sub-network
    """

    def __init__(self, substrate_interface: SubstrateInterface, netuid: int, load_old_nodes: bool = True) -> None:
        self.substrate_interface = substrate_interface
        self.nodes: dict[str, models.Node] = {}
        self.netuid = netuid
        self.is_in_sync = False
        self.stop_event = threading.Event()
        self.load_old_nodes = load_old_nodes

        # This is mainly to speed up development
        if load_old_nodes:
            self.load_nodes()
            if len(self.nodes) > 0:
                self.is_in_sync = True

    def periodically_sync_nodes(self) -> None:
        logger.info("Periodically syncing nodes...")

        # This is here in the case of loading nodes initially.
        # Don't move into the while loop, lest we sync after
        # a stop event
        if self.is_in_sync:
            logger.info("Metagraph is in sync, waiting 5 mins... 💤")
            self.stop_event.wait(60 * 5)

        while not self.stop_event.is_set():
            self.sync_nodes()
            self.is_in_sync = True
            if self.is_in_sync:
                logger.info("Metagraph is in sync, waiting 5 mins... 💤")
                self.stop_event.wait(60 * 5)

    def sync_nodes(self) -> None:
        logger.info("Syncing nodes...")
        nodes = fetch_nodes.get_nodes_for_netuid(self.substrate_interface, self.netuid)
        self.nodes = {node.hotkey: node for node in nodes}
        logger.info(f"✅ Successfully synced {len(self.nodes)} nodes!")

    def save_nodes(self) -> None:
        logger.info(f"Saving {len(self.nodes)} nodes")
        if self.load_old_nodes:
            if len(self.nodes) == 0:
                logger.warning("No nodes to save!")
                return

            logger.info(f"Saving {len(self.nodes)} nodes")
            nodes_as_dict = {hotkey: node.model_dump() for hotkey, node in self.nodes.items()}
            with open(fcst.SAVE_NODES_FILEPATH, "w") as f:
                json.dump(nodes_as_dict, f)
        else:
            logger.warning(f"Loading old nodes is not enabled, so I wont save the {len(self.nodes)} nodes I have")

    def load_nodes(self) -> None:
        logger.info(f"Loading nodes from {fcst.SAVE_NODES_FILEPATH}")
        try:
            with open(fcst.SAVE_NODES_FILEPATH, "r") as f:
                raw_nodes: dict[str, dict] = json.load(f)
        except FileNotFoundError:
            return

        self.nodes = {hotkey: models.Node(**node) for hotkey, node in raw_nodes.items()}

    def shutdown(self) -> None:
        self.stop_event.set()
        self.save_nodes()
