"""
downloader.py
Logic download memakai yt-dlp (Python API, bukan subprocess),
dengan progress hook Rich dan retry otomatis untuk error koneksi.
"""

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

from core.detector import DetectedContent
from core.options import DownloadChoice
from core.utils import build_filename, resolve_duplicate

console = Console()

CONNECTION_ERROR_HINTS = ("timed out", "timeout", "connection", "network", "temporary failure", "reset by peer")


class DownloadCancelled(Exception):
    """User cancel download (Ctrl+C)."""


class DownloadFailed(Exception):
    """Error fatal yang gak perlu di-retry (pesan sudah ramah)."""


@dataclass
class DownloadResult:
    filepath: Path
    size_bytes: int
    elapsed_seconds: float


def _quality_to_format_selector(quality: str) -> str:
    mapping = {
        "Best": "bestvideo*+bestaudio/best",
        "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
        "Worst": "worstvideo*+worstaudio/worst",
    }
    return mapping.get(quality, "bestvideo*+bestaudio/best")


def _audio_quality_to_kbps(quality: str) -> str:
    mapping = {"Best": "0", "320kbps": "320", "192kbps": "192", "128kbps": "128"}
    return mapping.get(quality, "0")


def _make_progress_hook(progress: Progress, task_id):
    def hook(d: dict):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                progress.update(task_id, total=total, completed=downloaded)
            progress.update(task_id, description=d.get("filename", "Downloading")[:40])
        elif d.get("status") == "finished":
            progress.update(task_id, completed=progress.tasks[task_id].total or 0)

    return hook


def _classify_error(e: Exception) -> str:
    msg = str(e).lower()
    if any(hint in msg for hint in CONNECTION_ERROR_HINTS):
        return "connection"
    if "private" in msg or "login required" in msg or "unavailable" in msg:
        return "private"
    if "requested format is not available" in msg or "no video formats" in msg:
        return "format"
    if "no space left" in msg:
        return "disk"
    return "unknown"


def _friendly_message(kind: str) -> str:
    return {
        "connection": "❌ Koneksi internet bermasalah, coba lagi",
        "private": "❌ Konten ini private / tidak bisa diakses",
        "format": "❌ Format tidak tersedia untuk konten ini",
        "disk": "❌ Tidak cukup ruang disk",
        "unknown": "❌ Terjadi kesalahan saat download",
    }[kind]


def download(
    content: DetectedContent,
    choice: DownloadChoice,
    output_folder: Path,
    naming_template: str,
    max_retry: int = 3,
) -> DownloadResult:
    """Download konten sesuai pilihan user, dengan retry otomatis untuk error koneksi."""
    output_folder.mkdir(parents=True, exist_ok=True)

    ext = choice.fmt if choice.output_kind != "video" else choice.fmt
    filename = build_filename(content.platform, content.title, ext, naming_template)
    dest = resolve_duplicate(output_folder / filename)

    ydl_opts = _build_ydl_opts(choice, dest)

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
                if kind == "connection" and attempt < max_retry:
                    attempt += 1
                    console.print(f"🔄 Retry {attempt}/{max_retry}...")
                    time.sleep(2)
                    continue
                raise DownloadFailed(_friendly_message(kind)) from e
            except Exception as e:  # noqa: BLE001
                raise DownloadFailed(_friendly_message(_classify_error(e))) from e

    elapsed = time.time() - start_time
    final_path = _resolve_final_path(dest)
    size = final_path.stat().st_size if final_path.exists() else 0

    return DownloadResult(filepath=final_path, size_bytes=size, elapsed_seconds=elapsed)


def _resolve_final_path(dest: Path) -> Path:
    """yt-dlp kadang ganti ekstensi (mis. setelah postprocessing). Cari file yang benar-benar ada."""
    if dest.exists():
        return dest
    matches = list(dest.parent.glob(f"{dest.stem}.*"))
    return matches[0] if matches else dest


def _build_ydl_opts(choice: DownloadChoice, dest: Path) -> dict:
    outtmpl = str(dest.with_suffix(""))  # ekstensi diserahkan ke yt-dlp/postprocessor
    opts = {
        "outtmpl": outtmpl + ".%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 0,  # retry ditangani manual di sini
    }

    if choice.output_kind == "video":
        opts["format"] = _quality_to_format_selector(choice.quality)
        opts["merge_output_format"] = choice.fmt
        opts["postprocessors"] = [
            {"key": "FFmpegVideoConvertor", "preferedformat": choice.fmt},
            {"key": "EmbedThumbnail"},
        ]
        opts["writethumbnail"] = True

    elif choice.output_kind == "audio":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": choice.fmt,
                "preferredquality": _audio_quality_to_kbps(choice.quality),
            }
        ]

    elif choice.output_kind == "image":
        opts["format"] = "best"
        opts["skip_download"] = False

    return opts
