"""
detector.py
Deteksi info video YouTube (judul, durasi, playlist) dari URL memakai yt-dlp,
tanpa mendownload.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import yt_dlp

from core.constants import YOUTUBE_HOSTS
from core.errors import DetectionError, classify_error, detection_message
from core.log import get_ydl_logger

__all__ = [
    "DetectionError",
    "DetectedContent",
    "is_youtube_url",
    "is_valid_url",
    "strip_playlist_context",
    "detect",
]

URL_PATTERN = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)


@dataclass
class DetectedContent:
    url: str
    title: str
    content_type: str = "VIDEO"  # "VIDEO" | "AUDIO" (audio = stream audio YouTube)
    duration: float | None = None
    entries: list = field(default_factory=list)  # untuk playlist
    raw_info: dict = field(default_factory=dict)

    @property
    def platform(self) -> str:
        return "YouTube"


def _host(url: str) -> str:
    try:
        return urlsplit(url).netloc.lower().split(":")[0]
    except ValueError:
        return ""


def is_youtube_url(url: str) -> bool:
    """True bila URL http(s) dengan host domain YouTube yang dikenal."""
    if not isinstance(url, str):
        return False
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        return False
    host = _host(url)
    return any(host == h or host.endswith("." + h) for h in YOUTUBE_HOSTS)


def is_valid_url(text: str) -> bool:
    """URL YouTube yang valid (http/https + host YouTube)."""
    if not isinstance(text, str):
        return False
    text = text.strip()
    return bool(URL_PATTERN.match(text)) and is_youtube_url(text)


def strip_playlist_context(url: str) -> str:
    """
    Buang parameter "list" (dan "index") dari URL kalau URL itu jelas
    menunjuk ke SATU video spesifik (ada "v=", /shorts/, /embed/, youtu.be),
    bukan link playlist murni. Tanpa ini, video biasa yang kebawa "list="
    salah narik metadata playlist-nya (judul salah, lambat, rawan 429).
    """
    parts = urlsplit(url)
    pairs = parse_qsl(parts.query, keep_blank_values=True)

    if not any(k == "list" for k, _ in pairs):
        return url

    query_dict = dict(pairs)
    has_specific_video = (
        "v" in query_dict
        or "/shorts/" in parts.path
        or "/embed/" in parts.path
        or ((parts.netloc == "youtu.be" or parts.netloc.endswith(".youtu.be")) and parts.path.strip("/") != "")
    )
    if not has_specific_video:
        return url

    filtered = [(k, v) for k, v in pairs if k not in ("list", "index")]
    new_query = urlencode(filtered)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def _base_ydl_opts() -> dict:
    return {
        "quiet": True,
        "no_warnings": True,
        # Alihkan noise mentah yt-dlp (baris ERROR:/WARNING:) ke file log,
        # terminal hanya menampilkan pesan ramah via rich.
        "logger": get_ydl_logger(),
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }


def _with_cookies_note(text: str) -> str:
    from core.errors import friendly_message  # noqa: PLC0415

    note = friendly_message("cookies").lstrip("❌ ").strip()
    return f"{note}. {text}"


def detect(url: str, cookies_browser: str | None = None, cookies_file: str | None = None) -> DetectedContent:
    """Ekstrak info video YouTube dari URL tanpa mendownload."""
    from core.utils import apply_cookie_opts  # noqa: PLC0415 - hindari circular import

    if not is_valid_url(url):
        raise DetectionError("URL bukan link YouTube yang valid")

    url = strip_playlist_context(url)

    ydl_opts = _base_ydl_opts()
    ydl_opts.update({"skip_download": True, "noplaylist": False})

    has_cookies = apply_cookie_opts(ydl_opts, cookies_browser, cookies_file)

    def _extract(opts: dict):
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        info = _extract(ydl_opts)
    except yt_dlp.utils.DownloadError as e:
        if has_cookies and classify_error(e) == "cookies":
            # Cookies gagal dibaca (browser terkunci/DPAPI): coba tanpa cookies.
            ydl_opts.pop("cookiesfrombrowser", None)
            ydl_opts.pop("cookiefile", None)
            try:
                info = _extract(ydl_opts)
            except yt_dlp.utils.DownloadError as e2:
                raise DetectionError(_with_cookies_note(detection_message(e2))) from e2
            except Exception as e2:  # noqa: BLE001
                raise DetectionError("URL bukan link YouTube yang valid") from e2
        else:
            raise DetectionError(detection_message(e)) from e
    except Exception as e:  # noqa: BLE001
        raise DetectionError("URL bukan link YouTube yang valid") from e

    if info is None:
        raise DetectionError("URL bukan link YouTube yang valid")

    raw_entries = info.get("entries") or []
    entries = raw_entries if isinstance(raw_entries, list) else list(raw_entries)
    vcodec = info.get("vcodec")

    return DetectedContent(
        url=url,
        title=info.get("title") or info.get("id") or "untitled",
        content_type="AUDIO" if vcodec == "none" else "VIDEO",
        duration=info.get("duration"),
        entries=entries,
        raw_info=info,
    )
