import logging
import os
import sys

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


# # NOTE: Pm2 hates this (colours aren't great), why?
# def get_logger(name: str):
#     logger = logging.getLogger(name.split(".")[-1])
#     mode: str = os.getenv("ENV", "prod")
#     logger.setLevel(logging.DEBUG if mode != "prod" else logging.INFO)
#     logger.handlers.clear()

#     format_string = (
#         "$BLUE%(asctime)s.%(msecs)03d$RESET | "
#         "$COLOR$BOLD%(levelname)-8s$RESET | "
#         "$BLUE%(name)s$RESET:"
#         "$BLUE%(funcName)s$RESET:"
#         "$BLUE%(lineno)d$RESET - "
#         "$COLOR$BOLD%(message)s$RESET"
#     )

#     colored_formatter = ColoredFormatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

#     console_handler = logging.StreamHandler(sys.stdout)
#     console_handler.setFormatter(colored_formatter)
#     logger.addHandler(console_handler)

#     logger.debug(f"Mode is {mode}")
#     return logger


def get_logger(name: str):
    logger.remove()
    mode: str = os.getenv("ENV", "dev").lower()
    log_level = "DEBUG" if mode != "prod" else "INFO"

    # Define the log format (all on one line)
    log_format = ("{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                  "{level: <8} | "
                  "{name}:{function}:{line} - "
                  "{message}")

    # Add a new handler with the appropriate log level and format
    logger.add(sys.stdout, format=log_format, level=log_level, colorize=False)

    logger.info(f"Logging mode is {log_level}")
    return logger.bind(name=name.split(".")[-1])
