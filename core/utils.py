"""
utils.py
Collection of helper functions: filename sanitization, size formatting,
and config.json read/write.

Compatible facade: canonical values live in core.constants,
but are still re-exported here so old imports
(`from core.utils import MAX_TITLE_LEN`, etc.) don't break.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime
from pathlib import Path

from core.constants import (
    AUDIO_TARGET_KBPS,
    CONFIG_VERSION,
    HEIGHT_LIMITS,
    HISTORY_LIMIT,
    ILLEGAL_CHARS,
    MAX_TITLE_LEN,
    SUPPORTED_COOKIE_BROWSERS,
    WINDOWS_RESERVED_NAMES,
)

__all__ = [
    "CONFIG_PATH",
    "DEFAULT_CONFIG",
    "SUPPORTED_COOKIE_BROWSERS",
    "ILLEGAL_CHARS",
    "MAX_TITLE_LEN",
    "get_default_download_folder",
    "get_default_config",
    "load_config",
    "save_config",
    "add_history_entry",
    "clear_history",
    "sanitize_filename",
    "is_valid_naming_template",
    "build_filename",
    "find_indexed_files",
    "resolve_duplicate",
    "build_cookies_from_browser",
    "resolve_cookie_file",
    "apply_cookie_opts",
    "format_size",
    "format_duration",
    "estimate_video_size_bytes",
    "estimate_audio_size_bytes",
    "estimate_average_speed_bps",
    "format_eta",
]

# Re-export so `utils.MAX_TITLE_LEN` etc. remain available.
# (Canonical values live in core.constants)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _user_data_dir() -> Path:
    """Per-OS user data directory (without the platformdirs dependency)."""
    import os
    import sys

    home = Path.home()
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "lumenfetch"
        return home / "AppData" / "Roaming" / "lumenfetch"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "lumenfetch"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "lumenfetch"
    return home / ".config" / "lumenfetch"


def _legacy_config_path() -> Path:
    return _project_root() / "config.json"


def _resolve_config_path() -> Path:
    """Priority: test-monkeypatched CONFIG_PATH > user dir.

    This is called dynamically (not once at import) so that
    `monkeypatch.setattr(utils, "CONFIG_PATH", ...)` stays respected.
    """
    return CONFIG_PATH


# Canonical location: user dir. The old file in the project root is migrated automatically
# once on first load (see _migrate_legacy_config).
CONFIG_PATH = _user_data_dir() / "config.json"


def get_default_download_folder() -> str:
    """
    Default download folder: the user's real OS "Downloads" folder
    (same as other browsers - Chrome, Firefox, Edge, etc. - which always
    default there), NOT a relative "downloads/" folder inside the
    project folder. Users can still switch to another folder anytime via the
    settings command > [1] Change default download folder.
    """
    return str(Path.home() / "Downloads")


DEFAULT_CONFIG = {
    "version": CONFIG_VERSION,
    "download_folder": get_default_download_folder(),
    "auto_paste": True,
    "naming_template": "%(platform)s_%(title)s_%(year)s",
    "max_retry": 3,
    "cookies_browser": None,
    "cookies_file": None,
    "ui_lang": "en",
    "history": [],
}


def get_default_config() -> dict:
    """
    Return a TRULY separate copy of DEFAULT_CONFIG (deep copy).

    Always use this (not DEFAULT_CONFIG.copy()) wherever a default config is needed,
    because "history" is a list - a shallow copy only copies its reference,
    not its contents. If that list is later mutated (e.g. via add_history_entry),
    the module-level DEFAULT_CONFIG gets "contaminated" and leaks into every new config
    created afterwards, including when the user resets to defaults.
    """
    return copy.deepcopy(DEFAULT_CONFIG)


def _coerce_config(data: dict) -> dict:
    """Light validation for loaded / manually edited config."""
    merged = get_default_config()
    if not isinstance(data, dict):
        return merged
    merged.update(data)
    # max_retry must be int >= 0, fall back to default if broken.
    try:
        merged["max_retry"] = max(0, int(merged.get("max_retry", 3)))
    except (TypeError, ValueError):
        merged["max_retry"] = 3
    if not isinstance(merged.get("history"), list):
        merged["history"] = []
    # Normalize cookies_browser: "none"/"" means None (disabled).
    cb = merged.get("cookies_browser")
    if cb is None:
        pass
    elif isinstance(cb, str) and cb.strip().lower() in ("", "none"):
        merged["cookies_browser"] = None
    elif isinstance(cb, str):
        merged["cookies_browser"] = cb.strip().lower()
    else:
        merged["cookies_browser"] = None
    if not isinstance(merged.get("download_folder"), str) or not merged["download_folder"].strip():
        merged["download_folder"] = get_default_download_folder()
    # cookies_file: path to the Netscape cookies file (optional). Normalize "" -> None.
    cf = merged.get("cookies_file")
    if isinstance(cf, str):
        cf = cf.strip()
        merged["cookies_file"] = cf or None
    else:
        merged["cookies_file"] = None
    # ui_lang: only "en"/"id" are valid, anything else falls back to default.
    lang = str(merged.get("ui_lang", "")).strip().lower()
    merged["ui_lang"] = lang if lang in ("en", "id") else "en"
    return merged


def _canonical_config_path() -> Path:
    return _user_data_dir() / "config.json"


def _migrate_legacy_config() -> None:
    """Copy the legacy config (project root) to the user dir if none exists there yet.

    Skipped when CONFIG_PATH is currently monkeypatched by tests to another location.
    """
    try:
        target = _resolve_config_path()
        if target.resolve() != _canonical_config_path().resolve():
            return
        if target.exists():
            return
        legacy = _legacy_config_path()
        # Skip migration for files containing only defaults / local dev sample history.
        if not legacy.exists() or legacy.resolve() == target.resolve():
            return
        data = json.loads(legacy.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError):
        pass


def load_config() -> dict:
    """Read config.json, creating defaults when missing / corrupted."""
    _migrate_legacy_config()
    path = _resolve_config_path()
    if not path.exists():
        fresh = get_default_config()
        save_config(fresh)
        return fresh

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return _coerce_config(data)
    except (json.JSONDecodeError, OSError, ValueError, AttributeError):
        fresh = get_default_config()
        save_config(fresh)
        return fresh


def save_config(config: dict) -> None:
    """
    Save config to config.json. Save failures (e.g. the folder the app
    runs in is read-only) do NOT raise - the app keeps running with the
    in-memory config, only the changes are not persisted to disk. This fail-safe
    automatically protects ALL of its callers (load_config, handle_settings in
    main.py, add_history_entry) without each caller needing its own try/except.

    utils.py deliberately prints nothing to the user (this module is a "pure
    helper" - see CONTRIBUTING.md, it must not know about CLI/rich) - if
    user notification is needed, that is the caller's responsibility.

    Thread-safe for parallel batches via a process-local lock.
    """
    lock = _history_lock()
    with lock:
        try:
            path = _resolve_config_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except OSError:
            pass


_history_lock_instance = None


def _history_lock():
    import threading

    global _history_lock_instance
    if _history_lock_instance is None:
        _history_lock_instance = threading.Lock()
    return _history_lock_instance


def add_history_entry(config: dict, entry: dict) -> None:
    """Add a new history entry, keeping at most the last HISTORY_LIMIT entries."""
    history = config.get("history")
    if not isinstance(history, list):
        history = []
        config["history"] = history
    history.insert(0, entry)
    config["history"] = history[:HISTORY_LIMIT]
    save_config(config)


def clear_history(config: dict) -> None:
    config["history"] = []
    save_config(config)


def sanitize_filename(name: str | None) -> str:
    """Clean a filename of illegal characters & whitespace, truncate to max 80 chars."""
    if not name:
        name = "untitled"
    name = re.sub(ILLEGAL_CHARS, "_", name)
    # Replace ALL whitespace (spaces, tabs, newlines) with "-", not just " ".
    name = re.sub(r"\s+", "-", name.strip())
    name = re.sub(r"-{2,}", "-", name)
    # Windows forbids names ending in a dot/space.
    name = name.strip(" .")
    if not name:
        name = "untitled"
    # Windows reserved names (CON, PRN, ...) must not be used bare.
    if name.upper() in WINDOWS_RESERVED_NAMES:
        name = f"_{name}"
    return name[:MAX_TITLE_LEN]


def is_valid_naming_template(template: str) -> bool:
    """
    Check whether a naming template is valid before saving it to config - used in
    handle_settings() so users cannot save a template that would make
    build_filename() crash (e.g. a mistyped placeholder like
    %(titel)s instead of %(title)s).
    """
    try:
        template % {"platform": "x", "title": "x", "year": 2026}
    except (KeyError, ValueError, TypeError):
        return False
    return True


def build_filename(platform: str, title: str, ext: str, template: str) -> str:
    """
    Build a filename from the naming template in config.

    Fail-safe: if the template turns out to be invalid (e.g. it passed validation
    when saved but was broken via manual config.json edits), automatically
    fall back to the default template - so a config mistake NEVER
    crashes the whole app mid-download.
    """
    year = datetime.now().year
    values = {
        "platform": sanitize_filename(platform or "Unknown"),
        "title": sanitize_filename(title or "untitled"),
        "year": year,
    }
    try:
        base = template % values
    except (KeyError, ValueError, TypeError):
        base = DEFAULT_CONFIG["naming_template"] % values
    base = sanitize_filename(base) if base else "untitled"
    ext = (ext or "").lower().lstrip(".")
    return f"{base}.{ext}" if ext else base


def _iter_dir_files(folder: Path):
    try:
        yield from folder.iterdir()
    except OSError:
        return


def find_indexed_files(dest: Path) -> list[Path]:
    """
    Find multi-item outtmpl result files: exact "{stem}-<number>.<ext>" pattern
    (the index comes from %(playlist_index,autonumber)d in yt-dlp, so it is
    always a pure number).

    DELIBERATELY uses a regex anchored to the end of the filename, NOT a plain
    "{stem}-*.*" glob - a bare glob false-positives when other content
    happens to share a prefix. E.g. stem "Sunset" would wrongly match
    "Sunset-Beach-1.jpg" (which belongs to OTHER content titled
    "Sunset-Beach"), because "Beach-1.jpg" still fits the loose "*.*"
    glob pattern. With a trailing `-\\d+\\.` regex, "Sunset-Beach-1.jpg"
    does not match stem "Sunset" (since the character after "Sunset-" is
    "B", not a digit), but still matches for the "Sunset-Beach" stem itself.

    Results are sorted NUMERICALLY by index number (not alphabetically
    by filename) - with a plain string sorted(), "Galeri-10.jpg"
    would come BEFORE "Galeri-2.jpg" (character comparison '1' < '2'),
    while the true order should be 2 before 10.

    FIX: do not use a raw `glob(f"{stem}-*.*")` because the stem may contain
    glob characters (`[`, `*`, `?`) from the original title (e.g. "Video [Official]").
    Use iterdir + regex to stay safe for all titles.
    """
    pattern = re.compile(rf"^{re.escape(dest.stem)}-(\d+)\.[^.]+$")
    indexed_matches = []
    for p in _iter_dir_files(dest.parent):
        if not p.is_file():
            continue
        m = pattern.match(p.name)
        if m:
            indexed_matches.append((int(m.group(1)), p))

    indexed_matches.sort(key=lambda pair: pair[0])
    return [p for _, p in indexed_matches]


def resolve_duplicate(path: Path, multi_item: bool = False) -> Path:
    """
    If the filename already exists, append a (1), (2), etc. suffix to the base filename.

    multi_item=True is used specifically for galleries/carousels (whose outtmpl later
    gets an index suffix like "-1.jpg", "-2.jpg" - see _build_ydl_opts
    in downloader.py). The exact "{stem}.{ext}" file is NEVER actually
    created for this case, so checking exists() on the path itself is
    wrong - it always returns False even when previously downloaded.
    What must be checked is whether ANY indexed files with that stem exist in
    the destination folder (see find_indexed_files). Without this, downloading the
    same gallery twice silently overwrites the first download instead of
    getting a (1) suffix like the normal single-item behavior.
    """

    def _already_exists(p: Path) -> bool:
        if multi_item:
            return bool(find_indexed_files(p))
        return p.exists()

    if not _already_exists(path):
        return path

    stem, suffix = path.stem, path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem}({counter}){suffix}")
        if not _already_exists(candidate):
            return candidate
        counter += 1


def build_cookies_from_browser(browser: str | None):
    """
    Convert a browser name from config into the format yt-dlp understands
    ('cookiesfrombrowser' option). Return None when the feature is disabled.
    """
    if not browser:
        return None
    normalized = str(browser).strip().lower()
    if normalized in ("", "none"):
        return None
    if normalized not in SUPPORTED_COOKIE_BROWSERS:
        return None
    return (normalized, None, None, None)


def resolve_cookie_file(path: str | None) -> str | None:
    """Validate a cookies file path (Netscape format). Return absolute path or None."""
    if not path:
        return None
    p = Path(str(path)).expanduser()
    if p.is_file():
        return str(p)
    return None


def apply_cookie_opts(ydl_opts: dict, cookies_browser: str | None, cookies_file: str | None = None) -> bool:
    """Apply cookie options to ydl_opts. Return True when any cookies are used.

    Order: cookies file first (most reliable, works even with the browser open),
    then browser cookies.
    """
    cookie_file = resolve_cookie_file(cookies_file)
    if cookie_file:
        ydl_opts["cookiefile"] = cookie_file
        return True
    cookies = build_cookies_from_browser(cookies_browser)
    if cookies:
        ydl_opts["cookiesfrombrowser"] = cookies
        return True
    return False


def format_size(num_bytes: float | None) -> str:
    """Format bytes as human-readable (KB/MB/GB)."""
    if num_bytes is None:
        return "?"
    try:
        num = float(num_bytes)
    except (TypeError, ValueError):
        return "?"
    if num < 0:
        num = 0
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def format_duration(seconds) -> str:
    """Format seconds as H:MM:SS or M:SS."""
    if not seconds:
        return "-"
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "-"
    if seconds <= 0:
        return "-"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _format_size_bytes_from_info(fmt: dict, duration: float | None) -> int | None:
    """
    Get the size (bytes) of a single yt-dlp format. "filesize" is the exact
    size reported by the platform, "filesize_approx" is yt-dlp's own
    estimate. If neither exists (fairly common, many platforms don't
    report sizes in metadata), fall back to computing from bitrate (tbr,
    in kbit/s) times the video duration.
    """
    if not isinstance(fmt, dict):
        return None
    if fmt.get("filesize"):
        try:
            return int(fmt["filesize"])
        except (TypeError, ValueError):
            pass
    if fmt.get("filesize_approx"):
        try:
            return int(fmt["filesize_approx"])
        except (TypeError, ValueError):
            pass
    try:
        tbr = float(fmt.get("tbr") or 0)
    except (TypeError, ValueError):
        tbr = 0
    if tbr and duration:
        try:
            return int(tbr * 1000 / 8 * float(duration))
        except (TypeError, ValueError):
            return None
    return None


def estimate_video_size_bytes(formats: list[dict], quality: str, duration: float | None) -> int | None:
    """
    Estimate the total size (video + audio to be merged) for one
    quality option, based on the format list yt-dlp already fetched during
    detection (no extra platform requests needed). Return None when
    the data is insufficient for an estimate (e.g. the platform exposes
    no filesize/bitrate at all) - better to show no estimate
    than a made-up number.
    """
    if not formats or not duration:
        return None

    limit = HEIGHT_LIMITS.get(quality)

    video_formats = [f for f in formats if isinstance(f, dict) and f.get("vcodec") not in (None, "none") and f.get("height")]
    if not video_formats:
        return None

    if quality == "Worst":
        video_formats.sort(key=lambda f: f["height"])
    else:
        if limit:
            video_formats = [f for f in video_formats if f["height"] <= limit]
            if not video_formats:
                # This tier is most likely unavailable for this content
                # (e.g. the source only goes up to 720p, no 360p option) -
                # better to show no estimate at all than guess
                # using ANOTHER tier's size which could mislead (looking
                # like "360p is as big as 1080p").
                return None
        video_formats.sort(key=lambda f: f["height"], reverse=True)

    video_size = _format_size_bytes_from_info(video_formats[0], duration)
    if video_size is None:
        return None

    audio_formats = [
        f for f in formats if isinstance(f, dict) and f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none")
    ]
    audio_size = 0
    if audio_formats:
        audio_formats.sort(key=lambda f: f.get("abr") or 0, reverse=(quality != "Worst"))
        audio_size = _format_size_bytes_from_info(audio_formats[0], duration) or 0

    return video_size + audio_size


def estimate_audio_size_bytes(formats: list[dict], quality: str, duration: float | None) -> int | None:
    """
    Estimate the audio extraction result size. For qualities with a fixed
    bitrate (320/192/128 kbps), computed directly from that target bitrate
    itself (more accurate, since that is the actual output bitrate after
    the ffmpeg convert - not the source bitrate). For "Best", the
    estimate from the best available source audio stream is used.
    """
    if not duration:
        return None

    try:
        dur = float(duration)
    except (TypeError, ValueError):
        return None
    if dur <= 0:
        return None

    target_kbps = AUDIO_TARGET_KBPS.get(quality)
    if target_kbps:
        return int(target_kbps * 1000 / 8 * dur)

    audio_formats = [f for f in (formats or []) if isinstance(f, dict) and f.get("acodec") not in (None, "none")]
    if not audio_formats:
        return None
    audio_formats.sort(key=lambda f: f.get("abr") or 0, reverse=True)
    return _format_size_bytes_from_info(audio_formats[0], dur)


def estimate_average_speed_bps(history: list[dict], sample_size: int = 10) -> float | None:
    """
    Average download speed (bytes/second) from recent successful downloads
    in history - used for download time estimates, more honest than guessing
    a generic speed number that may not match the user's connection.
    Return None when no history yet has complete data (e.g. first-time app use).
    """
    speeds = []
    for entry in (history or [])[:sample_size]:
        if not isinstance(entry, dict) or not entry.get("success"):
            continue
        size_bytes = entry.get("size_bytes")
        elapsed = entry.get("elapsed_seconds")
        try:
            if size_bytes and elapsed and float(elapsed) > 0:
                speeds.append(float(size_bytes) / float(elapsed))
        except (TypeError, ValueError):
            continue

    if not speeds:
        return None
    return sum(speeds) / len(speeds)


def format_eta(size_bytes: int | None, speed_bps: float | None, lang: str | None = None) -> str | None:
    """Convert size + speed estimates into ETA text ("~14 seconds", "~2 minutes"). None when data is insufficient."""
    from core.i18n import DEFAULT_LANG, STRINGS, SUPPORTED_LANGS, get_lang  # noqa: PLC0415

    if lang not in SUPPORTED_LANGS:
        lang = get_lang()
        if lang not in SUPPORTED_LANGS:
            lang = DEFAULT_LANG
    catalog = STRINGS.get(lang, STRINGS[DEFAULT_LANG])

    try:
        if not size_bytes or not speed_bps or float(speed_bps) <= 0:
            return None
        seconds = float(size_bytes) / float(speed_bps)
    except (TypeError, ValueError):
        return None

    if seconds < 60:
        return catalog["eta.second"].format(n=f"{seconds:.0f}")
    minutes = seconds / 60
    if minutes < 60:
        return catalog["eta.minute"].format(n=f"{minutes:.0f}")
    hours = minutes / 60
    return catalog["eta.hour"].format(n=f"{hours:.1f}")
