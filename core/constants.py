"""constants.py - Single source of truth untuk nilai-nilai shared.

Tujuannya biar tidak ada duplikasi magic value yang bisa drift
(mis. VERSION di main.py vs default arg di options.show_header,
atau daftar format audio di options.py vs mapping bitrate di utils.py).
"""

from __future__ import annotations

VERSION = "1.0.0"

# --- Config ---
HISTORY_LIMIT = 20
HISTORY_LOCK_TIMEOUT = 5.0
CONFIG_VERSION = 1
UPDATE_CHECK_TIMEOUT_SECONDS = 2
DOWNLOAD_TIMEOUT_SECONDS = 30
FFMPEG_TIMEOUT_SECONDS = 120
APP_NAME = "lumenfetch"

# --- Retry (backoff eksponensial) ---
RETRY_BASE_DELAY_SECONDS = 2.0
RETRY_MAX_DELAY_SECONDS = 30.0
RETRY_JITTER_SECONDS = 1.0

# --- Playlist ---
PLAYLIST_MODE_SINGLE = "single"
PLAYLIST_MODE_ALL = "all"
PLAYLIST_MODES = [PLAYLIST_MODE_SINGLE, PLAYLIST_MODE_ALL]

# --- Subtitle ---
SUBTITLE_LANGS_DEFAULT = ["en", "id"]
SUBTITLE_FORMATS = ["srt", "vtt", "ass", "lrc"]

# --- Batch ---
BATCH_DEFAULT_JOBS = 1
BATCH_MAX_JOBS = 4

# --- Filenames ---
ILLEGAL_CHARS = r'[\\/:*?"<>|]'
MAX_TITLE_LEN = 80
# Nama reserved Windows (case-insensitive) yang tidak boleh jadi nama file.
WINDOWS_RESERVED_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
)

# --- Pilihan menu ---
VIDEO_QUALITIES = ["Best", "1080p", "720p", "480p", "360p", "Worst"]
VIDEO_FORMATS = ["MP4", "WEBM", "MKV"]
AUDIO_FORMATS = ["MP3", "M4A", "WAV", "FLAC"]
AUDIO_QUALITIES = ["Best", "320kbps", "192kbps", "128kbps"]
IMAGE_FORMATS = ["JPG", "PNG", "WEBP"]

LOSSLESS_AUDIO_FORMATS = frozenset({"wav", "flac"})

# Container video yang didukung EmbedThumbnailPP milik yt-dlp.
# WEBM sengaja tidak termasuk (yt-dlp selalu raise EmbedThumbnailPPError).
EMBEDDABLE_VIDEO_FORMATS = frozenset({"mp4", "mkv"})

# --- Download ---
CONNECTION_ERROR_HINTS = (
    "timed out",
    "timeout",
    "connection",
    "network",
    "temporary failure",
    "reset by peer",
)

# Batas tinggi per label quality (None = tanpa batas / ambil terbaik).
HEIGHT_LIMITS = {
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
    "360p": 360,
}

# Target bitrate (kbps) untuk opsi audio lossy.
AUDIO_TARGET_KBPS = {
    "320kbps": 320,
    "192kbps": 192,
    "128kbps": 128,
}

# Browser yang didukung yt-dlp untuk cookiesfrombrowser.
SUPPORTED_COOKIE_BROWSERS = ["none", "chrome", "firefox", "edge", "brave", "opera", "vivaldi", "safari"]
