"""errors.py - Taxonomy error terpusat.

Sebelumnya logic klasifikasi error duplikat di detector.py dan
downloader.py dengan pola string yang bisa drift (mis. satu modul
kenal "429", satunya tidak). Sekarang satu fungsi klasifikasi dipakai
bersama, dengan pesan ramah yang konsisten.
"""

from __future__ import annotations

from core.constants import CONNECTION_ERROR_HINTS


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
ERROR_KIND_UNKNOWN = "unknown"

_FRIENDLY_MESSAGES = {
    ERROR_KIND_CONNECTION: "❌ Koneksi internet bermasalah, coba lagi",
    ERROR_KIND_PRIVATE: "❌ Konten ini private / tidak bisa diakses",
    ERROR_KIND_FORMAT: "❌ Format tidak tersedia untuk konten ini",
    ERROR_KIND_DISK: "❌ Tidak cukup ruang disk",
    ERROR_KIND_RATE_LIMIT: "❌ Terlalu banyak request ke platform ini - tunggu sebentar lalu coba lagi",
    ERROR_KIND_REMOVED: "❌ Konten ini sudah dihapus / tidak lagi tersedia",
    ERROR_KIND_UNSUPPORTED: "❌ URL tidak valid atau tidak didukung",
    ERROR_KIND_UNKNOWN: "❌ Terjadi kesalahan saat download",
}


def classify_error(exc: Exception) -> str:
    """Klasifikasikan exception (terutama dari yt-dlp) jadi kind string."""
    msg = str(exc).lower()
    if any(hint in msg for hint in CONNECTION_ERROR_HINTS):
        return ERROR_KIND_CONNECTION
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
    if "removed" in msg or "deleted" in msg or "no longer available" in msg:
        return ERROR_KIND_REMOVED
    return ERROR_KIND_UNKNOWN


def friendly_message(kind: str) -> str:
    """Pesan ramah untuk kind hasil classify_error()."""
    return _FRIENDLY_MESSAGES.get(kind, _FRIENDLY_MESSAGES[ERROR_KIND_UNKNOWN])


def detection_message(exc: Exception) -> str:
    """Pesan deteksi: sama dengan friendly, tapi unknown -> 'URL tidak valid'."""
    kind = classify_error(exc)
    if kind == ERROR_KIND_FORMAT:
        return "Konten ini tidak berisi video yang bisa didownload"
    if kind == ERROR_KIND_UNKNOWN:
        return "URL tidak valid atau tidak didukung"
    return friendly_message(kind).lstrip("❌ ").strip()
