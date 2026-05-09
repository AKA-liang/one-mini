"""
One-Mini logging — unified logging for all subsystems.

Produces logs to:
  - Console (stderr): ERROR/WARNING for ops visibility
  - File logs/: subsystem-debug logs for diagnostics

Usage:
    from app.logger import get_logger
    logger = get_logger("alibaba1688")
    logger.info("search started", extra={"keyword": "手机壳"})
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

os.makedirs(LOG_DIR, exist_ok=True)

_FORMAT_DETAIL = "%(asctime)s [%(name)s] %(levelname)-5s %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

ROOT_LOGGER_NAME = "one_mini"

_root_logger: logging.Logger | None = None
_initialized = False


def init_logging(level: int = logging.DEBUG, console_level: int = logging.WARNING):
    global _root_logger, _initialized
    if _initialized:
        return

    _root_logger = logging.getLogger(ROOT_LOGGER_NAME)
    _root_logger.setLevel(level)

    # Console handler (stderr) — only warnings and errors
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(console_level)
    console.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s", _DATE_FORMAT))
    _root_logger.addHandler(console)

    # File handler — all levels, rotated
    main_log = os.path.join(LOG_DIR, "one_mini.log")
    file_handler = RotatingFileHandler(main_log, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_FORMAT_DETAIL, _DATE_FORMAT))
    _root_logger.addHandler(file_handler)

    # Per-subsystem log files
    for subsystem in ["backend", "ai_engine", "spiders", "agents", "llm", "redis"]:
        sub_log = os.path.join(LOG_DIR, f"{subsystem}.log")
        sub_handler = RotatingFileHandler(sub_log, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        sub_handler.setLevel(logging.DEBUG)
        sub_handler.setFormatter(logging.Formatter(_FORMAT_DETAIL, _DATE_FORMAT))
        sub_handler.addFilter(SubsystemFilter(subsystem))
        _root_logger.addHandler(sub_handler)

    _initialized = True


class SubsystemFilter(logging.Filter):
    def __init__(self, subsystem: str):
        super().__init__()
        self.subsystem = subsystem

    def filter(self, record):
        if record.name == ROOT_LOGGER_NAME:
            return False
        try:
            module_path = record.name
            return self.subsystem in module_path
        except Exception:
            return False


def get_logger(name: str) -> logging.Logger:
    if not _initialized:
        init_logging()
    full_name = f"{ROOT_LOGGER_NAME}.{name}" if not name.startswith(ROOT_LOGGER_NAME) else name
    return logging.getLogger(full_name)


def log_event(logger, task_id: str, event: str, level: str = "info", **kwargs):
    """Structured event logging with task_id."""
    extra = {"task_id": task_id, "event": event, **kwargs}
    log_fn = getattr(logger, level, logger.info)
    log_fn(f"{event} | task={task_id}" + (f" | {kwargs}" if kwargs else ""))
