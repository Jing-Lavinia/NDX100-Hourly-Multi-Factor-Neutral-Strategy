import logging
import sys
from pathlib import Path
from . import config

def setup_logger(name="AlphaFactor"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(config.REPORTS_DIR / "backtest_run.log", mode='w')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

logger = setup_logger()