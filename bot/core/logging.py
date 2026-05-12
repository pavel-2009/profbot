"""Централизованная настройка логирования."""

import logging


LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """Настроить базовое логирование приложения."""
    logging.basicConfig(level=level, format=LOG_FORMAT)
