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
    build_cookies_from_browser,
    build_filename,
    convert_image,
    find_indexed_files,
    resolve_duplicate,
)

# Re-export agar import lama tetap jalan.
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

# Backward-compat: dulu definisi lokal, sekarang kanonis di constants.
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
    file_count: int = 1  # >1 kalau multi-item (galeri/carousel via yt-dlp, bukan Instagram)


def _quality_to_format_selector(quality: str, ext: str) -> str:
    """
    Selector video. Diprioritaskan cari kombinasi video+audio yang codec-nya
    sudah kompatibel dengan container tujuan (mis. mp4 = h264+aac), biar
    ffmpeg tinggal remux (gabung) tanpa perlu re-encode ulang. Ini juga
    yang bikin proses gabung audio+video jauh lebih stabil.
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
    """Delay eksponensial untuk retry ke-`attempt` (1-indexed), dibatasi max + jitter.

    attempt=1 -> ~2s, 2 -> ~4s, 3 -> ~8s, ... capped di RETRY_MAX_DELAY_SECONDS.
    Jitter acak 0..RETRY_JITTER_SECONDS biar retry paralel tidak sinkron.
    """
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
) -> DownloadResult:
    """Download konten sesuai pilihan user, dengan retry otomatis untuk error koneksi."""
    output_folder.mkdir(parents=True, exist_ok=True)

    ext = choice.fmt
    filename = build_filename(content.platform, content.title, ext, naming_template)

    entries_count = len(getattr(content, "entries", None) or [])
    playlist_all = getattr(choice, "playlist_mode", "single") == PLAYLIST_MODE_ALL

    # Konten gambar multi-item (carousel/galeri yang terdeteksi via yt-dlp,
    # BUKAN instaloader - itu punya jalur download sendiri) butuh perlakuan
    # khusus: noplaylist harus dimatikan supaya semua/entry terpilih ikut
    # kedownload, outtmpl butuh index unik biar antar-entry tidak saling
    # timpa, dan selected_indices (dari "pilih nomor tertentu") perlu benar-
    # benar dipakai lewat playlist_items - sebelumnya diabaikan begitu saja.
    # PENTING: harus dihitung SEBELUM resolve_duplicate() dipanggil, karena
    # deteksi duplikat untuk multi-item butuh pola pencarian yang beda
    # (lihat docstring resolve_duplicate).
    is_multi_item = choice.output_kind == "image" and not choice.is_video_thumbnail and entries_count > 1

    # Playlist murni (VIDEO/AUDIO dengan entries > 1): default tetap single
    # (backward compat), tapi --playlist all memaksa semua entry dengan
    # outtmpl ber-index agar tidak saling timpa.
    is_playlist_all = playlist_all and not is_multi_item and entries_count > 1

    # Kasus SEBALIKNYA: content_type VIDEO/AUDIO tapi entries > 1 berarti
    # URL-nya sebenarnya playlist MURNI (tanpa parameter "v="), bukan galeri
    # gambar. "noplaylist" TIDAK berefek buat URL semacam ini - dikonfirmasi
    # langsung oleh maintainer yt-dlp sendiri (issue #5215, di-close sebagai
    # "expected behavior"): noplaylist cuma mencegah playlist ke-download
    # kalau URL-nya nunjuk video SPESIFIK di dalam playlist (ada "v="), sama
    # sekali gak berefek buat URL playlist murni. Tanpa penanganan ini,
    # seluruh playlist bakal kedownload dan semua entry saling menimpa nama
    # file yang sama (app ini didesain satu konten per URL, bukan playlist
    # manager) - playlist_items="1" memaksa cuma entry pertama yang diambil,
    # apa pun isi "noplaylist"-nya.
    force_single_item = not is_multi_item and not is_playlist_all and entries_count > 1

    dest = resolve_duplicate(output_folder / filename, multi_item=(is_multi_item or is_playlist_all))

    ydl_opts = _build_ydl_opts(
        choice,
        dest,
        cookies_browser,
        multi_item=is_multi_item,
        force_single_item=force_single_item,
        playlist_all=is_playlist_all,
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

    multi_result = is_multi_item or is_playlist_all
    if choice.output_kind == "image":
        # Bug: menu ask_image_choice() menawarkan JPG/PNG/WEBP untuk SEMUA
        # sumber gambar (thumbnail YouTube, galeri Pinterest/Reddit/X, dll),
        # tapi yt-dlp sendiri cuma nyimpen file dalam format asli sumbernya
        # (biasanya JPG) - pilihan PNG/WEBP diam-diam diabaikan kalau tidak
        # dikonversi manual di sini. convert_image() sama persis dengan yang
        # dipakai instagram_fallback.py, jadi konsisten di semua jalur gambar.
        result_files = _find_result_files(dest, multi_item=is_multi_item)
        converted_files = [convert_image(f, choice.fmt) for f in result_files]
        if not converted_files:
            final_path, total_size, file_count = dest, 0, 0
        else:
            final_path = converted_files[0]
            total_size = sum(f.stat().st_size for f in converted_files if f.exists())
            file_count = len(converted_files)
    else:
        final_path, total_size, file_count = _resolve_final_path(dest, multi_item=multi_result)

    return DownloadResult(filepath=final_path, size_bytes=total_size, elapsed_seconds=elapsed, file_count=file_count)


def _find_result_files(dest: Path, multi_item: bool = False) -> list[Path]:
    """
    Cari semua file hasil download yang cocok dengan `dest` (urut). Dipakai
    bareng oleh _resolve_final_path() (buat non-gambar) dan download() (buat
    gambar, sebelum tahap konversi format) - satu sumber logic pencarian
    file, biar tidak ada dua implementasi glob yang bisa saling berbeda
    perilaku (itu yang pernah bikin _resolve_final_path() ketinggalan waktu
    outtmpl multi-item pertama kali ditambahkan).
    """
    if multi_item:
        return find_indexed_files(dest)

    if dest.exists():
        return [dest]

    # FIX glob-injection: stem bisa mengandung `[`, `*`, `?` dari judul
    # asli. Jangan pakai `glob(f"{stem}.*")` mentah - iterdir + filter manual.
    image_exts = {".jpg", ".jpeg", ".png", ".webp"}
    stem = dest.stem
    matches: list[Path] = []
    non_image_matches: list[Path] = []
    for p in _iter_dir_files(dest.parent):
        if not p.is_file():
            continue
        if p.stem != stem and not p.name.startswith(stem + "."):
            continue
        # Pola "{stem}.*": nama harus persis stem + satu ekstensi.
        if p.stem != stem:
            continue
        matches.append(p)
        if p.suffix.lower() not in image_exts:
            non_image_matches.append(p)

    # Thumbnail sisa (.jpg/.png/.webp) sengaja diprioritaskan PALING TERAKHIR,
    # karena urutan glob() tidak dijamin dan kalau kebetulan thumbnail-nya yang
    # kepilih duluan, path & ukuran yang dilaporkan ke user jadi salah (nunjuk
    # ke gambar, bukan video/audio hasil download).
    if non_image_matches:
        return [sorted(non_image_matches, key=lambda p: p.name)[0]]
    if matches:
        return [sorted(matches, key=lambda p: p.name)[0]]
    return []


def _resolve_final_path(dest: Path, multi_item: bool = False) -> tuple[Path, int, int]:
    """
    Return (path_representatif, total_size_bytes, jumlah_file).

    yt-dlp kadang ganti ekstensi (mis. setelah postprocessing), dan untuk
    multi_item outtmpl-nya punya suffix index (lihat _build_ydl_opts), jadi
    TIDAK PERNAH ada file persis di `dest` - harus dicari lewat
    find_indexed_files(), bukan glob polos "{stem}.*". Kalau ini kepakai
    pola yang salah, aplikasi bakal lapor "sukses" tapi filepath-nya gak
    exist dan size 0, padahal file-nya beneran ada.

    Untuk multi_item, sengaja pakai find_indexed_files() (regex-anchored ke
    "-<angka>." di akhir nama) dan BUKAN glob "{stem}-*.*" polos, biar gak
    salah ikut nyomot file dari konten LAIN yang judulnya kebetulan numpuk
    sebagai prefix (mis. stem "Sunset" gak boleh kebawa "Sunset-Beach-1.jpg"
    milik konten "Sunset-Beach" yang beda).
    """
    matches = _find_result_files(dest, multi_item=multi_item)
    if not matches:
        return dest, 0, 0
    total_size = sum(m.stat().st_size for m in matches if m.exists())
    return matches[0], total_size, len(matches)


def _build_ydl_opts(
    choice: DownloadChoice,
    dest: Path,
    cookies_browser: str | None = None,
    multi_item: bool = False,
    force_single_item: bool = False,
    playlist_all: bool = False,
) -> dict:
    indexed = multi_item or playlist_all
    if indexed:
        # Sisipkan index unik di nama file, biar tiap entry carousel/galeri/
        # playlist tidak saling timpa satu sama lain (sebelumnya SEMUA entry
        # ditulis ke nama file yang sama persis, jadi cuma entry terakhir
        # yang tersisa).
        outtmpl = f"{dest.with_suffix('')}-%(playlist_index,autonumber)d"
    else:
        outtmpl = str(dest.with_suffix(""))  # ekstensi diserahkan ke yt-dlp/postprocessor

    opts = {
        "outtmpl": outtmpl + ".%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 0,  # retry koneksi ditangani manual (backoff) di download()
        "fragment_retries": 3,  # retry per-fragmen HLS/DASH tetap milik yt-dlp
        "continuedl": True,  # resume file parsial (.part), jangan ulang dari 0
        "skip_unavailable_fragments": False,
        # Default matikan playlist expansion - Lumenfetch didesain buat download
        # satu konten per URL, bukan playlist manager. Kalau ini dibiarkan aktif
        # (default yt-dlp), URL yang kebetulan mengandung parameter playlist bisa
        # diam-diam mendownload banyak entry dan saling menimpa nama file yang sama.
        # Cuma dibuka (False) untuk multi-item gambar & --playlist all yang disengaja.
        "noplaylist": not indexed,
        # Player client alternatif buat YouTube - membantu mengurangi kemunculan
        # error "Sign in to confirm you're not a bot" tanpa perlu cookies.
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }

    if force_single_item:
        # "noplaylist" TIDAK berefek buat URL playlist murni (tanpa "v=") -
        # dikonfirmasi maintainer yt-dlp sendiri (issue #5215, "expected
        # behavior" bukan bug yt-dlp). playlist_items="1" independen dari
        # noplaylist dan memaksa cuma entry PERTAMA yang diambil, apa pun
        # kondisinya - ini yang benar-benar mencegah seluruh playlist
        # kedownload dan saling menimpa nama file yang sama.
        opts["playlist_items"] = "1"

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
        postprocessors: list[dict] = []
        if choice.fmt in EMBEDDABLE_VIDEO_FORMATS:
            postprocessors.append({"key": "EmbedThumbnail"})
            opts["writethumbnail"] = True
        else:
            opts["writethumbnail"] = False
        _apply_subs_metadata_opts(opts, postprocessors, choice)
        opts["postprocessors"] = postprocessors

    elif choice.output_kind == "audio":
        opts["format"] = "bestaudio/best"
        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": choice.fmt,
                "preferredquality": _audio_quality_to_kbps(choice.quality),
            }
        ]
        _apply_subs_metadata_opts(opts, postprocessors, choice, audio=True)
        opts["postprocessors"] = postprocessors

    elif choice.output_kind == "image":
        if choice.is_video_thumbnail:
            # Ini "Gambar (thumbnail)" dari menu VIDEO - user cuma minta
            # thumbnail resmi dari platform, BUKAN video utuh. format="best"
            # di sini bakal salah pilih stream video kualitas terbaik dan
            # download-nya PENUH, cuma buat nanti "diconvert" jadi gambar
            # (hasilnya paling cuma frame pertama, boros bandwidth & waktu,
            # dan itu bukan thumbnail resmi platform sama sekali). Yang
            # bener: skip_download + writethumbnail, TANPA set "format" -
            # yt-dlp tinggal ambil file thumbnail-nya langsung.
            opts["skip_download"] = True
            opts["writethumbnail"] = True
        else:
            opts["format"] = "best"
            opts["skip_download"] = False

        if multi_item and choice.selected_indices:
            # selected_indices dari options.py 0-indexed (buat indexing Python list),
            # tapi playlist_items yt-dlp butuh 1-indexed dipisah koma. Tanpa ini,
            # pilihan "nomor tertentu" user diam-diam diabaikan dan semua entry
            # tetap kedownload (atau sebaliknya, cuma entry pertama yang kena).
            opts["playlist_items"] = ",".join(str(i + 1) for i in choice.selected_indices)

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
