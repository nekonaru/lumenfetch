"""
detector.py
Deteksi platform, tipe konten (VIDEO/IMAGE/AUDIO), judul, dan durasi
dari sebuah URL memakai yt-dlp (tanpa download).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import yt_dlp

from core.utils import build_cookies_from_browser

URL_PATTERN = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)


class DetectionError(Exception):
    """Error ramah untuk ditampilkan ke user (bukan traceback mentah)."""


@dataclass
class DetectedContent:
    url: str
    platform: str
    title: str
    content_type: str  # "VIDEO" | "IMAGE" | "AUDIO"
    duration: float | None = None
    entries: list = field(default_factory=list)  # untuk carousel/multi-image
    raw_info: dict = field(default_factory=dict)


def is_valid_url(text: str) -> bool:
    return bool(URL_PATTERN.match(text.strip()))


def _guess_content_type(info: dict) -> str:
    """Tentukan VIDEO / AUDIO / IMAGE berdasarkan info dari yt-dlp."""
    is_playlist = info.get("_type") == "playlist"

    if is_playlist:
        entries = info.get("entries") or []
        # Kalau semua entry gak punya video codec -> anggap kumpulan gambar
        if entries and all(_looks_like_image(e) for e in entries):
            return "IMAGE"
        return "VIDEO"

    if _looks_like_image(info):
        return "IMAGE"

    vcodec = info.get("vcodec")
    if vcodec and vcodec != "none":
        return "VIDEO"

    acodec = info.get("acodec")
    if acodec and acodec != "none":
        return "AUDIO"

    # fallback: kalau ada duration dianggap video, kalau enggak dianggap image
    return "VIDEO" if info.get("duration") else "IMAGE"


def _looks_like_image(entry: dict) -> bool:
    ext = (entry.get("ext") or "").lower()
    return ext in {"jpg", "jpeg", "png", "webp"} or entry.get("vcodec") == "none" and not entry.get("duration")


def strip_playlist_context(url: str) -> str:
    """
    Buang parameter "list" (dan "index") dari URL kalau URL itu jelas
    menunjuk ke SATU video spesifik (ada parameter identitas video kayak
    "v=" di YouTube, atau path /shorts/, /embed/), bukan link playlist murni.

    Kenapa ini perlu: link video biasa yang dicopy pas lagi nonton di dalam
    playlist YouTube otomatis kebawa "&list=...". detect() sengaja pakai
    "noplaylist": False (biar galeri multi-gambar - Pinterest board, Reddit
    gallery, tweet multi-foto - bisa kedeteksi lengkap semua entry-nya).
    Tanpa strip ini, video biasa yang kebawa "list=" bakal salah kena narik
    METADATA PLAYLIST-nya (bukan video itu sendiri) - judul hasil deteksi
    jadi salah (nama playlist, bukan judul video), prosesnya jauh lebih
    lambat/berat (yt-dlp narik semua entry playlist walau skip_download),
    dan lebih rawan kena rate-limit (429) dari YouTube.

    Galeri multi-gambar TIDAK terpengaruh sama sekali oleh fungsi ini,
    karena mereka tidak pernah punya parameter "list" di URL-nya.
    """
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))

    if "list" not in query:
        return url

    has_specific_video = (
        "v" in query
        or "/shorts/" in parts.path
        or "/embed/" in parts.path
        # youtu.be/<video-id> - video ID-nya ada di PATH, bukan di query "v=".
        # Ini format link yang paling sering muncul (tombol Share YouTube),
        # jadi paling krusial buat gak kelewat. Dicek exact match / subdomain
        # (bukan endswith longgar) biar domain asing semacam "notyoutu.be"
        # gak ikut ke-treat sebagai youtu.be.
        or ((parts.netloc == "youtu.be" or parts.netloc.endswith(".youtu.be")) and parts.path.strip("/") != "")
    )
    if not has_specific_video:
        return url  # kemungkinan besar ini memang link playlist murni, biarkan apa adanya

    query.pop("list", None)
    query.pop("index", None)
    new_query = urlencode(query)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def detect(url: str, cookies_browser: str | None = None) -> DetectedContent:
    """Ekstrak info konten dari URL tanpa mendownload."""
    if not is_valid_url(url):
        raise DetectionError("URL tidak valid atau tidak didukung")

    url = strip_playlist_context(url)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": False,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }

    cookies = build_cookies_from_browser(cookies_browser)
    if cookies:
        ydl_opts["cookiesfrombrowser"] = cookies

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        msg = str(e).lower()
        if "there is no video in this post" in msg or "no video formats" in msg:
            from core import instagram_fallback  # noqa: PLC0415 - lazy import, hindari circular import

            if instagram_fallback.is_instagram_url(url):
                return instagram_fallback.detect_photo(url)
            raise DetectionError("Konten ini tidak berisi video yang bisa didownload") from e
        if "private" in msg or "login" in msg or "unavailable" in msg:
            raise DetectionError("Konten ini private / tidak bisa diakses") from e
        if "unsupported url" in msg:
            raise DetectionError("URL tidak valid atau tidak didukung") from e
        if "429" in msg or "too many requests" in msg or "rate-limit" in msg or "rate limit" in msg:
            raise DetectionError("Terlalu banyak request ke platform ini - tunggu sebentar lalu coba lagi") from e
        if "removed" in msg or "deleted" in msg or "no longer available" in msg:
            raise DetectionError("Konten ini sudah dihapus / tidak lagi tersedia") from e
        raise DetectionError("Koneksi internet bermasalah, coba lagi") from e
    except Exception as e:  # noqa: BLE001
        raise DetectionError("URL tidak valid atau tidak didukung") from e

    if info is None:
        raise DetectionError("URL tidak valid atau tidak didukung")

    content_type = _guess_content_type(info)
    entries = info.get("entries") or []

    return DetectedContent(
        url=url,
        platform=info.get("extractor_key") or info.get("extractor") or "Unknown",
        title=info.get("title") or info.get("id") or "untitled",
        content_type=content_type,
        duration=info.get("duration"),
        entries=list(entries),
        raw_info=info,
    )
