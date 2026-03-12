from __future__ import annotations

import logging
from pathlib import Path

from app.config import Settings


def _build_formatter() -> logging.Formatter:
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def configure_logging(settings: Settings) -> None:
    root_logger = logging.getLogger()
    if getattr(root_logger, "_ai_content_factory_ready", False):
        return

    root_logger.setLevel(logging.INFO)
    formatter = _build_formatter()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    log_file = Path(settings.logs_dir) / "app.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.handlers.clear()
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
    root_logger._ai_content_factory_ready = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

