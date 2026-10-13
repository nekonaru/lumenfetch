"""
downloader.py
Download video YouTube (MP4) / ekstrak audio (MP3) memakai yt-dlp,
dengan progress hook Rich, resume otomatis, dan retry backoff eksponensial.
"""

from __future__ import annotations

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

_HEIGHT_FILTERS = {
    "Best": "",
    "1080p": "[height<=1080]",
    "720p": "[height<=720]",
    "480p": "[height<=480]",
    "360p": "[height<=360]",
    "Worst": "",
}

_AUDIO_KBPS = {"Best": "0", "320kbps": "320", "192kbps": "192", "128kbps": "128"}


@dataclass
class DownloadResult:
    filepath: Path
    size_bytes: int
    elapsed_seconds: float
    file_count: int = 1  # >1 kalau --playlist all


def _quality_to_format_selector(quality: str, ext: str = "mp4") -> str:
    """
    Selector video: prioritaskan kombinasi video+audio yang codec-nya sudah
    kompatibel dengan MP4 (h264+aac) biar ffmpeg tinggal remux tanpa re-encode.
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
    """Wrapper kompatibel - logika kanonis di core.errors.classify_error."""
    return classify_error(e)


def _friendly_message(kind: str) -> str:
    return friendly_message(kind)


def backoff_delay(attempt: int) -> float:
    """Delay eksponensial untuk retry ke-`attempt` (1-indexed), dibatasi max + jitter."""
    import random

    base = RETRY_BASE_DELAY_SECONDS * (2.0 ** max(0, attempt - 1))
    capped = min(base, RETRY_MAX_DELAY_SECONDS)
    return capped + random.uniform(0, RETRY_JITTER_SECONDS)


def download(
    content: DetectedContent,
    choice: DownloadChoice,
    output_folder: Path,
    naming_template: str,
    max_retry: int = 3,
    cookies_browser: str | None = None,
    cookies_file: str | None = None,
) -> DownloadResult:
    """Download video/audio YouTube sesuai pilihan, retry backoff untuk error koneksi."""
    output_folder.mkdir(parents=True, exist_ok=True)

    ext = choice.fmt
    filename = build_filename(content.platform, content.title, ext, naming_template)

    entries_count = len(getattr(content, "entries", None) or [])
    playlist_all = getattr(choice, "playlist_mode", "single") == PLAYLIST_MODE_ALL and entries_count > 1
    # "noplaylist" tidak berefek untuk URL playlist murni (yt-dlp #5215):
    # paksa entry pertama bila mode single.
    force_single_item = not playlist_all and entries_count > 1

    dest = resolve_duplicate(output_folder / filename, multi_item=playlist_all)

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
                    console.print(
                        "[yellow]⚠️  Cookies browser gagal dibaca (tutup browser-nya) - lanjut tanpa cookies...[/yellow]"
                    )
                    continue
                if kind == "connection" and attempt < max_retry:
                    attempt += 1
                    delay = backoff_delay(attempt)
                    console.print(f"🔄 Retry {attempt}/{max_retry} dalam {delay:.0f}s...")
                    time.sleep(delay)
                    continue
                raise DownloadFailed(_friendly_message(kind)) from e
            except Exception as e:  # noqa: BLE001
                raise DownloadFailed(_friendly_message(_classify_error(e))) from e

    elapsed = time.time() - start_time
    final_path, total_size, file_count = _resolve_final_path(dest, multi_item=playlist_all)

    return DownloadResult(filepath=final_path, size_bytes=total_size, elapsed_seconds=elapsed, file_count=file_count)


def _find_result_files(dest: Path, multi_item: bool = False) -> list[Path]:
    """Cari file hasil download yang cocok dengan `dest` (aman dari karakter glob di judul)."""
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
    """Return (path_representatif, total_size_bytes, jumlah_file)."""
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
        outtmpl = str(dest.with_suffix(""))  # ekstensi diserahkan ke yt-dlp/postprocessor

    opts = {
        "outtmpl": outtmpl + ".%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 0,  # retry koneksi ditangani manual (backoff) di download()
        "fragment_retries": 3,
        "continuedl": True,  # resume file parsial (.part)
        "skip_unavailable_fragments": False,
        "noplaylist": not playlist_all,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
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
    """Tambahkan opsi subtitle & metadata ke ydl opts (default mati)."""
    write_subs = bool(getattr(choice, "write_subs", False))
    if write_subs:
        langs = getattr(choice, "sub_langs", None) or list(SUBTITLE_LANGS_DEFAULT)
        opts["writesubtitles"] = True
        opts["subtitleslangs"] = langs
        if bool(getattr(choice, "embed_subs", False)) and not audio:
            opts["embedsubtitles"] = True
    if bool(getattr(choice, "embed_metadata", False)):
        postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})
