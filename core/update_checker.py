"""
update_checker.py
Check the latest yt-dlp version on PyPI to show a notice when the local version is behind.
Fail silently without internet / when PyPI is unreachable - the
check MUST NOT block or slow down the user of the app.
"""

from __future__ import annotations

import json
import urllib.request
from urllib.error import URLError

import yt_dlp

from core.constants import UPDATE_CHECK_TIMEOUT_SECONDS

PYPI_URL = "https://pypi.org/pypi/yt-dlp/json"
LUMENFETCH_PYPI_URL = "https://pypi.org/pypi/lumenfetch/json"
TIMEOUT_SECONDS = UPDATE_CHECK_TIMEOUT_SECONDS


def get_installed_version() -> str:
    return yt_dlp.version.__version__


def get_latest_version(timeout: float = TIMEOUT_SECONDS) -> str | None:
    """Return the latest yt-dlp version on PyPI, or None if the check fails (e.g. no internet)."""
    try:
        with urllib.request.urlopen(PYPI_URL, timeout=timeout) as response:  # noqa: S310
            data = json.loads(response.read().decode("utf-8"))
        version = data.get("info", {}).get("version")
        return str(version) if version else None
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None


def _version_tuple(version: str) -> tuple[int, ...]:
    """yt-dlp uses the YYYY.MM.DD[.rev] version format - order as numbers so comparison is correct."""
    parts = []
    for part in str(version).split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def get_lumenfetch_latest(timeout: float = TIMEOUT_SECONDS) -> str | None:
    """Return the latest lumenfetch version on PyPI, or None if the check fails."""
    try:
        with urllib.request.urlopen(LUMENFETCH_PYPI_URL, timeout=timeout) as response:  # noqa: S310
            data = json.loads(response.read().decode("utf-8"))
        version = data.get("info", {}).get("version")
        return str(version) if version else None
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None


def check_self_update() -> tuple[bool, str, str | None]:
    """Check whether a newer lumenfetch release exists on PyPI."""
    from core.constants import VERSION  # noqa: PLC0415

    installed = VERSION
    latest = get_lumenfetch_latest()

    if latest is None:
        return False, installed, None

    has_update = _version_tuple(latest) > _version_tuple(installed)
    return has_update, installed, latest


def check_for_update() -> tuple[bool, str, str | None]:
    """
    Check whether a newer yt-dlp version exists than the installed one.

    Return (has_update, installed_version, latest_version_or_None).
    has_update is always False when already on the latest version OR when the check
    fails (fail-safe - no internet does not mean "has update").
    """
    installed = get_installed_version()
    latest = get_latest_version()

    if latest is None:
        return False, installed, None

    has_update = _version_tuple(latest) > _version_tuple(installed)
    return has_update, installed, latest
