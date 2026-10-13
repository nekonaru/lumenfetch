"""ffmpeg.py - Deteksi & penyiapan ffmpeg (sistem dulu, bundled fallback)."""

from __future__ import annotations

import shutil
import subprocess

from core.constants import FFMPEG_TIMEOUT_SECONDS


def find_system_ffmpeg() -> str | None:
    """Return path ffmpeg sistem kalau ada di PATH, else None."""
    return shutil.which("ffmpeg")


def is_available() -> bool:
    return find_system_ffmpeg() is not None


def exe() -> str:
    """Nama/path executable ffmpeg yang dipakai yt-dlp (merge MP4 / ekstrak MP3)."""
    return find_system_ffmpeg() or "ffmpeg"


def ensure() -> bool:
    """Pastikan ffmpeg bisa dipanggil.

    1. Kalau ffmpeg sistem ada -> langsung True (tanpa download apa pun).
    2. Kalau tidak ada -> coba static_ffmpeg bundled (lazy import).
    3. Verifikasi dengan `ffmpeg -version` (cepat, timeout 10s).
    """
    if is_available():
        return _verify(exe())
    try:
        import static_ffmpeg  # noqa: PLC0415
    except ImportError:
        return False
    try:
        static_ffmpeg.add_paths()
    except Exception:  # noqa: BLE001
        return False
    return _verify(exe())


def _verify(ffmpeg_exe: str, timeout: int = 10) -> bool:
    try:
        subprocess.run(
            [ffmpeg_exe, "-version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def version() -> str | None:
    """Versi ffmpeg (baris pertama `ffmpeg -version`), None kalau tak tersedia."""
    try:
        out = subprocess.run(
            [exe(), "-version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
        return out.splitlines()[0].strip() if out else None
    except (subprocess.CalledProcessError, FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None


__all__ = ["find_system_ffmpeg", "is_available", "exe", "ensure", "version", "FFMPEG_TIMEOUT_SECONDS"]
