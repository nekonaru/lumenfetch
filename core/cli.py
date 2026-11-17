"""cli.py - Argument parsing + non-interactive choice building. No business logic."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import TYPE_CHECKING

from core.constants import (
    AUDIO_FORMAT,
    BATCH_DEFAULT_JOBS,
    BATCH_MAX_JOBS,
    PLAYLIST_MODE_ALL,
    PLAYLIST_MODE_SINGLE,
    SUBTITLE_LANGS_DEFAULT,
    VIDEO_FORMAT,
)

if TYPE_CHECKING:
    # Only needed for annotations; importing it at runtime pulls in rich.
    from core.options import DownloadChoice

_RATE_RE = re.compile(r"^([0-9]+(?:\.[0-9]+)?)\s*([BKMGT])?B?$", re.IGNORECASE)
_FRAGMENTS_RE = re.compile(r"^[0-9]{1,2}$")
_PLAYLIST_ITEMS_RE = re.compile(r"^[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*$")
_RATE_UNITS = {"B": 1, "K": 1024, "M": 1024 * 1024, "G": 1024 * 1024 * 1024, "T": 1024 * 1024 * 1024 * 1024}

__all__ = [
    "parse_args",
    "apply_cli_overrides",
    "build_choice_from_args",
    "read_batch_file",
    "parse_rate",
]


def parse_rate(value: str) -> int:
    """Parse a rate like '512K', '2M', '1048576', or '2MB' into bytes per second."""
    m = _RATE_RE.match(str(value).strip())
    if not m:
        raise argparse.ArgumentTypeError(f"expected a rate like '512K', '2M' or plain bytes, got {value!r}")
    if m.group(2) is None and "." in m.group(1):
        raise argparse.ArgumentTypeError(f"a fractional rate needs a unit, e.g. '1.5M', got {value!r}")
    number = float(m.group(1))
    unit = (m.group(2) or "B").upper()
    rate = int(number * _RATE_UNITS[unit])
    if rate <= 0:
        raise argparse.ArgumentTypeError("rate must be positive")
    return rate


def _fragments_arg(value: str) -> int:
    text = str(value).strip()
    if not _FRAGMENTS_RE.match(text):
        raise argparse.ArgumentTypeError(f"expected an integer 1-10, got {value!r}")
    n = int(text, 10)
    if not 1 <= n <= 10:
        raise argparse.ArgumentTypeError(f"--concurrent-fragments must be between 1 and 10, got {n}")
    return n


def _playlist_items_arg(value: str) -> str:
    v = str(value).strip().replace(" ", "")
    if not _PLAYLIST_ITEMS_RE.match(v):
        raise argparse.ArgumentTypeError(f"expected syntax like '1-3,7', got {value!r}")
    seen: set[int] = set()
    for part in v.split(","):
        start, _, end = part.partition("-")
        a = int(start)
        b = int(end) if end else a
        if a > b:
            raise argparse.ArgumentTypeError(f"reversed playlist range: {part!r}")
        if a < 1:
            raise argparse.ArgumentTypeError("playlist item numbers start at 1")
        for i in range(a, b + 1):
            if len(seen) >= 10000:
                raise argparse.ArgumentTypeError("too many playlist items selected (max 10000)")
            if i in seen:
                raise argparse.ArgumentTypeError(f"duplicate playlist item: {i}")
            seen.add(i)
    return v


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
    p.add_argument("--limit-rate", dest="limit_rate", type=parse_rate, default=None, metavar="RATE", help="Throttle download speed (e.g. 512K, 2M)")
    p.add_argument("--concurrent-fragments", dest="concurrent_fragments", type=_fragments_arg, default=None, metavar="N", help="Download HLS fragments in parallel (1-10, default 1)")
    p.add_argument("--no-overwrites", dest="no_overwrites", action="store_true", help="Skip download if the output file already exists")
    p.add_argument("--playlist-items", dest="playlist_items", type=_playlist_items_arg, default=None, metavar="ITEMS", help="Only download these playlist items (e.g. '1-3,7'; playlist URLs)")
    p.add_argument("--audio-format", dest="audio_format", choices=["mp3", "m4a", "opus", "aac", "flac", "wav"], default=None, help="Audio codec for extraction (default: mp3)")
    p.add_argument("--sponsorblock-chapters", dest="sponsorblock_chapters", nargs="*", default=None, help="Mark SponsorBlock segments as chapters instead of skipping (e.g. --sponsorblock-chapters sponsor intro outro)")
    p.add_argument("--dry-run", dest="dry_run", action="store_true", help="Detect and report what would be downloaded without downloading")
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
    if getattr(args, "limit_rate", None) is not None:
        choice.limit_rate = args.limit_rate
    if getattr(args, "concurrent_fragments", None):
        choice.concurrent_fragments = args.concurrent_fragments
    if getattr(args, "no_overwrites", False):
        choice.no_overwrites = True
    if getattr(args, "playlist_items", None):
        choice.playlist_items = args.playlist_items
    sponsorblock_chapters = getattr(args, "sponsorblock_chapters", None)
    if sponsorblock_chapters is not None:
        choice.sponsorblock_chapters = [c.strip().lower() for c in sponsorblock_chapters if c.strip()] or ["sponsor"]
    return choice


def build_choice_from_args(content, args: argparse.Namespace) -> DownloadChoice:
    """Build a non-interactive DownloadChoice from CLI flags."""
    from core.options import DownloadChoice  # noqa: PLC0415 - lazy, avoids rich at startup

    kind = args.output_type or ("audio" if content.content_type == "AUDIO" else "video")
    audio_format = getattr(args, "audio_format", None) if kind == "audio" else None
    if kind == "audio":
        # An explicit --audio-format wins over the shorthand -f for audio.
        fmt = audio_format or (args.fmt.lower() if args.fmt else AUDIO_FORMAT)
    else:
        fmt = VIDEO_FORMAT
    choice = DownloadChoice(output_kind=kind, quality=args.quality or "Best", fmt=fmt)
    if audio_format:
        choice.audio_format = audio_format
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
