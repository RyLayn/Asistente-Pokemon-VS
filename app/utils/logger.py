"""Configuración centralizada de *logging* para toda la aplicación."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.utils.paths import cache_dir

_CONFIGURED = False
_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """Inicializa el logging raíz una sola vez (consola + fichero rotatorio)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(level)
    formatter = logging.Formatter(_FORMAT)

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    root.addHandler(stream)

    try:
        log_file = cache_dir() / "app.log"
        file_handler = RotatingFileHandler(
            log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # Si no se puede escribir el log no debe romper la aplicación.
        pass

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger nombrado, garantizando que el logging esté listo."""
    setup_logging()
    return logging.getLogger(name)
