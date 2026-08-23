"""
downloader.py
Logic download memakai yt-dlp (Python API, bukan subprocess),
dengan progress hook Rich dan retry otomatis untuk error koneksi.
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

from core.detector import DetectedContent
from core.options import DownloadChoice
from core.utils import build_cookies_from_browser, build_filename, resolve_duplicate

console = Console()

CONNECTION_ERROR_HINTS = ("timed out", "timeout", "connection", "network", "temporary failure", "reset by peer")

# Container video yang didukung EmbedThumbnailPP milik yt-dlp untuk video
# (subset dari daftar lengkapnya: mp3, mkv/mka, ogg/opus/flac, m4a/mp4/m4v/mov).
# WEBM sengaja TIDAK dimasukkan karena yt-dlp belum bisa embed thumbnail ke WEBM.
EMBEDDABLE_VIDEO_FORMATS = {"mp4", "mkv"}


class DownloadCancelled(Exception):
    """User cancel download (Ctrl+C)."""


class DownloadFailed(Exception):
    """Error fatal yang gak perlu di-retry (pesan sudah ramah)."""


@dataclass
class DownloadResult:
    filepath: Path
    size_bytes: int
    elapsed_seconds: float


def _quality_to_format_selector(quality: str, ext: str) -> str:
    """
    Selector video. Diprioritaskan cari kombinasi video+audio yang codec-nya
    sudah kompatibel dengan container tujuan (mis. mp4 = h264+aac), biar
    ffmpeg tinggal remux (gabung) tanpa perlu re-encode ulang. Ini juga
    yang bikin proses gabung audio+video jauh lebih stabil.
    """
    height_filters = {
        "Best": "",
        "1080p": "[height<=1080]",
        "720p": "[height<=720]",
        "480p": "[height<=480]",
        "360p": "[height<=360]",
        "Worst": "",
    }
    hf = height_filters.get(quality, "")

    if quality == "Worst":
        return f"worstvideo*{hf}+worstaudio/worst{hf}"

    if ext == "mp4":
        return (
            f"bestvideo[ext=mp4]{hf}+bestaudio[ext=m4a]/"
            f"bestvideo*{hf}+bestaudio/best{hf}"
        )
    return f"bestvideo*{hf}+bestaudio/best{hf}"


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
    cookies_browser: str | None = None,
) -> DownloadResult:
    """Download konten sesuai pilihan user, dengan retry otomatis untuk error koneksi."""
    output_folder.mkdir(parents=True, exist_ok=True)

    ext = choice.fmt
    filename = build_filename(content.platform, content.title, ext, naming_template)
    dest = resolve_duplicate(output_folder / filename)

    # Konten gambar multi-item (carousel/galeri yang terdeteksi via yt-dlp,
    # BUKAN instaloader - itu punya jalur download sendiri) butuh perlakuan
    # khusus: noplaylist harus dimatikan supaya semua/entry terpilih ikut
    # kedownload, outtmpl butuh index unik biar antar-entry tidak saling
    # timpa, dan selected_indices (dari "pilih nomor tertentu") perlu benar-
    # benar dipakai lewat playlist_items - sebelumnya diabaikan begitu saja.
    is_multi_item = choice.output_kind == "image" and len(getattr(content, "entries", None) or []) > 1

    ydl_opts = _build_ydl_opts(choice, dest, cookies_browser, multi_item=is_multi_item)

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
    """
    yt-dlp kadang ganti ekstensi (mis. setelah postprocessing). Cari file yang
    benar-benar ada. Thumbnail sisa (.jpg/.png/.webp) sengaja diprioritaskan
    PALING TERAKHIR, karena urutan glob() tidak dijamin dan kalau kebetulan
    thumbnail-nya yang kepilih duluan, path & ukuran yang dilaporkan ke user
    jadi salah (nunjuk ke gambar, bukan video/audio hasil download).
    """
    if dest.exists():
        return dest

    image_exts = {".jpg", ".jpeg", ".png", ".webp"}
    matches = list(dest.parent.glob(f"{dest.stem}.*"))
    non_image_matches = [m for m in matches if m.suffix.lower() not in image_exts]

    if non_image_matches:
        return non_image_matches[0]
    if matches:
        return matches[0]
    return dest


def _build_ydl_opts(
    choice: DownloadChoice,
    dest: Path,
    cookies_browser: str | None = None,
    multi_item: bool = False,
) -> dict:
    if multi_item:
        # Sisipkan index unik di nama file, biar tiap entry carousel/galeri
        # tidak saling timpa satu sama lain (sebelumnya SEMUA entry ditulis
        # ke nama file yang sama persis, jadi cuma entry terakhir yang tersisa).
        outtmpl = f"{dest.with_suffix('')}-%(playlist_index,autonumber)d"
    else:
        outtmpl = str(dest.with_suffix(""))  # ekstensi diserahkan ke yt-dlp/postprocessor

    opts = {
        "outtmpl": outtmpl + ".%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 0,  # retry ditangani manual di sini
        # Default matikan playlist expansion - Lumenfetch didesain buat download
        # satu konten per URL, bukan playlist manager. Kalau ini dibiarkan aktif
        # (default yt-dlp), URL yang kebetulan mengandung parameter playlist bisa
        # diam-diam mendownload banyak entry dan saling menimpa nama file yang sama.
        # Cuma dimatikan (False) untuk kasus gambar multi-item yang memang disengaja.
        "noplaylist": not multi_item,
        # Player client alternatif buat YouTube - membantu mengurangi kemunculan
        # error "Sign in to confirm you're not a bot" tanpa perlu cookies.
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }

    cookies = build_cookies_from_browser(cookies_browser)
    if cookies:
        opts["cookiesfrombrowser"] = cookies

    if choice.output_kind == "video":
        opts["format"] = _quality_to_format_selector(choice.quality, choice.fmt)
        opts["merge_output_format"] = choice.fmt
        # Merge audio+video ditangani otomatis oleh yt-dlp lewat merge_output_format.
        # EmbedThumbnail cuma didukung yt-dlp untuk container tertentu (mp3, mkv/mka,
        # ogg/opus/flac, m4a/mp4/m4v/mov) - WEBM TIDAK ada di daftar itu dan bakal
        # selalu raise EmbedThumbnailPPError kalau dipaksakan, padahal video-nya
        # sendiri sudah berhasil didownload utuh. Jadi thumbnail sengaja di-skip
        # khusus buat WEBM, bukan sekadar gagal diam-diam.
        if choice.fmt in EMBEDDABLE_VIDEO_FORMATS:
            opts["postprocessors"] = [{"key": "EmbedThumbnail"}]
            opts["writethumbnail"] = True
        else:
            opts["postprocessors"] = []
            opts["writethumbnail"] = False

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
        if multi_item and choice.selected_indices:
            # selected_indices dari options.py 0-indexed (buat indexing Python list),
            # tapi playlist_items yt-dlp butuh 1-indexed dipisah koma. Tanpa ini,
            # pilihan "nomor tertentu" user diam-diam diabaikan dan semua entry
            # tetap kedownload (atau sebaliknya, cuma entry pertama yang kena).
            opts["playlist_items"] = ",".join(str(i + 1) for i in choice.selected_indices)

    return opts
