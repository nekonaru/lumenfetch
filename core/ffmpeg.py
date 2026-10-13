"""ffmpeg.py - ffmpeg detection & setup (system first, bundled fallback)."""

from __future__ import annotations

import shutil
import subprocess

from core.constants import FFMPEG_TIMEOUT_SECONDS


def find_system_ffmpeg() -> str | None:
    """Return the system ffmpeg path if found on PATH, else None."""
    return shutil.which("ffmpeg")


def is_available() -> bool:
    return find_system_ffmpeg() is not None


def exe() -> str:
    """Name/path of the ffmpeg executable used by yt-dlp (MP4 merge / MP3 extraction)."""
    return find_system_ffmpeg() or "ffmpeg"


def ensure() -> bool:
    """Ensure ffmpeg can be invoked.

    1. If system ffmpeg exists -> True directly (no downloads at all).
    2. If missing -> try the bundled static_ffmpeg (lazy import).
    3. Verify with `ffmpeg -version` (fast, 10s timeout).
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
    """ffmpeg version (first line of `ffmpeg -version`), None if unavailable."""
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
