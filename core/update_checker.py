"""
update_checker.py
Cek versi terbaru yt-dlp di PyPI, buat kasih notice kalau versi lokal ketinggalan.
Gagal diam-diam kalau tidak ada internet / PyPI tidak bisa diakses - proses
pengecekan TIDAK BOLEH menghalangi atau memperlambat user pakai aplikasi.
"""

from __future__ import annotations

import json
import urllib.request
from urllib.error import URLError

import yt_dlp

PYPI_URL = "https://pypi.org/pypi/yt-dlp/json"
TIMEOUT_SECONDS = 3


def get_installed_version() -> str:
    return yt_dlp.version.__version__


def get_latest_version() -> str | None:
    """Return versi terbaru yt-dlp di PyPI, atau None kalau gagal cek (mis. tidak ada internet)."""
    try:
        with urllib.request.urlopen(PYPI_URL, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            data = json.loads(response.read().decode("utf-8"))
        return data.get("info", {}).get("version")
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None


def _version_tuple(version: str) -> tuple[int, ...]:
    """yt-dlp pakai format versi YYYY.MM.DD[.rev] - urutkan sebagai angka biar perbandingan benar."""
    parts = []
    for part in version.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def check_for_update() -> tuple[bool, str, str | None]:
    """
    Cek apakah ada versi yt-dlp yang lebih baru dari yang terinstall.

    Return (ada_update, versi_terinstall, versi_terbaru_atau_None).
    ada_update selalu False kalau sudah versi terbaru ATAU kalau pengecekan
    gagal (fail-safe - tidak ada internet bukan berarti "ada update").
    """
    installed = get_installed_version()
    latest = get_latest_version()

    if latest is None:
        return False, installed, None

    has_update = _version_tuple(latest) > _version_tuple(installed)
    return has_update, installed, latest
