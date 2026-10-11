"""log.py - Logging file terpusat (console tetap ramah via rich)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_LOGGER_NAME = "lumenfetch"
_configured = False


def log_file_path() -> Path:
    """Lokasi file log (sefolder dengan config user)."""
    from core.utils import _user_data_dir  # noqa: PLC0415 - hindari circular import

    d = _user_data_dir()
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return d / "lumenfetch.log"


def setup(verbose: bool = False) -> logging.Logger:
    """Setup handler file + stderr. Aman dipanggil berkali-kali."""
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
    # Error ke stderr agar tidak hilang saat rich console di-redirect.
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.WARNING)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    _configured = True
    return logger


def get_logger(name: str = _LOGGER_NAME) -> logging.Logger:
    return logging.getLogger(name)


__all__ = ["setup", "get_logger", "log_file_path"]
