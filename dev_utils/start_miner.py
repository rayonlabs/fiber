import os

from dotenv import load_dotenv

load_dotenv("dev.env")  # Important to load this before importing anything else!

from fiber.logging_utils import get_logger
from fiber.miner import server
from fiber.miner.endpoints.subnet import factory_router as get_subnet_router
from fiber.miner.middleware import configure_extra_logging_middleware

logger = get_logger(__name__)

app = server.factory_app(debug=True)

app.include_router(get_subnet_router())


if os.getenv("ENV", "dev").lower() == "dev":
    configure_extra_logging_middleware(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=7999)

    # Remember to fiber-post-ip to whatever testnet you are using!
