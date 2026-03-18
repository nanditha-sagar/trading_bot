import logging
import sys

LOG_FILE = "bot.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # File handler: logs everything to bot.log
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    # Console handler: only warnings/errors (keeps CLI output clean)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)