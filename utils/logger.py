"""
utils/logger.py
Logger centralizzato per tutto il sistema META Lead ADS Assistant.
"""

import logging
import os
from datetime import datetime
from config.settings import settings

os.makedirs(settings.logs_dir, exist_ok=True)

log_filename = os.path.join(
    settings.logs_dir,
    f"meta_ads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
