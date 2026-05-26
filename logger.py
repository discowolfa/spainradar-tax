import logging
import os

from config import LOG_PATH


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("spainradar_tax")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    directory = os.path.dirname(LOG_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(LOG_PATH)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
