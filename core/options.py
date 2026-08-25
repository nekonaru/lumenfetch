"""
options.py
Semua prompt/menu interaktif (pilih tipe output, quality, format, dll)
memakai Rich. Tidak ada logic download di sini.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from core.detector import DetectedContent
from core.utils import estimate_audio_size_bytes, estimate_video_size_bytes, format_duration, format_eta, format_size

console = Console()

VIDEO_QUALITIES = ["Best", "1080p", "720p", "480p", "360p", "Worst"]
VIDEO_FORMATS = ["MP4", "WEBM", "MKV"]
AUDIO_FORMATS = ["MP3", "M4A", "WAV", "FLAC"]
AUDIO_QUALITIES = ["Best", "320kbps", "192kbps", "128kbps"]
IMAGE_FORMATS = ["JPG", "PNG", "WEBP"]


@dataclass
class DownloadChoice:
    output_kind: str  # "video" | "audio" | "image"
    quality: str = "Best"
    fmt: str = ""
    selected_indices: list[int] | None = None  # untuk carousel
    is_video_thumbnail: bool = False  # True kalau ini "Gambar (thumbnail)" dari menu VIDEO


def show_header(version: str = "1.0.0") -> None:
    console.print(
        Panel.fit(
            f"[bold cyan]Lumenfetch[/bold cyan]  v{version}\n"
            "[dim]Powered by yt-dlp[/dim]",
            border_style="cyan",
        )
    )


def show_update_notice(installed_version: str, latest_version: str) -> None:
    console.print(
        Panel(
            f"yt-dlp kamu versi [bold]{installed_version}[/bold], "
            f"versi terbaru [bold green]{latest_version}[/bold green] sudah tersedia.\n"
            "[dim]Platform (YouTube/TikTok/Instagram/dll) sering ubah sistem mereka, "
            "jadi update yt-dlp disarankan biar tetap kompatibel:[/dim]\n"
            "[bold cyan]pip install --upgrade yt-dlp[/bold cyan]",
            title="🔔 Update yt-dlp tersedia",
            border_style="yellow",
        )
    )


def show_content_panel(content: DetectedContent) -> None:
    lines = [
        f"[bold]Platform[/bold]  : {content.platform}",
        f"[bold]Judul[/bold]     : {content.title}",
        f"[bold]Tipe[/bold]      : {content.content_type}"
        + (f" ({len(content.entries)} gambar)" if content.content_type == "IMAGE" and content.entries else ""),
    ]
    if content.duration:
        lines.append(f"[bold]Durasi[/bold]    : {format_duration(content.duration)}")

    console.print(Panel("\n".join(lines), title="✅ Konten Terdeteksi", border_style="green"))


def _select_from_list(
    prompt_text: str,
    choices: list[str],
    default_index: int = 0,
    extra: list[str] | None = None,
) -> str:
    console.print(f"\n{prompt_text}")
    for i, c in enumerate(choices):
        line = f"  [{i + 1}] {c}"
        if i == default_index:
            line += "  (default)"
        if extra and extra[i]:
            line += f"  [dim]{extra[i]}[/dim]"
        console.print(line)

    raw = Prompt.ask("→", default=str(default_index + 1))
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(choices):
            return choices[idx]
    except ValueError:
        pass
    return choices[default_index]


def ask_output_type_for_video() -> str:
    console.print("\nPilih tipe output:")
    console.print("  [1] Video")
    console.print("  [2] Audio")
    console.print("  [3] Gambar (thumbnail)")
    raw = Prompt.ask("→", default="1")
    mapping = {"1": "video", "2": "audio", "3": "image"}
    return mapping.get(raw.strip(), "video")


def _build_size_labels(
    formats: list[dict],
    qualities: list[str],
    duration: float | None,
    avg_speed_bps: float | None,
    estimator,
) -> list[str]:
    """
    Bikin label "(~85 MB, ~14 detik)" per opsi quality. Kalau ukurannya gak
    bisa diestimasi (platform gak expose filesize/bitrate), labelnya kosong
    aja - lebih baik gak nampilin apa-apa daripada nampilin angka ngasal.
    """
    labels = []
    for quality in qualities:
        size_bytes = estimator(formats, quality, duration)
        if size_bytes is None:
            labels.append("")
            continue
        size_text = f"~{format_size(size_bytes)}"
        eta_text = format_eta(size_bytes, avg_speed_bps)
        labels.append(f"({size_text}, {eta_text})" if eta_text else f"({size_text})")
    return labels


def ask_video_choice(content: DetectedContent | None = None, avg_speed_bps: float | None = None) -> DownloadChoice:
    extra = None
    if content is not None:
        formats = content.raw_info.get("formats") or []
        extra = _build_size_labels(formats, VIDEO_QUALITIES, content.duration, avg_speed_bps, estimate_video_size_bytes)

    quality = _select_from_list("Pilih Quality:", VIDEO_QUALITIES, default_index=0, extra=extra)
    fmt = _select_from_list("Pilih Format:", VIDEO_FORMATS, default_index=0)
    return DownloadChoice(output_kind="video", quality=quality, fmt=fmt.lower())


def ask_audio_choice(content: DetectedContent | None = None, avg_speed_bps: float | None = None) -> DownloadChoice:
    fmt = _select_from_list("Pilih Format:", AUDIO_FORMATS, default_index=0)

    extra = None
    if content is not None:
        formats = content.raw_info.get("formats") or []
        extra = _build_size_labels(formats, AUDIO_QUALITIES, content.duration, avg_speed_bps, estimate_audio_size_bytes)

    quality = _select_from_list("Pilih Quality:", AUDIO_QUALITIES, default_index=0, extra=extra)
    return DownloadChoice(output_kind="audio", quality=quality, fmt=fmt.lower())


def ask_image_choice(content: DetectedContent, is_video_thumbnail: bool = False) -> DownloadChoice:
    fmt = _select_from_list("Pilih Format:", IMAGE_FORMATS, default_index=0)
    choice = DownloadChoice(output_kind="image", fmt=fmt.lower(), is_video_thumbnail=is_video_thumbnail)

    if content.entries and len(content.entries) > 1:
        console.print("\nPilih gambar:")
        console.print(f"  [1] Download semua ({len(content.entries)} gambar)")
        console.print("  [2] Pilih tertentu")
        raw = Prompt.ask("→", default="1")
        if raw.strip() == "2":
            nums = Prompt.ask("Nomor gambar (contoh: 1,3,5) [dim](kosongkan = semua)[/dim]", default="")
            nums = nums.strip()
            if not nums:
                choice.selected_indices = None  # kosong / enter doang -> download semua
            else:
                try:
                    parsed = [int(n.strip()) - 1 for n in nums.split(",") if n.strip()]
                except ValueError:
                    parsed = None

                if parsed is None:
                    choice.selected_indices = None
                else:
                    # Nomor yang di luar jangkauan (mis. entries cuma 5 tapi
                    # user ketik "99") disaring dulu, biar gak diam-diam
                    # jadi "0 gambar terdownload" - konsisten sama fallback
                    # yang sudah ada di instagram_fallback.py.
                    valid = [i for i in parsed if 0 <= i < len(content.entries)]
                    if not valid:
                        console.print(
                            "[yellow]Nomor yang dimasukkan tidak valid - download semua gambar sebagai gantinya.[/yellow]"
                        )
                        choice.selected_indices = None
                    else:
                        choice.selected_indices = valid
    return choice


def resolve_choice(content: DetectedContent, avg_speed_bps: float | None = None) -> DownloadChoice:
    """Alur pilihan dinamis sesuai tipe konten terdeteksi."""
    if content.content_type == "VIDEO":
        kind = ask_output_type_for_video()
        if kind == "video":
            return ask_video_choice(content, avg_speed_bps)
        if kind == "audio":
            return ask_audio_choice(content, avg_speed_bps)
        return ask_image_choice(content, is_video_thumbnail=True)

    if content.content_type == "AUDIO":
        return ask_audio_choice(content, avg_speed_bps)

    return ask_image_choice(content)


def ask_output_folder(default_folder: str) -> Path:
    raw = Prompt.ask(f"\nFolder output [dim](default: {default_folder})[/dim]", default=default_folder)
    return Path(raw or default_folder)


def confirm_filename(filename: str) -> bool:
    console.print(f"\n📄 Nama file: [bold]{filename}[/bold]")
    return Confirm.ask("Lanjutkan?", default=True)


def ask_again() -> bool:
    return Confirm.ask("\nDownload lagi?", default=True)


def show_history_table(history: list[dict]) -> None:
    if not history:
        console.print("[dim]Belum ada riwayat download.[/dim]")
        return

    table = Table(title="Riwayat Download (20 terakhir)")
    for col in ("No", "Tanggal", "Platform", "Judul", "Format", "Ukuran", "Status"):
        table.add_column(col)

    for i, entry in enumerate(history, start=1):
        status = "✅" if entry.get("success") else "❌"
        table.add_row(
            str(i),
            entry.get("date", "-"),
            entry.get("platform", "-"),
            (entry.get("title", "-") or "-")[:40],
            entry.get("format", "-"),
            entry.get("size", "-"),
            status,
        )
    console.print(table)


def show_help() -> None:
    console.print(
        Panel(
            "[bold]COMMAND TERSEDIA[/bold]\n"
            "history   Lihat riwayat download\n"
            "settings  Buka pengaturan\n"
            "help      Tampilkan halaman ini\n"
            "q/quit    Keluar dari aplikasi\n\n"
            "[bold]CARA PAKAI[/bold]\n"
            "1. Paste URL dari platform apapun\n"
            "2. Pilih tipe output yang diinginkan\n"
            "3. Pilih format & quality\n"
            "4. Tunggu download selesai\n\n"
            "[bold]PLATFORM DIDUKUNG[/bold]\n"
            "YouTube, TikTok, Instagram, Facebook,\n"
            "X/Twitter, Threads, Pinterest, Reddit,\n"
            "+ 1000 lainnya\n\n"
            "[bold]CANCEL DOWNLOAD[/bold]\n"
            "Tekan Ctrl+C saat download berjalan",
            title="📖 Lumenfetch Help",
            border_style="blue",
        )
    )


def show_settings_menu(config: dict) -> str:
    cookies_status = config.get("cookies_browser") or "none"
    console.print("\n[bold]Settings[/bold]")
    console.print(f"  [1] Ganti folder download default  [dim](saat ini: {config['download_folder']})[/dim]")
    console.print(f"  [2] Ganti max retry  [dim](saat ini: {config['max_retry']})[/dim]")
    console.print(f"  [3] Toggle auto-paste clipboard  [dim](saat ini: {'ON' if config['auto_paste'] else 'OFF'})[/dim]")
    console.print(f"  [4] Ganti naming template  [dim](saat ini: {config['naming_template']})[/dim]")
    console.print(f"  [5] Pakai cookies dari browser  [dim](saat ini: {cookies_status})[/dim]")
    console.print("  [6] Reset ke default")
    console.print("  [7] Kembali")
    return Prompt.ask("→", default="7")


def ask_cookies_browser() -> str:
    """Minta user pilih browser buat ambil cookies (buat konten yang butuh login)."""
    console.print(
        "\n[dim]Dipakai buat konten yang minta login (misal Instagram).[/dim]\n"
        "[dim]Pastikan kamu sudah login ke platform tersebut di browser pilihanmu.[/dim]"
    )
    labels = ["Nonaktifkan", "Chrome", "Firefox", "Edge", "Brave", "Opera", "Vivaldi", "Safari"]
    values = ["none", "chrome", "firefox", "edge", "brave", "opera", "vivaldi", "safari"]
    for i, label in enumerate(labels):
        console.print(f"  [{i + 1}] {label}")
    raw = Prompt.ask("→", default="1")
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(values):
            return values[idx]
    except ValueError:
        pass
    return "none"
