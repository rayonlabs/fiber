"""
TODO:
- INTEGRATE THIS NEW WAY OF DOING THINGS INTO THE SUBNET CODE, BYE BYE SYNAPSES AND DENDRITES
- BIN SIGNING SERVICE, BIN CHAIN NODE, PUT INTRO CONTROL NODE
- CONTROL NODE SHOULD ALSO CHANGE TEH WAY IT SCHEDULES TO SCHEDULE BY TASK NOT BY PARTICIPANT, ABSTRACTS A LOT BETTER THAT WAY
- ALSO JUST THINK ABOUT THE WHOLE PARTICIPANTS, CHECKING THEM OVER ONE HOUR, ETC. IS THERE NOT A MORE CONTINUOUS SATISFYING WAY OF DOING IT?S
- Let client nodes be queried by anyone who signs a message and verifies them
- Write a small package based on fiber for this
- DDOS protection for valis using redis & a banhammer
- Integrate with the vali UI's
- THEN TEST motha
"""

from contextlib import asynccontextmanager
import threading
from fastapi import FastAPI
from fiber.miner.endpoints.handshake import factory_router as handshake_factory_router
from fiber.miner.core import configuration
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


def factory_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = configuration.factory_config()
        metagraph = config.metagraph
        sync_thread = threading.Thread(target=metagraph.periodically_sync_nodes, daemon=True)
        sync_thread.start()

        yield

        logger.info("Shutting down...")

        metagraph.shutdown()
        sync_thread.join()

    app = FastAPI(lifespan=lifespan)



    handshake_router = handshake_factory_router()
    app.include_router(handshake_router)

    return app
