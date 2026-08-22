"""
utils.py
Kumpulan fungsi bantu: sanitasi nama file, format ukuran,
dan baca/tulis config.json.
"""

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
    "history": [],
}

ILLEGAL_CHARS = r'[\\/:*?"<>|]'
MAX_TITLE_LEN = 80


def load_config() -> dict:
    """Baca config.json, buat default kalau belum ada / rusak."""
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Isi field yang hilang biar tetap kompatibel ke depan
        merged = DEFAULT_CONFIG.copy()
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


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
