"""cli.py - Argument parsing + non-interactive choice building. No business logic."""

from __future__ import annotations

import argparse
from pathlib import Path

from core.constants import (
    AUDIO_FORMAT,
    BATCH_DEFAULT_JOBS,
    BATCH_MAX_JOBS,
    PLAYLIST_MODE_ALL,
    PLAYLIST_MODE_SINGLE,
    SUBTITLE_LANGS_DEFAULT,
    VIDEO_FORMAT,
)
from core.options import DownloadChoice

__all__ = [
    "parse_args",
    "apply_cli_overrides",
    "build_choice_from_args",
    "read_batch_file",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="lumenfetch",
        description="YouTube downloader - MP4 & MP3.",
    )
    p.add_argument("url", nargs="?", default=None, help="YouTube video/playlist URL directly")
    p.add_argument("-t", "--type", dest="output_type", choices=["video", "audio"], default=None)
    p.add_argument("-f", "--format", dest="fmt", choices=["mp4", "mp3"], default=None)
    p.add_argument("-q", "--quality", default=None, help="Video quality (Best/1080p/720p/480p/360p/Worst) or MP3 bitrate (Best/320kbps/192kbps/128kbps)")
    p.add_argument("-o", "--output", default=None, help="Folder output (override config)")
    p.add_argument("--cookies", default=None, help="Browser cookies (chrome/firefox/edge/brave/opera/vivaldi/safari/none)")
    p.add_argument("--cookies-file", default=None, help="Netscape-format cookie file")
    p.add_argument("--max-retry", type=int, default=None)
    p.add_argument("--playlist", choices=[PLAYLIST_MODE_SINGLE, PLAYLIST_MODE_ALL], default=None)
    p.add_argument("--subs", action="store_true", help="Download subtitles when available")
    p.add_argument("--sub-langs", default=None, help="Subtitle languages, comma-separated (default: en,id)")
    p.add_argument("--embed-subs", action="store_true")
    p.add_argument("--embed-metadata", action="store_true")
    p.add_argument("--sponsorblock", nargs="*", default=None, help="Skip SponsorBlock segments (e.g. --sponsorblock sponsor intro outro)")
    p.add_argument("--write-info-json", action="store_true", help="Save video metadata as .info.json next to the file")
    p.add_argument("--batch", default=None, help="Text file with URLs (one per line)")
    p.add_argument("--jobs", type=int, default=BATCH_DEFAULT_JOBS, help=f"Batch parallelism 1-{BATCH_MAX_JOBS} (default 1)")
    p.add_argument("--no-clipboard", action="store_true")
    p.add_argument("--yes", "-y", action="store_true", help="Skip the filename confirmation")
    p.add_argument("--verbose", "-v", action="store_true", help="Detailed logging to file + console")
    p.add_argument("--ui-lang", choices=["en", "id"], default=None, help="Display language (default: en, remembered)")
    p.add_argument("--history", action="store_true", help="Show history and exit")
    p.add_argument("--doctor", action="store_true", help="Diagnose setup (ffmpeg, deps, cookies, network) and exit")
    p.add_argument("--version", action="store_true", help="Show the version")
    return p.parse_args(argv)


def apply_cli_overrides(choice: DownloadChoice, args: argparse.Namespace) -> DownloadChoice:
    """Apply CLI flags to DownloadChoice without extra prompts."""
    if args.playlist:
        choice.playlist_mode = args.playlist
    if args.subs:
        choice.write_subs = True
        if args.sub_langs:
            choice.sub_langs = [s.strip().lower() for s in str(args.sub_langs).replace(",", " ").split() if s.strip()]
        else:
            choice.sub_langs = list(SUBTITLE_LANGS_DEFAULT)
    if args.embed_subs:
        choice.write_subs = True
        if not choice.sub_langs:
            choice.sub_langs = list(SUBTITLE_LANGS_DEFAULT)
        choice.embed_subs = True
    if args.embed_metadata:
        choice.embed_metadata = True
    sponsor_cats = getattr(args, "sponsorblock", None)
    if sponsor_cats:
        choice.sponsorblock = [c.strip().lower() for c in sponsor_cats if c.strip()] or ["sponsor"]
    if getattr(args, "write_info_json", False):
        choice.write_info_json = True
    return choice


def build_choice_from_args(content, args: argparse.Namespace) -> DownloadChoice:
    """Build a non-interactive DownloadChoice from CLI flags."""
    kind = args.output_type or ("audio" if content.content_type == "AUDIO" else "video")
    if args.fmt:
        fmt = args.fmt.lower()
    else:
        fmt = AUDIO_FORMAT if kind == "audio" else VIDEO_FORMAT
    if kind == "audio" and fmt != AUDIO_FORMAT:
        fmt = AUDIO_FORMAT
    if kind == "video" and fmt != VIDEO_FORMAT:
        fmt = VIDEO_FORMAT
    choice = DownloadChoice(output_kind=kind, quality=args.quality or "Best", fmt=fmt)
    return apply_cli_overrides(choice, args)


def read_batch_file(path: str | Path) -> list[str]:
    """Read URLs from a text file (one per line, `#` = comment).

    Uses utf-8-sig so files saved with BOM (e.g. PowerShell Out-File)
    don't poison the first URL.
    """
    urls: list[str] = []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls
