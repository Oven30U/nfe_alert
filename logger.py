import logging
import os
from pathlib import Path
from typing import Optional


class Logger:
    """Centralized logger for the project"""

    _instance: Optional["Logger"] = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # Get log path from environment or use default
            log_file_path = os.getenv("log_file_path")
            if not log_file_path:
                log_file_path = Path("Estructura-robot/System/logfile.log")

            Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)

            self.logger = logging.getLogger()
            self.logger.setLevel(logging.INFO)

            # File handler
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setLevel(logging.INFO)
            file_format = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_format)

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_format = logging.Formatter("%(levelname)s: %(message)s")
            console_handler.setFormatter(console_format)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

            self._initialized = True

    @classmethod
    def get_logger(cls) -> logging.Logger:
        return cls().logger
