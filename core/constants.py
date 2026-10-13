"""constants.py - Single source of truth for shared values."""

from __future__ import annotations

VERSION = "2.1.0"

# --- Config ---
HISTORY_LIMIT = 20
CONFIG_VERSION = 2
UPDATE_CHECK_TIMEOUT_SECONDS = 2
DOWNLOAD_TIMEOUT_SECONDS = 30
FFMPEG_TIMEOUT_SECONDS = 120
APP_NAME = "lumenfetch"

# --- Retry (exponential backoff) ---
RETRY_BASE_DELAY_SECONDS = 2.0
RETRY_MAX_DELAY_SECONDS = 30.0
RETRY_JITTER_SECONDS = 1.0

# --- Playlist ---
PLAYLIST_MODE_SINGLE = "single"
PLAYLIST_MODE_ALL = "all"
PLAYLIST_MODES = [PLAYLIST_MODE_SINGLE, PLAYLIST_MODE_ALL]

# --- Subtitle ---
SUBTITLE_LANGS_DEFAULT = ["en", "id"]

# --- Batch ---
BATCH_DEFAULT_JOBS = 1
BATCH_MAX_JOBS = 4

# --- YouTube ---
YOUTUBE_HOSTS = ("youtube.com", "youtu.be", "music.youtube.com", "youtube-nocookie.com")
VIDEO_QUALITIES = ["Best", "1080p", "720p", "480p", "360p", "Worst"]
VIDEO_FORMAT = "mp4"
AUDIO_FORMAT = "mp3"
AUDIO_QUALITIES = ["Best", "320kbps", "192kbps", "128kbps"]

# Video containers supported by yt-dlp's EmbedThumbnailPP.
EMBEDDABLE_VIDEO_FORMATS = frozenset({"mp4"})

# --- Download ---
CONNECTION_ERROR_HINTS = (
    "timed out",
    "timeout",
    "connection",
    "network",
    "temporary failure",
    "reset by peer",
)

# Height limit per quality label (None = unlimited / take best).
HEIGHT_LIMITS = {
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
    "360p": 360,
}

# Target bitrate (kbps) for lossy audio options.
AUDIO_TARGET_KBPS = {
    "320kbps": 320,
    "192kbps": 192,
    "128kbps": 128,
}

# Browsers supported by yt-dlp for cookiesfrombrowser.
SUPPORTED_COOKIE_BROWSERS = ["none", "chrome", "firefox", "edge", "brave", "opera", "vivaldi", "safari"]

# --- Filenames ---
ILLEGAL_CHARS = r'[\\/:*?"<>|]'
MAX_TITLE_LEN = 80
# Windows reserved names (case-insensitive) that must not be used as file names.
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
