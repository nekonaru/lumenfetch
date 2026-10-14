"""
downloader.py
Download YouTube video (MP4) / extract audio (MP3) using yt-dlp,
with Rich progress hook, automatic resume, and exponential backoff retry.
"""

from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import yt_dlp
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from core.constants import (
    EMBEDDABLE_VIDEO_FORMATS,
    PLAYLIST_MODE_ALL,
    RETRY_BASE_DELAY_SECONDS,
    RETRY_JITTER_SECONDS,
    RETRY_MAX_DELAY_SECONDS,
    SUBTITLE_LANGS_DEFAULT,
)
from core.detector import DetectedContent
from core.errors import (
    DownloadCancelled,
    DownloadFailed,
    classify_error,
    friendly_message,
)
from core.i18n import t
from core.log import get_ydl_logger
from core.options import DownloadChoice
from core.utils import (
    _iter_dir_files,
    apply_cookie_opts,
    build_filename,
    find_indexed_files,
    resolve_duplicate,
)

__all__ = [
    "DownloadCancelled",
    "DownloadFailed",
    "DownloadResult",
    "CONNECTION_ERROR_HINTS",
    "EMBEDDABLE_VIDEO_FORMATS",
    "backoff_delay",
    "download",
]

console = Console()

CONNECTION_ERROR_HINTS = tuple(__import__("core.constants", fromlist=["CONNECTION_ERROR_HINTS"]).CONNECTION_ERROR_HINTS)

_HEIGHT_FILTERS = {    "Best": "",
    "1080p": "[height<=1080]",
    "720p": "[height<=720]",
    "480p": "[height<=480]",
    "360p": "[height<=360]",
    "Worst": "",
}

_AUDIO_KBPS = {"Best": "0", "320kbps": "320", "192kbps": "192", "128kbps": "128"}

# Lock + in-memory set for duplicate resolution, so parallel batch
# workers downloading the same title don't pick the same filename.
# NOTE: reservation is memory-only on purpose. An earlier version created
# an empty placeholder FILE, but yt-dlp treats an existing dest file as
# "already downloaded" and finishes instantly with 0 bytes (then the
# thumbnail postprocessor crashes on it). Never pre-create the dest.
_resolve_lock = threading.Lock()
_reserved_keys: set[str] = set()


@dataclass
class DownloadResult:
    filepath: Path
    size_bytes: int
    elapsed_seconds: float
    file_count: int = 1  # >1 when --playlist all


def _quality_to_format_selector(quality: str, ext: str = "mp4") -> str:
    """
    Video selector: prioritize video+audio combinations whose codecs are already
    MP4-compatible (h264+aac) so ffmpeg only needs to remux without re-encoding.
    """
    hf = _HEIGHT_FILTERS.get(quality, "")

    if quality == "Worst":
        return f"worstvideo*{hf}+worstaudio/worst{hf}"

    if ext == "mp4":
        return f"bestvideo[ext=mp4]{hf}+bestaudio[ext=m4a]/bestvideo*{hf}+bestaudio/best{hf}"
    return f"bestvideo*{hf}+bestaudio/best{hf}"


def _audio_quality_to_kbps(quality: str) -> str:
    return _AUDIO_KBPS.get(quality, "0")


def _make_progress_hook(progress: Progress, task_id):
    def hook(d: dict):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                progress.update(task_id, total=total, completed=downloaded)
            filename = d.get("filename") or "Downloading"
            progress.update(task_id, description=filename[:40])
        elif d.get("status") == "finished":
            try:
                total = progress.tasks[task_id].total
            except (IndexError, AttributeError):
                total = None
            if total:
                progress.update(task_id, completed=total)

    return hook


def _classify_error(e: Exception) -> str:
    """Compatible wrapper - canonical logic lives in core.errors.classify_error."""
    return classify_error(e)


def _friendly_message(kind: str) -> str:
    return friendly_message(kind)


def backoff_delay(attempt: int) -> float:
    """Exponential delay for retry `attempt` (1-indexed), capped at max + jitter."""
    import random

    base = RETRY_BASE_DELAY_SECONDS * (2.0 ** max(0, attempt - 1))
    capped = min(base, RETRY_MAX_DELAY_SECONDS)
    return capped + random.uniform(0, RETRY_JITTER_SECONDS)


def _reserve_key(dest: Path, multi_item: bool) -> str:
    norm = os.path.normcase(os.path.abspath(dest if not multi_item else dest.with_suffix("")))
    return norm


def _bump_suffix(dest: Path) -> Path:
    """X.mp4 -> X(1).mp4 -> X(2).mp4 (same scheme as resolve_duplicate)."""
    stem, suffix = dest.stem, dest.suffix
    m = re.search(r"\((\d+)\)$", stem)
    if m:
        base = stem[: m.start()]
        n = int(m.group(1)) + 1
    else:
        base, n = stem, 1
    return dest.with_name(f"{base}({n}){suffix}")


def _reserve_dest(path: Path, multi_item: bool = False) -> tuple[Path, str | None]:
    """Resolve a duplicate-free dest and reserve it in-memory (no files created).

    Returns (dest, token). Pass the token to _release_reservation() when done.
    """
    with _resolve_lock:
        dest = resolve_duplicate(path, multi_item=multi_item)
        guard = 0
        while _reserve_key(dest, multi_item) in _reserved_keys and guard < 1000:
            dest = resolve_duplicate(_bump_suffix(dest), multi_item=multi_item)
            guard += 1
        token: str | None = _reserve_key(dest, multi_item)
        _reserved_keys.add(token)
        return dest, token


def _release_reservation(token: str | None) -> None:
    if token is None:
        return
    with _resolve_lock:
        _reserved_keys.discard(token)


def download(
    content: DetectedContent,
    choice: DownloadChoice,
    output_folder: Path,
    naming_template: str,
    max_retry: int = 3,
    cookies_browser: str | None = None,
    cookies_file: str | None = None,
) -> DownloadResult:
    """Download YouTube video/audio per the choice, with backoff retry for connection errors."""
    output_folder.mkdir(parents=True, exist_ok=True)

    ext = choice.fmt
    filename = build_filename(content.platform, content.title, ext, naming_template)

    entries_count = len(getattr(content, "entries", None) or [])
    playlist_all = getattr(choice, "playlist_mode", "single") == PLAYLIST_MODE_ALL and entries_count > 1
    # "noplaylist" has no effect for pure playlist URLs (yt-dlp #5215):
    # force the first entry when in single mode.
    force_single_item = not playlist_all and entries_count > 1

    dest, token = _reserve_dest(output_folder / filename, multi_item=playlist_all)

    ydl_opts = _build_ydl_opts(
        choice,
        dest,
        cookies_browser,
        cookies_file,
        force_single_item=force_single_item,
        playlist_all=playlist_all,
    )

    attempt = 0
    start_time = time.time()

    try:
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task(f"📥 {content.title[:40]}", total=None)
            ydl_opts["progress_hooks"] = [_make_progress_hook(progress, task_id)]

            while True:
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([content.url])
                    break
                except KeyboardInterrupt:
                    raise DownloadCancelled("Download dibatalkan oleh user") from None
                except yt_dlp.utils.DownloadError as e:
                    kind = _classify_error(e)
                    if kind == "cookies" and ("cookiesfrombrowser" in ydl_opts or "cookiefile" in ydl_opts):
                        ydl_opts.pop("cookiesfrombrowser", None)
                        ydl_opts.pop("cookiefile", None)
                        console.print(f"[yellow]{_friendly_message(kind)} - {t('dl.cookie_retry')}[/yellow]")
                        continue
                    if kind == "connection" and attempt < max_retry:
                        attempt += 1
                        delay = backoff_delay(attempt)
                        console.print(t("dl.retry", a=attempt, m=max_retry, d=delay))
                        time.sleep(delay)
                        continue
                    if kind == "format" and attempt < max_retry:
                        # SABR-only sessions come and go per request: a fresh
                        # extraction may get full formats again. Same backoff.
                        attempt += 1
                        delay = backoff_delay(attempt)
                        console.print(t("dl.retry", a=attempt, m=max_retry, d=delay))
                        time.sleep(delay)
                        continue
                    raise DownloadFailed(_friendly_message(kind)) from e
                except Exception as e:  # noqa: BLE001
                    raise DownloadFailed(_friendly_message(_classify_error(e))) from e
    except (DownloadCancelled, DownloadFailed) as e:
        if isinstance(e, DownloadFailed):
            salvaged = _salvage_media(dest, playlist_all)
            if salvaged is not None:
                path, size, count = salvaged
                console.print(f"[yellow]{t('dl.pp_warning')}[/yellow]")
                _cleanup_failed_dest(dest, playlist_all, keep={path})
                _release_reservation(token)
                return DownloadResult(
                    filepath=path,
                    size_bytes=size,
                    elapsed_seconds=time.time() - start_time,
                    file_count=count,
                )
        _cleanup_failed_dest(dest, playlist_all)
        _release_reservation(token)
        raise

    elapsed = time.time() - start_time
    final_path, total_size, file_count = _resolve_final_path(dest, multi_item=playlist_all)
    if total_size == 0:
        # yt-dlp reported success but left nothing (or an empty file):
        # expired stream URLs typically end like this. Never report these
        # as success, and don't leave 0-byte litter behind.
        _cleanup_failed_dest(dest, playlist_all)
        _release_reservation(token)
        raise DownloadFailed(t("dl.empty_result"))

    if choice.output_kind == "audio" and playlist_all and file_count > 1:
        _write_m3u_playlist(dest)

    _release_reservation(token)
    return DownloadResult(filepath=final_path, size_bytes=total_size, elapsed_seconds=elapsed, file_count=file_count)


_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _salvage_media(dest: Path, multi_item: bool = False) -> tuple[Path, int, int] | None:
    """Return (path, size, count) if a NON-EMPTY media file exists despite the failure.

    Post-processing (e.g. thumbnail embed) must never nuke an otherwise good
    download: a failed PP step on top of an intact video still counts.
    """
    matches = _find_result_files(dest, multi_item=multi_item)
    good = [p for p in matches if p.exists() and p.suffix.lower() not in _IMAGE_EXTS]
    good = [p for p in good if _safe_size(p) > 0]
    if not good:
        return None
    total = sum(_safe_size(p) for p in good)
    return good[0], total, len(good)


def _safe_size(p: Path) -> int:
    try:
        return p.stat().st_size
    except OSError:
        return 0


def _cleanup_failed_dest(dest: Path, multi_item: bool = False, keep: frozenset | set = frozenset()) -> None:
    """Remove 0-byte results and thumbnail leftovers of a failed download.

    Never touches non-empty media files: only 0-byte stem files and stem
    thumbnail litter from crashed runs.
    """
    try:
        if multi_item:
            candidates = find_indexed_files(dest)
        else:
            candidates = [p for p in _iter_dir_files(dest.parent) if p.is_file() and p.stem == dest.stem]
        for p in candidates:
            if p in keep:
                continue
            try:
                if p.suffix.lower() in _IMAGE_EXTS or _safe_size(p) == 0:
                    p.unlink()
            except OSError:
                pass
    except OSError:
        pass


def _write_m3u_playlist(dest: Path) -> Path | None:
    """Write a `.m3u` playlist next to audio `--playlist all` results. Best effort."""
    try:
        tracks = sorted(
            (p for p in _find_result_files(dest, multi_item=True) if p.suffix.lower() == ".mp3" and p.exists()),
            key=lambda p: p.name,
        )
        if len(tracks) < 2:
            return None
        m3u = dest.parent / (dest.stem + ".m3u")
        m3u.write_text("\n".join(p.name for p in tracks) + "\n", encoding="utf-8")
        return m3u
    except OSError:
        return None


def _find_result_files(dest: Path, multi_item: bool = False) -> list[Path]:
    """Find downloaded result file(s) matching `dest` (safe against glob chars in titles)."""
    if multi_item:
        return find_indexed_files(dest)

    if dest.exists():
        return [dest]

    image_exts = {".jpg", ".jpeg", ".png", ".webp"}
    stem = dest.stem
    matches: list[Path] = []
    non_image_matches: list[Path] = []
    for p in _iter_dir_files(dest.parent):
        if not p.is_file() or p.stem != stem:
            continue
        matches.append(p)
        if p.suffix.lower() not in image_exts:
            non_image_matches.append(p)

    if non_image_matches:
        return [sorted(non_image_matches, key=lambda p: p.name)[0]]
    if matches:
        return [sorted(matches, key=lambda p: p.name)[0]]
    return []


def _resolve_final_path(dest: Path, multi_item: bool = False) -> tuple[Path, int, int]:
    """Return (representative_path, total_size_bytes, file_count)."""
    matches = _find_result_files(dest, multi_item=multi_item)
    if not matches:
        return dest, 0, 0
    total_size = sum(m.stat().st_size for m in matches if m.exists())
    return matches[0], total_size, len(matches)


def _build_ydl_opts(
    choice: DownloadChoice,
    dest: Path,
    cookies_browser: str | None = None,
    cookies_file: str | None = None,
    force_single_item: bool = False,
    playlist_all: bool = False,
) -> dict:
    if playlist_all:
        outtmpl = f"{dest.with_suffix('')}-%(playlist_index,autonumber)d"
    else:
        outtmpl = str(dest.with_suffix(""))  # extension is left to yt-dlp/postprocessor

    opts = {
        "outtmpl": outtmpl + ".%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        # See detector._base_ydl_opts: raw noise goes to the log file only.
        "logger": get_ydl_logger(),
        "retries": 0,  # connection retries are handled manually (backoff) in download()
        "fragment_retries": 3,
        "continuedl": True,  # resume partial files (.part)
        # NOTE: do NOT set skip_unavailable_fragments=False here. yt-dlp's
        # default (True) skips dead fragments in flaky SABR/HLS sessions;
        # aborting on the first bad fragment turns one hiccup into a 0-byte
        # failure (seen live with ConnectionResetError mid-fragments).
        # Same as detector._base_ydl_opts: a JS runtime is needed for signature challenges.
        "js_runtimes": {"node": {}, "deno": {}, "bun": {}, "quickjs": {}},
        "noplaylist": not playlist_all,
        # No forced player_client (see detector._base_ydl_opts): yt-dlp
        # defaults survive YouTube's SABR-only sessions much better.
    }

    if force_single_item:
        opts["playlist_items"] = "1"

    apply_cookie_opts(opts, cookies_browser, cookies_file)

    if choice.output_kind == "video":
        opts["format"] = _quality_to_format_selector(choice.quality, choice.fmt)
        opts["merge_output_format"] = choice.fmt
        postprocessors: list[dict] = []
        if choice.fmt in EMBEDDABLE_VIDEO_FORMATS:
            postprocessors.append({"key": "EmbedThumbnail"})
            opts["writethumbnail"] = True
        else:
            opts["writethumbnail"] = False
        _apply_subs_metadata_opts(opts, postprocessors, choice)
        opts["postprocessors"] = postprocessors

    else:  # audio -> MP3
        opts["format"] = "bestaudio/best"
        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": _audio_quality_to_kbps(choice.quality),
            }
        ]
        _apply_subs_metadata_opts(opts, postprocessors, choice, audio=True)
        opts["postprocessors"] = postprocessors

    return opts


def _apply_subs_metadata_opts(opts: dict, postprocessors: list[dict], choice, audio: bool = False) -> None:
    """Add subtitle & metadata options to ydl opts (off by default)."""
    write_subs = bool(getattr(choice, "write_subs", False))
    if write_subs:
        langs = getattr(choice, "sub_langs", None) or list(SUBTITLE_LANGS_DEFAULT)
        opts["writesubtitles"] = True
        opts["subtitleslangs"] = langs
        if bool(getattr(choice, "embed_subs", False)) and not audio:
            opts["embedsubtitles"] = True
    if bool(getattr(choice, "embed_metadata", False)):
        postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})
    sponsor_cats = getattr(choice, "sponsorblock", None) or []
    if sponsor_cats:
        opts["sponsorblock_remove"] = list(sponsor_cats)
    if bool(getattr(choice, "write_info_json", False)):
        opts["writeinfojson"] = True
