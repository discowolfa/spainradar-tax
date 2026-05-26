import logging
import os
from logging.handlers import RotatingFileHandler

from config import LOG_BACKUP_COUNT, LOG_MAX_BYTES, LOG_PATH


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

    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
