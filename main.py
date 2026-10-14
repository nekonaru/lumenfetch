#!/usr/bin/env python3
"""
Lumenfetch - YouTube Downloader (CLI): MP4 & MP3.
Application entry point.
"""

from __future__ import annotations

import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from core import doctor, options, update_checker, utils
from core.cli import apply_cli_overrides, build_choice_from_args, parse_args, read_batch_file
from core.constants import (
    BATCH_MAX_JOBS,
    PLAYLIST_MODE_ALL,
    PLAYLIST_MODE_SINGLE,
    VERSION,
)
from core.detector import DetectionError, detect, is_valid_url
from core.downloader import download
from core.errors import DownloadCancelled, DownloadFailed
from core.i18n import resolve_lang, set_lang, t

console = Console()

# Re-export so tests (`main.pyperclip`, `main.static_ffmpeg`) keep working.
try:
    import pyperclip as _pyperclip_mod  # noqa: F401
except ImportError:  # pragma: no cover - environment without clipboard
    _pyperclip_mod = None  # type: ignore[assignment]

try:
    import static_ffmpeg as _static_ffmpeg_mod  # noqa: F401
except ImportError:  # pragma: no cover
    _static_ffmpeg_mod = None  # type: ignore[assignment]

pyperclip = _pyperclip_mod
static_ffmpeg = _static_ffmpeg_mod

# Re-exported from core.cli so existing callers (and tests) keep working
# via the `main.*` namespace.
__all__ = [
    "apply_cli_overrides",
    "build_choice_from_args",
    "console",
    "parse_args",
    "process_batch",
    "process_url",
    "read_batch_file",
]

_history_write_lock = threading.Lock()


def _safe_io() -> None:
    """Do not crash (UnicodeEncodeError) on non-UTF-8 terminals / piped output.

    Emoji in rich messages need UTF-8; under the cp1252 locale (old PowerShell, pipes)
    a raw print() would raise. Switch the error handler to "replace" once
    up front - a single line of defense for ALL CLI output.
    """
    import sys as _sys

    for stream in (_sys.stdout, _sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:  # noqa: BLE001
            pass


def _get_pyperclip():
    global pyperclip
    if pyperclip is None:
        try:
            import pyperclip as mod  # noqa: PLC0415

            pyperclip = mod
        except ImportError:
            return None
    return pyperclip


def _ensure_ffmpeg() -> bool:
    """Ensure ffmpeg is available: system first, bundled fallback (lazy)."""
    from core import ffmpeg as _ffmpeg  # noqa: PLC0415

    if _ffmpeg.is_available():
        return True
    global static_ffmpeg
    if static_ffmpeg is None:
        try:
            import static_ffmpeg as mod  # noqa: PLC0415

            static_ffmpeg = mod
        except ImportError:
            console.print(t("main.ffmpeg_missing"))
            return False
    try:
        static_ffmpeg.add_paths()
        return _ffmpeg.is_available() or True
    except Exception as e:  # noqa: BLE001
        console.print(t("main.ffmpeg_fail", e=e))
        return False


def try_clipboard_url(config: dict, last_prompted: str | None) -> tuple[str | None, str | None]:
    """Offer a YouTube URL from the clipboard (once per content, no repeats)."""
    if not config.get("auto_paste", True):
        return None, last_prompted

    pc = _get_pyperclip()
    if pc is None:
        return None, last_prompted

    try:
        clip = pc.paste().strip()
    except Exception:  # noqa: BLE001
        return None, last_prompted

    if not clip or not is_valid_url(clip):
        return None, last_prompted

    if clip == last_prompted:
        return None, last_prompted

    console.print(t("clip.found", url=clip))
    if Prompt.ask(t("clip.use"), default="y").lower().startswith("y"):
        return clip, clip
    return None, clip


def handle_settings(config: dict) -> dict:
    handlers = {
        "1": _settings_change_folder,
        "2": _settings_change_retry,
        "3": _settings_toggle_autopaste,
        "4": _settings_change_template,
        "5": _settings_change_cookies,
        "6": _settings_reset,
    }
    while True:
        choice = options.show_settings_menu(config)
        if choice == "7":
            return config
        handler = handlers.get(choice)
        if handler is None:
            return config
        handler(config)


def _settings_change_folder(config: dict) -> None:
    new_folder = Prompt.ask(t("main.folder_prompt"), default=config["download_folder"])
    config["download_folder"] = str(Path(new_folder).expanduser())
    utils.save_config(config)


def _settings_change_retry(config: dict) -> None:
    raw = Prompt.ask(t("main.retry_prompt"), default=str(config["max_retry"]))
    if str(raw).strip().isdigit():
        config["max_retry"] = int(str(raw).strip())
        utils.save_config(config)


def _settings_toggle_autopaste(config: dict) -> None:
    config["auto_paste"] = not config.get("auto_paste", True)
    utils.save_config(config)


def _settings_change_template(config: dict) -> None:
    new_template = Prompt.ask(t("main.template_prompt"), default=config["naming_template"])
    if utils.is_valid_naming_template(new_template):
        config["naming_template"] = new_template
        utils.save_config(config)
    else:
        console.print(t("main.bad_template"))


def _settings_change_cookies(config: dict) -> None:
    config["cookies_browser"] = options.ask_cookies_browser()
    if not config["cookies_browser"]:
        raw = Prompt.ask(
            t("main.cookiefile_prompt"),
            default=config.get("cookies_file") or "",
        ).strip()
        config["cookies_file"] = raw or None
    else:
        config["cookies_file"] = None
    utils.save_config(config)


def _settings_reset(config: dict) -> None:
    config.clear()
    config.update(utils.get_default_config())
    utils.save_config(config)
    console.print(t("main.reset_done"))


def _warn_if_pure_playlist(content, playlist_mode: str = PLAYLIST_MODE_SINGLE) -> None:
    if content.entries and len(content.entries) > 1:
        if playlist_mode == PLAYLIST_MODE_ALL:
            console.print(t("main.warn_all", n=len(content.entries)))
            return
        console.print(t("main.warn_single", n=len(content.entries)))


def _save_history_threadsafe(config: dict, entry: dict) -> None:
    with _history_write_lock:
        utils.add_history_entry(config, entry)


def _maybe_show_updates() -> None:
    """yt-dlp + self update notices. Failures are silent by design."""
    try:
        has_update, installed_version, latest_version = update_checker.check_for_update()
    except Exception:  # noqa: BLE001
        has_update, installed_version, latest_version = False, "", None
    if has_update and latest_version:
        options.show_update_notice(installed_version, latest_version)
    try:
        self_update, self_installed, self_latest = update_checker.check_self_update()
    except Exception:  # noqa: BLE001
        self_update, self_latest = False, None
        self_installed = VERSION
    if self_update and self_latest:
        options.show_self_update_notice(self_installed, self_latest)


def _session_from_config(config: dict, args: argparse.Namespace) -> dict:
    """Build an in-memory session copy with CLI overrides applied.

    CLI flags (--output, --cookies, ...) must never leak into the persisted
    config: add_history_entry() saves whatever dict it is given, so the
    persisted object has to stay pristine.
    """
    session = dict(config)
    if args.output:
        session["download_folder"] = str(Path(args.output).expanduser())
    if args.cookies is not None:
        session["cookies_browser"] = None if str(args.cookies).lower() == "none" else str(args.cookies).lower()
    if args.cookies_file is not None:
        session["cookies_file"] = (
            str(Path(args.cookies_file).expanduser()) if str(args.cookies_file).strip() else None
        )
    if args.max_retry is not None:
        session["max_retry"] = max(0, int(args.max_retry))
    if args.no_clipboard:
        session["auto_paste"] = False
    return session


def process_url(
    url: str,
    config: dict,
    choice_override=None,
    auto_confirm: bool = False,
    playlist_mode: str | None = None,
    runtime: dict | None = None,
) -> bool:
    """Process a single YouTube URL. Return True on success.

    `config` is the persisted object (history is saved into it); `runtime`
    optionally carries temporary CLI overrides for everything else.
    """
    from core.log import get_logger  # noqa: PLC0415

    log = get_logger()
    rt = runtime or config
    console.print(t("main.detecting"))
    try:
        content = detect(url, cookies_browser=rt.get("cookies_browser"), cookies_file=rt.get("cookies_file"))
    except DetectionError as e:
        console.print(f"[red]{e}[/red]")
        log.warning("detect gagal %s: %s", url, e)
        return False

    options.show_content_panel(content)

    if choice_override is not None:
        choice = choice_override
        mode = playlist_mode or getattr(choice, "playlist_mode", PLAYLIST_MODE_SINGLE)
        _warn_if_pure_playlist(content, mode)
    else:
        _warn_if_pure_playlist(content)
        avg_speed_bps = utils.estimate_average_speed_bps(config.get("history", []))
        choice = options.resolve_choice(content, avg_speed_bps)
        if playlist_mode:
            choice.playlist_mode = playlist_mode

    _ensure_ffmpeg()

    output_folder = Path(rt["download_folder"]).expanduser()
    filename_preview = utils.build_filename(content.platform, content.title, choice.fmt, rt["naming_template"])

    if not auto_confirm and not options.confirm_filename(filename_preview):
        return False

    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "platform": content.platform,
        "title": content.title,
        "format": choice.fmt,
        "size": "-",
        "success": False,
    }

    try:
        result = download(
            content,
            choice,
            output_folder,
            rt["naming_template"],
            max_retry=rt.get("max_retry", 3),
            cookies_browser=rt.get("cookies_browser"),
            cookies_file=rt.get("cookies_file"),
        )
        entry.update(
            {
                "size": utils.format_size(result.size_bytes),
                "size_bytes": result.size_bytes,
                "elapsed_seconds": result.elapsed_seconds,
                "success": result.file_count > 0,
            }
        )
        if not entry["success"]:
            console.print(t("main.not_found"))
        elif result.file_count > 1:
            console.print(
                t("main.done")
                + f"\n   File  : {result.file_count} {t('main.files_in')} {output_folder}\n"
                f"   {t('main.total_size')}: {utils.format_size(result.size_bytes)}\n"
                f"   {t('main.time')} : {result.elapsed_seconds:.0f} {t('main.seconds')}"
            )
        else:
            console.print(
                t("main.done")
                + f"\n   File  : {result.filepath}\n"
                f"   {t('main.size')}: {utils.format_size(result.size_bytes)}\n"
                f"   {t('main.time')} : {result.elapsed_seconds:.0f} {t('main.seconds')}"
            )
    except DownloadCancelled:
        console.print(t("main.cancelled"))
        log.info("download dibatalkan %s", url)
    except DownloadFailed as e:
        console.print(f"[red]{e}[/red]")
        log.warning("download gagal %s: %s", url, e)
    except Exception as e:  # noqa: BLE001
        console.print(t("main.failed", e=e))
        log.exception("download error %s", url)
    finally:
        _save_history_threadsafe(config, entry)
    return bool(entry.get("success"))


def process_batch(urls: list[str], config: dict, args: argparse.Namespace, runtime: dict | None = None) -> dict:
    """Process many URLs (sequential/parallel). Return a summary."""
    rt = runtime or config
    jobs = max(1, min(int(getattr(args, "jobs", 1) or 1), BATCH_MAX_JOBS))
    results: dict = {"total": len(urls), "success": 0, "failed": 0}

    def _one(u: str) -> bool:
        try:
            content_probe = None
            choice = None
            if args.output_type or args.fmt or args.quality or args.yes or args.playlist or args.subs:
                try:
                    content_probe = detect(
                        u,
                        cookies_browser=rt.get("cookies_browser"),
                        cookies_file=rt.get("cookies_file"),
                    )
                    choice = build_choice_from_args(content_probe, args)
                except DetectionError as e:
                    console.print(f"[red]{u}: {e}[/red]")
                    choice = None
            if choice is not None:
                return process_url(
                    u, config, choice_override=choice, auto_confirm=True, playlist_mode=args.playlist, runtime=rt
                )
            try:
                probe = content_probe or detect(
                    u,
                    cookies_browser=rt.get("cookies_browser"),
                    cookies_file=rt.get("cookies_file"),
                )
                default_choice = build_choice_from_args(probe, args)
            except DetectionError as e:
                console.print(f"[red]{u}: {e}[/red]")
                return False
            return process_url(
                u, config, choice_override=default_choice, auto_confirm=True, playlist_mode=args.playlist, runtime=rt
            )
        except Exception as e:  # noqa: BLE001
            console.print(f"[red]{u}: {e}[/red]")
            return False

    if jobs == 1 or len(urls) <= 1:
        for u in urls:
            ok = _one(u)
            results["success" if ok else "failed"] += 1
        return results

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(_one, u): u for u in urls}
        for fut in as_completed(futs):
            try:
                ok = fut.result()
            except Exception:  # noqa: BLE001
                ok = False
            results["success" if ok else "failed"] += 1
    return results


def main(argv: list[str] | None = None) -> int:
    # argv=None means interactive mode (do not read sys.argv so that
    # programmatic/test calls are not polluted by pytest arguments).
    _safe_io()
    args = parse_args([] if argv is None else argv)
    from core.log import setup as _setup_log  # noqa: PLC0415

    _setup_log(verbose=args.verbose)

    if args.version:
        console.print(f"Lumenfetch v{VERSION}")
        return 0

    config = utils.load_config()
    # Display language: --ui-lang > env LUMENFETCH_LANG > config > default en.
    # An explicit CLI choice is remembered for the next session.
    if args.ui_lang:
        config["ui_lang"] = args.ui_lang
        utils.save_config(config)
    set_lang(resolve_lang(args.ui_lang, config))
    # Runtime copy carries CLI overrides; `config` stays pristine so history
    # saves never persist temporary flags (e.g. --output) by accident.
    session = _session_from_config(config, args)

    if args.history:
        options.show_history_table(config.get("history", []))
        return 0

    if args.doctor:
        options.show_header(VERSION)
        ok = doctor.show(doctor.run_all(session))
        return 0 if ok else 1

    if args.batch:
        try:
            urls = read_batch_file(args.batch)
        except OSError as e:
            console.print(t("main.batch_read_fail", e=e))
            return 1
        if not urls:
            console.print(t("main.batch_empty"))
            return 1
        options.show_header(VERSION)
        summary = process_batch(urls, config, args, runtime=session)
        console.print(t("main.batch_done", ok=summary["success"], total=summary["total"]))
        return 0 if summary["failed"] == 0 else 1

    if args.url:
        options.show_header(VERSION)
        _maybe_show_updates()
        non_interactive = bool(
            args.output_type or args.fmt or args.quality or args.yes or args.playlist or args.subs or args.embed_metadata or args.embed_subs
        )
        if non_interactive:
            try:
                content = detect(
                    args.url,
                    cookies_browser=session.get("cookies_browser"),
                    cookies_file=session.get("cookies_file"),
                )
            except DetectionError as e:
                console.print(f"[red]{e}[/red]")
                return 1
            choice = build_choice_from_args(content, args)
            ok = process_url(
                args.url, config, choice_override=choice, auto_confirm=True, playlist_mode=args.playlist, runtime=session
            )
            return 0 if ok else 1
        process_url(args.url, config, playlist_mode=args.playlist, runtime=session)
        return 0

    options.show_header(VERSION)
    _maybe_show_updates()

    last_clip_prompted: str | None = None

    while True:
        clip_url, last_clip_prompted = try_clipboard_url(session, last_clip_prompted)

        raw = clip_url or Prompt.ask(t("main.url_prompt")).strip()

        if raw.lower() in ("q", "quit"):
            console.print(t("main.bye"))
            break
        if raw.lower() == "history":
            options.show_history_table(config.get("history", []))
            continue
        if raw.lower() == "settings":
            config = handle_settings(config)
            session = _session_from_config(config, args)
            continue
        if raw.lower() == "help":
            options.show_help()
            continue
        if raw.lower() == "doctor":
            doctor.show(doctor.run_all(session))
            continue
        if not raw:
            continue

        try:
            process_url(raw, config, runtime=session)
        except Exception as e:  # noqa: BLE001
            console.print(t("main.unexpected", e=e))

        nxt = options.ask_again_or_url()
        if isinstance(nxt, str):
            try:
                process_url(nxt, config, runtime=session)
            except Exception as e:  # noqa: BLE001
                console.print(t("main.unexpected", e=e))
            continue
        if not nxt:
            console.print(t("main.bye"))
            break
    return 0


def cli() -> None:
    """Console script entry point `lumenfetch` (see pyproject [project.scripts])."""
    import sys as _sys

    try:
        raise SystemExit(main(_sys.argv[1:]))
    except KeyboardInterrupt:
        console.print(t("main.kicked"))


if __name__ == "__main__":
    cli()
