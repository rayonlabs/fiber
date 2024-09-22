import logging
import os

from colorama import Back, Fore, Style, init
from loguru import logger

init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Back.WHITE,
    }

    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            levelname_color = self.COLORS[levelname] + Style.BRIGHT + levelname + Style.RESET_ALL
            record.levelname = levelname_color

        message = super().format(record)

        color = self.COLORS.get(record.levelname, Fore.WHITE)
        message = message.replace("$RESET", Style.RESET_ALL)
        message = message.replace("$BOLD", Style.BRIGHT)
        message = message.replace("$COLOR", color)
        message = message.replace("$BLUE", Fore.BLUE + Style.BRIGHT)

        return message


# NOTE: Pm2 hates this (colours aren't great), why?
def get_logger(name: str):
    logger.remove()
    mode: str = os.getenv("ENV", "dev").lower()
    log_level = "DEBUG" if mode != "prod" else "INFO"
    logger.add(sink=lambda msg: print(msg), level=log_level)
    logger.info(f"Logging mode is {log_level}")
    return logger.bind(name=name.split(".")[-1])
