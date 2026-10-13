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


def get_ydl_logger() -> logging.Logger:
    """Logger khusus untuk yt-dlp: semua output mentahnya (termasuk baris
    `ERROR:` yang tidak bisa dimatikan via `quiet`) dialihkan ke file log,
    TIDAK ke terminal. Terminal hanya menampilkan pesan ramah via rich."""
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
