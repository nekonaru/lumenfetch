"""log.py - Centralized file logging (console stays friendly via rich)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_LOGGER_NAME = "lumenfetch"
_configured = False


def log_file_path() -> Path:
    """Log file location (same folder as the user config)."""
    from core.utils import _user_data_dir  # noqa: PLC0415 - avoid circular import

    d = _user_data_dir()
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return d / "lumenfetch.log"


def setup(verbose: bool = False) -> logging.Logger:
    """Set up file + stderr handlers. Safe to call multiple times."""
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)
    if _configured:
        return logger
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        fh = logging.FileHandler(str(log_file_path()), encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        pass
    # Errors go to stderr so they are not lost when the rich console is redirected.
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.WARNING)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    _configured = True
    return logger


def get_logger(name: str = _LOGGER_NAME) -> logging.Logger:
    return logging.getLogger(name)


def get_ydl_logger() -> logging.Logger:
    """Dedicated logger for yt-dlp: all of its raw output (including
    `ERROR:` lines that cannot be silenced via `quiet`) is redirected to the log file,
    NOT to the terminal. The terminal only shows friendly messages via rich."""
    name = f"{_LOGGER_NAME}.ydl"
    logger = logging.getLogger(name)
    if getattr(logger, "_lumenfetch_configured", False):
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    try:
        fh = logging.FileHandler(str(log_file_path()), encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(fh)
    except OSError:
        logger.addHandler(logging.NullHandler())
    logger._lumenfetch_configured = True  # type: ignore[attr-defined]
    return logger


__all__ = ["setup", "get_logger", "get_ydl_logger", "log_file_path"]
