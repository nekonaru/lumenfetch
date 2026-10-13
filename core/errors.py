"""errors.py - Centralized error taxonomy.

Error-classification logic used to be duplicated in detector.py and
downloader.py with string patterns that could drift (e.g. one module
recognized "429" while the other did not). Now a single classification
function is shared, with consistent friendly messages.
"""

from __future__ import annotations

from core.constants import CONNECTION_ERROR_HINTS
from core.i18n import t


class DetectionError(Exception):
    """Friendly error for display to the user (not a raw traceback)."""


class DownloadCancelled(Exception):
    """User cancel download (Ctrl+C)."""


class DownloadFailed(Exception):
    """Fatal error that needs no retry (message is already friendly)."""


# Kinds known to classify_error().
ERROR_KIND_CONNECTION = "connection"
ERROR_KIND_PRIVATE = "private"
ERROR_KIND_FORMAT = "format"
ERROR_KIND_DISK = "disk"
ERROR_KIND_RATE_LIMIT = "rate_limit"
ERROR_KIND_REMOVED = "removed"
ERROR_KIND_UNSUPPORTED = "unsupported"
ERROR_KIND_BLOCKED = "blocked"
ERROR_KIND_COOKIES = "cookies"
ERROR_KIND_JSRUNTIME = "jsruntime"
ERROR_KIND_UNKNOWN = "unknown"

_KIND_TO_KEY = {
    ERROR_KIND_CONNECTION: "err.connection",
    ERROR_KIND_PRIVATE: "err.private",
    ERROR_KIND_FORMAT: "err.format",
    ERROR_KIND_DISK: "err.disk",
    ERROR_KIND_RATE_LIMIT: "err.rate_limit",
    ERROR_KIND_REMOVED: "err.removed",
    ERROR_KIND_UNSUPPORTED: "err.unsupported",
    ERROR_KIND_BLOCKED: "err.blocked",
    ERROR_KIND_COOKIES: "err.cookies",
    ERROR_KIND_JSRUNTIME: "err.jsruntime",
    ERROR_KIND_UNKNOWN: "err.unknown",
}


def classify_error(exc: Exception) -> str:
    """Classify an exception (mainly from yt-dlp) into a kind string."""
    msg = str(exc).lower()
    if any(hint in msg for hint in CONNECTION_ERROR_HINTS):
        return ERROR_KIND_CONNECTION
    if "could not copy" in msg and "cookie" in msg:
        # Cookie file locked by a still-open browser (yt-dlp #7271).
        # Not a broken URL - must be handled specially (retry without cookies).
        return ERROR_KIND_COOKIES
    if "failed to decrypt" in msg or "dpapi" in msg or "failed to load cookies" in msg:
        # Encrypted cookies cannot be decrypted (yt-dlp #10927, common on
        # Edge/Chrome for Windows) - likewise: not a broken URL, fall back without cookies.
        return ERROR_KIND_COOKIES
    if "javascript runtime" in msg or "js runtime" in msg:
        # Modern yt-dlp needs Deno/Node/Bun to solve YouTube signature
        # challenges - without one, videos fail as "unavailable".
        return ERROR_KIND_JSRUNTIME
    if "unexpected response from webpage request" in msg or "confirm you are on the latest version" in msg:
        # Bot-check challenge that only passes with impersonation + cookies,
        # not a broken URL.
        return ERROR_KIND_BLOCKED
    if "private" in msg or "login required" in msg or "login" in msg or "unavailable" in msg:
        return ERROR_KIND_PRIVATE
    if "unsupported url" in msg:
        return ERROR_KIND_UNSUPPORTED
    if "requested format is not available" in msg or "no video formats" in msg:
        return ERROR_KIND_FORMAT
    if "no space left" in msg:
        return ERROR_KIND_DISK
    if "429" in msg or "too many requests" in msg or "rate-limit" in msg or "rate limit" in msg:
        return ERROR_KIND_RATE_LIMIT
    if "404" in msg or "not found" in msg or "removed" in msg or "deleted" in msg or "no longer available" in msg:
        return ERROR_KIND_REMOVED
    return ERROR_KIND_UNKNOWN


def _curl_cffi_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("curl_cffi") is not None


def blocked_message() -> str:
    """Adaptive blocked message: mention curl_cffi only when it is not installed."""
    base = t("err.blocked")
    if not _curl_cffi_available():
        base += t("err.blocked_curl")
    return base


def friendly_message(kind: str) -> str:
    """Friendly message for a classify_error() kind (follows the active language)."""
    if kind == ERROR_KIND_BLOCKED:
        return blocked_message()
    key = _KIND_TO_KEY.get(kind, "err.unknown")
    return t(key)


def detection_message(exc: Exception) -> str:
    """Detection message: same as friendly, but unknown -> invalid YouTube URL."""
    kind = classify_error(exc)
    if kind == ERROR_KIND_FORMAT:
        return t("err.no_video")
    if kind == ERROR_KIND_UNKNOWN:
        return t("err.unknown_detect")
    return friendly_message(kind).lstrip("❌ ").strip()
