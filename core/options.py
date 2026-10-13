"""
options.py
Semua prompt/menu interaktif (pilih output, quality, dll) memakai Rich.
Tidak ada logic download di sini. Bahasa mengikuti core.i18n (default English).
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
from core.i18n import t
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
            t("update.body", installed=installed_version, latest=latest_version),
            title=t("update.title"),
            border_style="yellow",
        )
    )


def show_content_panel(content: DetectedContent) -> None:
    if content.entries:
        n = len(content.entries)
        count_text = f" {t('panel.video_one', n=n) if n == 1 else t('panel.video_many', n=n)}"
    else:
        count_text = ""

    lines = [
        f"[bold]{t('panel.title_label')}[/bold]     : {content.title}",
        f"[bold]{t('panel.type_label')}[/bold]      : {content.content_type}{count_text}",
    ]
    if content.duration:
        lines.append(f"[bold]{t('panel.duration_label')}[/bold]    : {format_duration(content.duration)}")

    console.print(Panel("\n".join(lines), title=t("panel.title"), border_style="green"))


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
    console.print(t("out.prompt"))
    console.print(f"  [1] {t('out.video')}")
    console.print(f"  [2] {t('out.audio')}")
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

    quality = _select_from_list(t("q.video"), VIDEO_QUALITIES, default_index=0, extra=extra)
    return DownloadChoice(output_kind="video", quality=quality, fmt=VIDEO_FORMAT)


def ask_audio_choice(content: DetectedContent | None = None, avg_speed_bps: float | None = None) -> DownloadChoice:
    extra = None
    if content is not None:
        formats = content.raw_info.get("formats") or []
        extra = _build_size_labels(formats, AUDIO_QUALITIES, content.duration, avg_speed_bps, estimate_audio_size_bytes)

    quality = _select_from_list(t("q.audio"), AUDIO_QUALITIES, default_index=0, extra=extra)
    return DownloadChoice(output_kind="audio", quality=quality, fmt=AUDIO_FORMAT)


def ask_playlist_mode(total: int) -> str:
    """Tanya mode playlist: 1 video pertama (default) atau semua."""
    console.print(t("pl.prompt", total=total))
    console.print(f"  [1] {t('pl.single')}")
    console.print(f"  [2] {t('pl.all', total=total)}")
    raw = Prompt.ask("→", default="1")
    return "all" if str(raw).strip() == "2" else "single"


def ask_subtitle_options() -> tuple[bool, list[str] | None, bool]:
    """Return (write_subs, sub_langs, embed_subs). Default mati."""
    console.print(t("subs.prompt"))
    console.print(f"  [1] {t('subs.no')}")
    console.print(f"  [2] {t('subs.yes')}")
    raw = Prompt.ask("→", default="1")
    if str(raw).strip() != "2":
        return False, None, False
    langs_raw = Prompt.ask(t("subs.langs"), default=",".join(SUBTITLE_LANGS_DEFAULT))
    langs = [p.strip().lower() for p in str(langs_raw).replace(",", " ").split() if p.strip()]
    embed = Confirm.ask(t("subs.embed"), default=False)
    return True, langs or list(SUBTITLE_LANGS_DEFAULT), bool(embed)


def ask_embed_metadata() -> bool:
    return Confirm.ask(t("meta.prompt"), default=False)


def resolve_choice(content: DetectedContent, avg_speed_bps: float | None = None) -> DownloadChoice:
    """Alur pilihan dinamis: video YouTube -> tanya output, lalu quality."""
    if content.content_type == "AUDIO":
        return ask_audio_choice(content, avg_speed_bps)
    kind = ask_output_type()
    if kind == "audio":
        return ask_audio_choice(content, avg_speed_bps)
    return ask_video_choice(content, avg_speed_bps)


def confirm_filename(filename: str) -> bool:
    console.print(t("confirm.file", name=filename))
    return Confirm.ask(t("confirm.go"), default=True)


def ask_again_or_url() -> bool | str:
    """Prompt lanjutan yang toleran terhadap paste URL langsung."""
    from core.detector import is_valid_url  # noqa: PLC0415 - hindari circular import

    while True:
        raw = Prompt.ask(t("again.prompt"), default="y").strip()
        if is_valid_url(raw):
            return raw
        low = raw.lower()
        if low in ("y", "yes") or low.startswith("y"):
            return True
        if low in ("n", "no", "q", "quit") or low.startswith("n"):
            return False
        console.print(t("again.invalid"))


def ask_again() -> bool:
    return Confirm.ask(t("again.ask"), default=True)


def show_history_table(history: list[dict]) -> None:
    if not history:
        console.print(t("hist.empty"))
        return

    table = Table(title=t("hist.title"))
    for col in ("hist.col_no", "hist.col_date", "hist.col_title", "hist.col_format", "hist.col_size", "hist.col_status"):
        table.add_column(t(col))

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
    console.print(Panel(t("help.text"), title=t("help.title"), border_style="blue"))


def show_settings_menu(config: dict) -> str:
    cookies_status = config.get("cookies_browser") or config.get("cookies_file") or "none"
    console.print(t("set.title"))
    console.print(f"  [1] {t('set.folder')}  {t('set.current', v=config['download_folder'])}")
    console.print(f"  [2] {t('set.retry')}  {t('set.current', v=config['max_retry'])}")
    on_off = t("set.on") if config["auto_paste"] else t("set.off")
    console.print(f"  [3] {t('set.autopaste')}  {t('set.current', v=on_off)}")
    console.print(f"  [4] {t('set.template')}  {t('set.current', v=config['naming_template'])}")
    console.print(f"  [5] {t('set.cookies')}  {t('set.current', v=cookies_status)}")
    console.print(f"  [6] {t('set.reset')}")
    console.print(f"  [7] {t('set.back')}")
    return Prompt.ask("→", default="7")


def ask_cookies_browser() -> str | None:
    """Minta user pilih browser buat ambil cookies (konten age-restricted/private)."""
    console.print(t("cookie.info1"))
    console.print(t("cookie.info2"))
    labels = [t("cookie.disable"), "Chrome", "Firefox", "Edge", "Brave", "Opera", "Vivaldi", "Safari"]
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
