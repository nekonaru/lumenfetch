"""
utils.py
Kumpulan fungsi bantu: sanitasi nama file, format ukuran,
dan baca/tulis config.json.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path("config.json")

DEFAULT_CONFIG = {
    "version": 1,
    "download_folder": "downloads/",
    "auto_paste": True,
    "naming_template": "%(platform)s_%(title)s_%(year)s",
    "max_retry": 3,
    "cookies_browser": None,
    "history": [],
}

# Browser yang didukung yt-dlp untuk ambil cookies (buat konten yang butuh login,
# misal Instagram). None/"none" berarti fitur ini nonaktif.
SUPPORTED_COOKIE_BROWSERS = ["none", "chrome", "firefox", "edge", "brave", "opera", "vivaldi", "safari"]

ILLEGAL_CHARS = r'[\\/:*?"<>|]'
MAX_TITLE_LEN = 80


def get_default_config() -> dict:
    """
    Return salinan BENAR-BENAR terpisah dari DEFAULT_CONFIG (deep copy).

    Wajib pakai ini (bukan DEFAULT_CONFIG.copy()) di manapun butuh config default,
    karena "history" adalah list - shallow copy cuma menyalin referensinya,
    bukan isinya. Kalau nanti list itu dimutasi (mis. lewat add_history_entry),
    DEFAULT_CONFIG module-level ikut "tercemar" dan bocor ke semua config baru
    yang dibuat sesudahnya, termasuk pas user reset ke default.
    """
    return copy.deepcopy(DEFAULT_CONFIG)


def load_config() -> dict:
    """Baca config.json, buat default kalau belum ada / rusak."""
    if not CONFIG_PATH.exists():
        fresh = get_default_config()
        save_config(fresh)
        return fresh

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Isi field yang hilang biar tetap kompatibel ke depan
        merged = get_default_config()
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        fresh = get_default_config()
        save_config(fresh)
        return fresh


def save_config(config: dict) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def add_history_entry(config: dict, entry: dict) -> None:
    """Tambah entri riwayat baru, maksimal simpan 20 entri terakhir."""
    history = config.get("history", [])
    history.insert(0, entry)
    config["history"] = history[:20]
    save_config(config)


def clear_history(config: dict) -> None:
    config["history"] = []
    save_config(config)


def sanitize_filename(name: str) -> str:
    """Bersihkan nama file dari karakter ilegal & spasi, truncate max 80 char."""
    if not name:
        name = "untitled"
    name = re.sub(ILLEGAL_CHARS, "_", name)
    name = name.strip().replace(" ", "-")
    name = re.sub(r"-{2,}", "-", name)
    return name[:MAX_TITLE_LEN]


def build_filename(platform: str, title: str, ext: str, template: str) -> str:
    """Susun nama file berdasarkan naming template dari config."""
    year = datetime.now().year
    base = template % {
        "platform": sanitize_filename(platform or "Unknown"),
        "title": sanitize_filename(title or "untitled"),
        "year": year,
    }
    return f"{base}.{ext}"


def resolve_duplicate(path: Path) -> Path:
    """Kalau nama file udah ada, tambahin suffix (1), (2), dst."""
    if not path.exists():
        return path

    stem, suffix = path.stem, path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem}({counter}){suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def build_cookies_from_browser(browser: str | None):
    """
    Ubah nama browser dari config jadi format yang dipahami yt-dlp
    (opsi 'cookiesfrombrowser'). Return None kalau fitur nonaktif.
    """
    if not browser or browser == "none":
        return None
    if browser not in SUPPORTED_COOKIE_BROWSERS:
        return None
    return (browser, None, None, None)


def format_size(num_bytes: float) -> str:
    """Format bytes jadi human-readable (KB/MB/GB)."""
    if num_bytes is None:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def format_duration(seconds) -> str:
    """Format detik jadi H:MM:SS atau M:SS."""
    if not seconds:
        return "-"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
