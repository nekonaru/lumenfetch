"""
detector.py
Detect YouTube video info (title, duration, playlist) from a URL using yt-dlp,
without downloading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import yt_dlp

from core.constants import YOUTUBE_HOSTS
from core.errors import DetectionError, classify_error, detection_message
from core.i18n import t
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
    content_type: str = "VIDEO"  # "VIDEO" | "AUDIO" (audio = YouTube audio stream)
    duration: float | None = None
    entries: list = field(default_factory=list)  # for playlists
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
    """True when the URL is http(s) with a known YouTube domain host."""
    if not isinstance(url, str):
        return False
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        return False
    host = _host(url)
    return any(host == h or host.endswith("." + h) for h in YOUTUBE_HOSTS)


def is_valid_url(text: str) -> bool:
    """A valid YouTube URL (http/https + YouTube host)."""
    if not isinstance(text, str):
        return False
    text = text.strip()
    return bool(URL_PATTERN.match(text)) and is_youtube_url(text)


def strip_playlist_context(url: str) -> str:
    """
    Strip the "list" (and "index") parameters from a URL when it clearly points
    to ONE specific video ("v=", /shorts/, /embed/, youtu.be) rather than a
    pure playlist link. Without this, an ordinary video carrying "list="
    wrongly pulls playlist metadata (wrong title, slow, prone to 429).
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
        # Redirect raw yt-dlp noise (ERROR:/WARNING: lines) to the log file;
        # the terminal only shows friendly messages via rich.
        "logger": get_ydl_logger(),
        # NOTE: do NOT force player_client here. An old override
        # (["android", "web"]) dodged "Sign in to confirm you're not a bot"
        # but now triggers YouTube's SABR-only experiment: only 1 progressive
        # format served instead of ~46, so quality selection fails.
        # yt-dlp's maintained defaults handle clients + fallbacks better.
        # Signature challenges still need a JS runtime (deno is yt-dlp's
        # default; also allow node/bun/quickjs if already installed).
        "js_runtimes": {"node": {}, "deno": {}, "bun": {}, "quickjs": {}},
    }


def _with_cookies_note(text: str) -> str:
    from core.errors import friendly_message  # noqa: PLC0415

    note = friendly_message("cookies").lstrip("❌ ").strip()
    return f"{note}. {text}"


def detect(url: str, cookies_browser: str | None = None, cookies_file: str | None = None) -> DetectedContent:
    """Extract YouTube video info from a URL without downloading."""
    from core.utils import apply_cookie_opts  # noqa: PLC0415 - avoid circular import

    if not is_valid_url(url):
        raise DetectionError(t("err.not_youtube_url"))

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
            # Cookies unreadable (locked browser/DPAPI): retry without cookies.
            ydl_opts.pop("cookiesfrombrowser", None)
            ydl_opts.pop("cookiefile", None)
            try:
                info = _extract(ydl_opts)
            except yt_dlp.utils.DownloadError as e2:
                raise DetectionError(_with_cookies_note(detection_message(e2))) from e2
            except Exception as e2:  # noqa: BLE001
                raise DetectionError(t("err.not_youtube_url")) from e2
        else:
            raise DetectionError(detection_message(e)) from e
    except Exception as e:  # noqa: BLE001
        raise DetectionError(t("err.not_youtube_url")) from e

    if info is None:
        raise DetectionError(t("err.not_youtube_url"))

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
