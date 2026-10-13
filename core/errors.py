"""errors.py - Taxonomy error terpusat.

Sebelumnya logic klasifikasi error duplikat di detector.py dan
downloader.py dengan pola string yang bisa drift (mis. satu modul
kenal "429", satunya tidak). Sekarang satu fungsi klasifikasi dipakai
bersama, dengan pesan ramah yang konsisten.
"""

from __future__ import annotations

from core.constants import CONNECTION_ERROR_HINTS
from core.i18n import t


class DetectionError(Exception):
    """Error ramah untuk ditampilkan ke user (bukan traceback mentah)."""


class DownloadCancelled(Exception):
    """User cancel download (Ctrl+C)."""


class DownloadFailed(Exception):
    """Error fatal yang gak perlu di-retry (pesan sudah ramah)."""


# Kind yang dikenal classify_error().
ERROR_KIND_CONNECTION = "connection"
ERROR_KIND_PRIVATE = "private"
ERROR_KIND_FORMAT = "format"
ERROR_KIND_DISK = "disk"
ERROR_KIND_RATE_LIMIT = "rate_limit"
ERROR_KIND_REMOVED = "removed"
ERROR_KIND_UNSUPPORTED = "unsupported"
ERROR_KIND_BLOCKED = "blocked"
ERROR_KIND_COOKIES = "cookies"
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
    ERROR_KIND_UNKNOWN: "err.unknown",
}


def classify_error(exc: Exception) -> str:
    """Klasifikasikan exception (terutama dari yt-dlp) jadi kind string."""
    msg = str(exc).lower()
    if any(hint in msg for hint in CONNECTION_ERROR_HINTS):
        return ERROR_KIND_CONNECTION
    if "could not copy" in msg and "cookie" in msg:
        # File cookies dikunci browser yang masih terbuka (yt-dlp #7271).
        # Bukan URL rusak - harus ditangani khusus (coba tanpa cookies).
        return ERROR_KIND_COOKIES
    if "failed to decrypt" in msg or "dpapi" in msg or "failed to load cookies" in msg:
        # Cookies terenkripsi tak bisa didekripsi (yt-dlp #10927, umum di
        # Edge/Chrome Windows) - sama: bukan URL rusak, fallback tanpa cookies.
        return ERROR_KIND_COOKIES
    if "unexpected response from webpage request" in msg or "confirm you are on the latest version" in msg:
        # Challenge bot-check yang cuma lolos pakai impersonation + cookies,
        # bukan URL rusak.
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
    """Pesan blocked yang adaptif: sebut curl_cffi hanya bila belum terinstall."""
    base = t("err.blocked")
    if not _curl_cffi_available():
        base += t("err.blocked_curl")
    return base


def friendly_message(kind: str) -> str:
    """Pesan ramah untuk kind hasil classify_error() (mengikuti bahasa aktif)."""
    if kind == ERROR_KIND_BLOCKED:
        return blocked_message()
    key = _KIND_TO_KEY.get(kind, "err.unknown")
    return t(key)


def detection_message(exc: Exception) -> str:
    """Pesan deteksi: sama dengan friendly, tapi unknown -> URL YouTube tidak valid."""
    kind = classify_error(exc)
    if kind == ERROR_KIND_FORMAT:
        return t("err.no_video")
    if kind == ERROR_KIND_UNKNOWN:
        return t("err.unknown_detect")
    return friendly_message(kind).lstrip("❌ ").strip()
