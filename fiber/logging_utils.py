import os
import sys

from colorama import init
from loguru import logger

init(autoreset=True)


def get_logger(name: str):
    logger.remove()
    mode: str = os.getenv("ENV", "dev").lower()
    log_level = "DEBUG" if mode != "prod" else "INFO"

    log_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | " "{level: <8} | " "{name}:{function}:{line} - " "{message}"

    logger.add(sys.stdout, format=log_format, level=log_level, colorize=False)

    logger.info(f"Logging mode is {log_level}")
    return logger.bind(name=name.split(".")[-1])
