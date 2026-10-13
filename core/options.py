"""
options.py
Semua prompt/menu interaktif (pilih output, quality, dll) memakai Rich.
Tidak ada logic download di sini.
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from core.constants import (
    AUDIO_FORMAT,
    AUDIO_QUALITIES,
    PLAYLIST_MODES,
    SUBTITLE_LANGS_DEFAULT,
    VERSION,
    VIDEO_FORMAT,
    VIDEO_QUALITIES,
)
from core.detector import DetectedContent
from core.utils import estimate_audio_size_bytes, estimate_video_size_bytes, format_duration, format_eta, format_size

console = Console()

__all__ = [
    "DownloadChoice",
    "VIDEO_QUALITIES",
    "AUDIO_QUALITIES",
    "PLAYLIST_MODES",
]


@dataclass
class DownloadChoice:
    output_kind: str  # "video" | "audio"
    quality: str = "Best"
    fmt: str = ""  # "mp4" untuk video, "mp3" untuk audio
    playlist_mode: str = "single"  # "single" | "all"
    write_subs: bool = False
    sub_langs: list[str] | None = None
    embed_subs: bool = False
    embed_metadata: bool = False


def show_header(version: str = VERSION) -> None:
    console.print(
        Panel.fit(
            f"[bold cyan]Lumenfetch[/bold cyan]  v{version}\n[dim]YouTube downloader (MP4/MP3)[/dim]",
            border_style="cyan",
        )
    )


def show_update_notice(installed_version: str, latest_version: str) -> None:
    console.print(
        Panel(
            f"yt-dlp kamu versi [bold]{installed_version}[/bold], "
            f"versi terbaru [bold green]{latest_version}[/bold green] sudah tersedia.\n"
            "[dim]YouTube sering ubah sistemnya, jadi update disarankan biar tetap kompatibel:[/dim]\n"
            "[bold cyan]pip install --upgrade yt-dlp[/bold cyan]",
            title="🔔 Update yt-dlp tersedia",
            border_style="yellow",
        )
    )


def show_content_panel(content: DetectedContent) -> None:
    count_text = f" ({len(content.entries)} video)" if content.entries else ""
    lines = [
        f"[bold]Judul[/bold]     : {content.title}",
        f"[bold]Tipe[/bold]      : {content.content_type}{count_text}",
    ]
    if content.duration:
        lines.append(f"[bold]Durasi[/bold]    : {format_duration(content.duration)}")
    console.print(Panel("\n".join(lines), title="✅ Video Terdeteksi", border_style="green"))


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
        idx = int(str(raw).strip()) - 1
        if 0 <= idx < len(choices):
            return choices[idx]
    except (ValueError, TypeError):
        pass
    return choices[default_index]


def ask_output_type() -> str:
    console.print("\nPilih tipe output:")
    console.print("  [1] Video (MP4)")
    console.print("  [2] Audio (MP3)")
    raw = Prompt.ask("→", default="1")
    return "audio" if str(raw).strip() == "2" else "video"


def _build_size_labels(
    formats: list[dict],
    qualities: list[str],
    duration: float | None,
    avg_speed_bps: float | None,
    estimator,
) -> list[str]:
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
    return DownloadChoice(output_kind="video", quality=quality, fmt=VIDEO_FORMAT)


def ask_audio_choice(content: DetectedContent | None = None, avg_speed_bps: float | None = None) -> DownloadChoice:
    extra = None
    if content is not None:
        formats = content.raw_info.get("formats") or []
        extra = _build_size_labels(formats, AUDIO_QUALITIES, content.duration, avg_speed_bps, estimate_audio_size_bytes)

    quality = _select_from_list("Pilih Quality (bitrate MP3):", AUDIO_QUALITIES, default_index=0, extra=extra)
    return DownloadChoice(output_kind="audio", quality=quality, fmt=AUDIO_FORMAT)


def ask_playlist_mode(total: int) -> str:
    """Tanya mode playlist: 1 video pertama (default) atau semua."""
    console.print(f"\nURL ini playlist berisi {total} video:")
    console.print("  [1] Download video pertama saja  (default)")
    console.print(f"  [2] Download semua ({total} video)")
    raw = Prompt.ask("→", default="1")
    return "all" if str(raw).strip() == "2" else "single"


def ask_subtitle_options() -> tuple[bool, list[str] | None, bool]:
    """Return (write_subs, sub_langs, embed_subs). Default mati."""
    console.print("\nDownload subtitle?")
    console.print("  [1] Tidak  (default)")
    console.print("  [2] Ya, download file subtitle")
    raw = Prompt.ask("→", default="1")
    if str(raw).strip() != "2":
        return False, None, False
    langs_raw = Prompt.ask("Bahasa subtitle (koma, mis. en,id)", default=",".join(SUBTITLE_LANGS_DEFAULT))
    langs = [p.strip().lower() for p in str(langs_raw).replace(",", " ").split() if p.strip()]
    embed = Confirm.ask("Embed subtitle ke file MP4?", default=False)
    return True, langs or list(SUBTITLE_LANGS_DEFAULT), bool(embed)


def ask_embed_metadata() -> bool:
    return Confirm.ask("Embed metadata (judul/artis) ke file hasil?", default=False)


def resolve_choice(content: DetectedContent, avg_speed_bps: float | None = None) -> DownloadChoice:
    """Alur pilihan dinamis: video YouTube -> tanya output, lalu quality."""
    if content.content_type == "AUDIO":
        return ask_audio_choice(content, avg_speed_bps)
    kind = ask_output_type()
    if kind == "audio":
        return ask_audio_choice(content, avg_speed_bps)
    return ask_video_choice(content, avg_speed_bps)


def confirm_filename(filename: str) -> bool:
    console.print(f"\n📄 Nama file: [bold]{filename}[/bold]")
    return Confirm.ask("Lanjutkan?", default=True)


def ask_again_or_url() -> bool | str:
    """Prompt lanjutan yang toleran terhadap paste URL langsung."""
    from core.detector import is_valid_url  # noqa: PLC0415 - hindari circular import

    while True:
        raw = Prompt.ask("\nDownload lagi? [y/n] [dim](atau paste URL langsung)[/dim]", default="y").strip()
        if is_valid_url(raw):
            return raw
        low = raw.lower()
        if low in ("y", "yes") or low.startswith("y"):
            return True
        if low in ("n", "no", "q", "quit") or low.startswith("n"):
            return False
        console.print("[red]Jawab y/n, atau paste URL langsung.[/red]")


def ask_again() -> bool:
    return Confirm.ask("\nDownload lagi?", default=True)


def show_history_table(history: list[dict]) -> None:
    if not history:
        console.print("[dim]Belum ada riwayat download.[/dim]")
        return

    table = Table(title="Riwayat Download (20 terakhir)")
    for col in ("No", "Tanggal", "Judul", "Format", "Ukuran", "Status"):
        table.add_column(col)

    for i, entry in enumerate(history, start=1):
        if not isinstance(entry, dict):
            continue
        status = "✅" if entry.get("success") else "❌"
        table.add_row(
            str(i),
            str(entry.get("date") or "-"),
            str(entry.get("title") or "-")[:40],
            str(entry.get("format") or "-"),
            str(entry.get("size") or "-"),
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
            "1. Paste link video YouTube\n"
            "2. Pilih output Video (MP4) / Audio (MP3)\n"
            "3. Pilih quality\n"
            "4. Tunggu download selesai\n\n"
            "[bold]CANCEL DOWNLOAD[/bold]\n"
            "Tekan Ctrl+C saat download berjalan",
            title="📖 Lumenfetch Help",
            border_style="blue",
        )
    )


def show_settings_menu(config: dict) -> str:
    cookies_status = config.get("cookies_browser") or config.get("cookies_file") or "none"
    console.print("\n[bold]Settings[/bold]")
    console.print(f"  [1] Ganti folder download default  [dim](saat ini: {config['download_folder']})[/dim]")
    console.print(f"  [2] Ganti max retry  [dim](saat ini: {config['max_retry']})[/dim]")
    console.print(f"  [3] Toggle auto-paste clipboard  [dim](saat ini: {'ON' if config['auto_paste'] else 'OFF'})[/dim]")
    console.print(f"  [4] Ganti naming template  [dim](saat ini: {config['naming_template']})[/dim]")
    console.print(f"  [5] Pakai cookies dari browser/file  [dim](saat ini: {cookies_status})[/dim]")
    console.print("  [6] Reset ke default")
    console.print("  [7] Kembali")
    return Prompt.ask("→", default="7")


def ask_cookies_browser() -> str | None:
    """Minta user pilih browser buat ambil cookies (konten age-restricted/private)."""
    console.print(
        "\n[dim]Dipakai buat video yang minta login / age-restricted.[/dim]\n"
        "[dim]Pastikan kamu sudah login ke YouTube di browser pilihanmu.[/dim]"
    )
    labels = ["Nonaktifkan", "Chrome", "Firefox", "Edge", "Brave", "Opera", "Vivaldi", "Safari"]
    values: list[str | None] = [None, "chrome", "firefox", "edge", "brave", "opera", "vivaldi", "safari"]
    for i, label in enumerate(labels):
        console.print(f"  [{i + 1}] {label}")
    raw = Prompt.ask("→", default="1")
    try:
        idx = int(str(raw).strip()) - 1
        if 0 <= idx < len(values):
            return values[idx]
    except (ValueError, TypeError):
        pass
    return None
