#!/usr/bin/env python3
"""
Lumenfetch - Universal Media Downloader (CLI)
Entry point aplikasi.
"""

from __future__ import annotations

import argparse
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from core import options, update_checker, utils
from core.constants import (
    BATCH_DEFAULT_JOBS,
    BATCH_MAX_JOBS,
    PLAYLIST_MODE_ALL,
    PLAYLIST_MODE_SINGLE,
    SUBTITLE_LANGS_DEFAULT,
    VERSION,
)
from core.detector import DetectionError, detect, is_valid_url
from core.downloader import download
from core.errors import DownloadCancelled, DownloadFailed

console = Console()

# Re-export agar test lama (`main.pyperclip`, `main.static_ffmpeg`, ...) tetap jalan.
try:
    import pyperclip as _pyperclip_mod  # noqa: F401
except ImportError:  # pragma: no cover - lingkungan tanpa clipboard
    _pyperclip_mod = None  # type: ignore[assignment]

try:
    import static_ffmpeg as _static_ffmpeg_mod  # noqa: F401
except ImportError:  # pragma: no cover
    _static_ffmpeg_mod = None  # type: ignore[assignment]

pyperclip = _pyperclip_mod
static_ffmpeg = _static_ffmpeg_mod

_history_write_lock = threading.Lock()


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
    """Pastikan ffmpeg tersedia: sistem dulu, bundled fallback (lazy).

    Return True kalau siap, False kalau gagal (fitur terkait mungkin gagal
    dengan pesan ramah, tapi aplikasi tetap jalan).
    """
    from core import ffmpeg as _ffmpeg  # noqa: PLC0415

    if _ffmpeg.is_available():
        return True
    global static_ffmpeg
    if static_ffmpeg is None:
        try:
            import static_ffmpeg as mod  # noqa: PLC0415

            static_ffmpeg = mod
        except ImportError:
            console.print("[yellow]⚠️  ffmpeg tidak ditemukan (sistem maupun bundled).[/yellow]")
            return False
    try:
        static_ffmpeg.add_paths()
        return _ffmpeg.is_available() or True
    except Exception as e:  # noqa: BLE001
        console.print(f"[yellow]⚠️  Gagal menyiapkan ffmpeg bundled: {e}[/yellow]")
        return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="lumenfetch",
        description="Universal media downloader - paste link, biar sisanya otomatis.",
    )
    p.add_argument("url", nargs="?", default=None, help="URL media langsung (tanpa menu utama)")
    p.add_argument("-f", "--format", dest="fmt", default=None, help="Format output (mis. mp4, mp3, jpg)")
    p.add_argument("-q", "--quality", default=None, help="Quality (video: Best/1080p/720p/480p/360p/Worst, audio: Best/320kbps/192kbps/128kbps)")
    p.add_argument("-t", "--type", dest="output_type", choices=["video", "audio", "image"], default=None)
    p.add_argument("-o", "--output", default=None, help="Folder output (override config)")
    p.add_argument("--cookies", default=None, help="Cookies browser (chrome/firefox/edge/brave/opera/vivaldi/safari/none)")
    p.add_argument("--max-retry", type=int, default=None)
    p.add_argument("--playlist", choices=[PLAYLIST_MODE_SINGLE, PLAYLIST_MODE_ALL], default=None)
    p.add_argument("--subs", action="store_true", help="Download subtitle bila tersedia")
    p.add_argument("--sub-langs", default=None, help="Bahasa subtitle koma (default: en,id)")
    p.add_argument("--embed-subs", action="store_true")
    p.add_argument("--embed-metadata", action="store_true")
    p.add_argument("--batch", default=None, help="File teks berisi daftar URL (satu per baris)")
    p.add_argument("--jobs", type=int, default=BATCH_DEFAULT_JOBS, help=f"Paralel batch 1-{BATCH_MAX_JOBS} (default 1)")
    p.add_argument("--no-clipboard", action="store_true")
    p.add_argument("--yes", "-y", action="store_true", help="Lewati konfirmasi nama file")
    p.add_argument("--verbose", "-v", action="store_true", help="Log detail ke file + console")
    p.add_argument("--history", action="store_true", help="Tampilkan riwayat lalu keluar")
    p.add_argument("--version", action="store_true", help="Tampilkan versi lalu keluar")
    return p.parse_args(argv)


def apply_cli_overrides(choice, args: argparse.Namespace):
    """Terapkan flag CLI ke DownloadChoice tanpa prompt tambahan."""
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
    return choice


def build_choice_from_args(content, args: argparse.Namespace):
    """Bangun DownloadChoice non-interaktif dari flag CLI (untuk url/batch/-y)."""
    from core.options import DownloadChoice  # noqa: PLC0415

    kind = args.output_type
    if kind is None:
        kind = "video" if content.content_type == "VIDEO" else ("audio" if content.content_type == "AUDIO" else "image")
    fmt = (args.fmt or "").lower() or None
    if fmt is None:
        fmt = {"video": "mp4", "audio": "mp3", "image": "jpg"}[kind]
    quality = args.quality or "Best"
    choice = DownloadChoice(output_kind=kind, quality=quality, fmt=fmt)
    return apply_cli_overrides(choice, args)


def try_clipboard_url(config: dict, last_prompted: str | None) -> tuple[str | None, str | None]:
    """
    Return (url_yang_dipakai_atau_None, clip_terakhir_yang_sudah_ditanyakan).

    Tidak menawarkan isi clipboard yang SAMA dua kali berturut-turut kalau
    user sudah pernah ditanya soal itu sebelumnya (baik dipakai atau
    ditolak) - tanpa ini, user harus jawab 'n' berulang kali tiap loop kalau
    isi clipboard belum berubah dari sebelumnya.
    """
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
        return None, last_prompted  # sudah pernah ditanyakan, jangan tanya lagi

    console.print(f"\n📋 Clipboard terdeteksi: {clip}")
    if Prompt.ask("Gunakan URL ini? [Y/n]", default="y").lower().startswith("y"):
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
    new_folder = Prompt.ask("Folder download baru", default=config["download_folder"])
    config["download_folder"] = str(Path(new_folder).expanduser())
    utils.save_config(config)


def _settings_change_retry(config: dict) -> None:
    raw = Prompt.ask("Max retry baru", default=str(config["max_retry"]))
    if str(raw).strip().isdigit():
        config["max_retry"] = int(str(raw).strip())
        utils.save_config(config)


def _settings_toggle_autopaste(config: dict) -> None:
    config["auto_paste"] = not config.get("auto_paste", True)
    utils.save_config(config)


def _settings_change_template(config: dict) -> None:
    new_template = Prompt.ask("Naming template baru", default=config["naming_template"])
    if utils.is_valid_naming_template(new_template):
        config["naming_template"] = new_template
        utils.save_config(config)
    else:
        console.print("[red]Template tidak valid - pastikan cuma pakai %(platform)s, %(title)s, dan %(year)s.[/red]")


def _settings_change_cookies(config: dict) -> None:
    config["cookies_browser"] = options.ask_cookies_browser()
    utils.save_config(config)


def _settings_reset(config: dict) -> None:
    config.clear()
    config.update(utils.get_default_config())
    utils.save_config(config)
    console.print("[green]Config direset ke default.[/green]")


def _warn_if_pure_playlist(content, playlist_mode: str = PLAYLIST_MODE_SINGLE) -> None:
    if content.content_type in ("VIDEO", "AUDIO") and len(content.entries) > 1:
        if playlist_mode == PLAYLIST_MODE_ALL:
            console.print(f"[cyan]ℹ️  Playlist terdeteksi: {len(content.entries)} video akan didownload semua.[/cyan]")
            return
        console.print(
            f"[yellow]⚠️  URL ini playlist berisi {len(content.entries)} video - "
            "Lumenfetch cuma download SATU per URL (video pertama), bukan "
            "playlist manager. Kalau mau video tertentu, paste link video "
            "itu langsung. (Gunakan --playlist all untuk semua.)[/yellow]"
        )


def _needs_ffmpeg(choice) -> bool:
    return choice.output_kind in ("video", "audio")


def _download_via_instagram(content, choice, output_folder: Path, naming_template: str, max_retry: int = 3) -> tuple[dict, str]:
    from core import instagram_fallback  # noqa: PLC0415

    instaloader_start = time.time()
    result = instagram_fallback.download_photos(
        content,
        choice.selected_indices,
        choice.fmt,
        output_folder,
        naming_template,
        max_retry=max_retry,
    )
    total_size = sum(p.stat().st_size for p in result.paths if p.exists())
    entry_extra = {
        "size": utils.format_size(total_size),
        "size_bytes": total_size,
        "elapsed_seconds": time.time() - instaloader_start,
        "success": result.success_count > 0,
    }
    if result.failed_count == 0:
        console.print(
            f"\n✅ Selesai!\n"
            f"   File  : {result.success_count} gambar tersimpan di {output_folder}\n"
            f"   Ukuran total: {utils.format_size(total_size)}"
        )
    elif result.success_count > 0:
        console.print(
            f"\n⚠️  Selesai sebagian!\n"
            f"   File  : {result.success_count}/{result.total_count} gambar berhasil "
            f"tersimpan di {output_folder}\n"
            f"   Ukuran total: {utils.format_size(total_size)}\n"
            f"   [yellow]{result.failed_count} gambar gagal didownload[/yellow]"
        )
    else:
        console.print("[red]❌ Semua gambar gagal didownload[/red]")
    return entry_extra, "instagram"


def _download_via_ytdlp(content, choice, output_folder: Path, naming_template: str, config: dict) -> dict:
    if _needs_ffmpeg(choice):
        _ensure_ffmpeg()
    result = download(
        content,
        choice,
        output_folder,
        naming_template,
        max_retry=config.get("max_retry", 3),
        cookies_browser=config.get("cookies_browser"),
    )
    entry_extra = {
        "size": utils.format_size(result.size_bytes),
        "size_bytes": result.size_bytes,
        "elapsed_seconds": result.elapsed_seconds,
        "success": result.file_count > 0,
    }
    if not entry_extra["success"]:
        console.print("[red]❌ Terjadi kesalahan saat download - file hasil tidak ditemukan[/red]")
    elif result.file_count > 1:
        console.print(
            f"\n✅ Selesai!\n"
            f"   File  : {result.file_count} gambar tersimpan di {output_folder}\n"
            f"   Ukuran total: {utils.format_size(result.size_bytes)}\n"
            f"   Waktu : {result.elapsed_seconds:.0f} detik"
        )
    else:
        console.print(
            f"\n✅ Selesai!\n"
            f"   File  : {result.filepath}\n"
            f"   Ukuran: {utils.format_size(result.size_bytes)}\n"
            f"   Waktu : {result.elapsed_seconds:.0f} detik"
        )
    return entry_extra


def _save_history_threadsafe(config: dict, entry: dict) -> None:
    with _history_write_lock:
        utils.add_history_entry(config, entry)


def process_url(
    url: str,
    config: dict,
    choice_override=None,
    auto_confirm: bool = False,
    playlist_mode: str | None = None,
) -> bool:
    """Proses satu URL. Return True bila sukses. Backward-compat: tanpa override tetap interaktif."""
    from core.log import get_logger  # noqa: PLC0415

    log = get_logger()
    console.print("\n🔍 Mendeteksi konten...")
    try:
        content = detect(url, cookies_browser=config.get("cookies_browser"))
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

    output_folder = Path(config["download_folder"]).expanduser()
    filename_preview = utils.build_filename(content.platform, content.title, choice.fmt, config["naming_template"])

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
        if content.raw_info.get("source") == "instaloader":
            entry_extra, _ = _download_via_instagram(
                content, choice, output_folder, config["naming_template"], max_retry=config.get("max_retry", 3)
            )
            entry.update(entry_extra)
        else:
            entry.update(_download_via_ytdlp(content, choice, output_folder, config["naming_template"], config))
    except DownloadCancelled:
        console.print("[yellow]❌ Download dibatalkan oleh user[/yellow]")
        log.info("download dibatalkan %s", url)
    except DownloadFailed as e:
        console.print(f"[red]{e}[/red]")
        log.warning("download gagal %s: %s", url, e)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]❌ Gagal download: {e}[/red]")
        log.exception("download error %s", url)
    finally:
        _save_history_threadsafe(config, entry)
    return bool(entry.get("success"))


def read_batch_file(path: str | Path) -> list[str]:
    urls: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def process_batch(urls: list[str], config: dict, args: argparse.Namespace) -> dict:
    """Proses banyak URL (sequential/paralel). Return ringkasan."""
    jobs = max(1, min(int(getattr(args, "jobs", 1) or 1), BATCH_MAX_JOBS))
    results: dict = {"total": len(urls), "success": 0, "failed": 0}

    def _one(u: str) -> bool:
        try:
            content_probe = None
            # Deteksi ringan untuk default non-interaktif? Langsung build choice
            # generik bila deteksi penuh gagal di process_url (tetap dilaporkan).
            choice = None
            if args.output_type or args.fmt or args.quality or args.yes or args.playlist or args.subs:
                # Butuh content untuk default kind/format; deteksi di sini
                # agar choice_override bisa dibangun sebelum process_url.
                try:
                    content_probe = detect(u, cookies_browser=config.get("cookies_browser"))
                    choice = build_choice_from_args(content_probe, args)
                except DetectionError:
                    choice = None
            if choice is not None:
                return process_url(u, config, choice_override=choice, auto_confirm=True, playlist_mode=args.playlist)
            # Fallback: butuh interaksi? di batch selalu non-interaktif:
            # pakai default Best bila tidak ada flag.
            try:
                probe = content_probe or detect(u, cookies_browser=config.get("cookies_browser"))
                default_choice = build_choice_from_args(probe, args)
            except DetectionError:
                return False
            return process_url(u, config, choice_override=default_choice, auto_confirm=True, playlist_mode=args.playlist)
        except Exception:  # noqa: BLE001
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
    # argv=None berarti "tidak ada argumen CLI" (mode interaktif) - sengaja
    # TIDAK membaca sys.argv di sini agar pemanggilan programatik
    # (termasuk unit test yang memanggil main.main() di dalam pytest,
    # di mana sys.argv berisi argumen pytest seperti 'tests/ -q')
    # tidak ikut terparse. Entry point script meneruskan sys.argv[1:]
    # secara eksplisit (lihat __main__ di bawah).
    args = parse_args([] if argv is None else argv)
    from core.log import setup as _setup_log  # noqa: PLC0415

    _setup_log(verbose=args.verbose)

    if args.version:
        console.print(f"Lumenfetch v{VERSION}")
        return 0

    config = utils.load_config()
    # Override config dari flag (tanpa simpan permanen).
    if args.output:
        config["download_folder"] = str(Path(args.output).expanduser())
    if args.cookies is not None:
        config["cookies_browser"] = None if str(args.cookies).lower() == "none" else str(args.cookies).lower()
    if args.max_retry is not None:
        config["max_retry"] = max(0, int(args.max_retry))
    if args.no_clipboard:
        config["auto_paste"] = False

    if args.history:
        options.show_history_table(config.get("history", []))
        return 0

    # Mode non-interaktif: --batch atau URL posisi.
    if args.batch:
        try:
            urls = read_batch_file(args.batch)
        except OSError as e:
            console.print(f"[red]Gagal baca batch file: {e}[/red]")
            return 1
        if not urls:
            console.print("[yellow]Batch file kosong.[/yellow]")
            return 1
        options.show_header(VERSION)
        summary = process_batch(urls, config, args)
        console.print(f"\nBatch selesai: {summary['success']}/{summary['total']} sukses.")
        return 0 if summary["failed"] == 0 else 1

    if args.url:
        options.show_header(VERSION)
        has_update, installed_version, latest_version = update_checker.check_for_update()
        if has_update and latest_version:
            options.show_update_notice(installed_version, latest_version)
        # Non-interaktif bila ada flag pembeda; else tetap tanya pilihan.
        non_interactive = bool(args.output_type or args.fmt or args.quality or args.yes or args.playlist or args.subs or args.embed_metadata or args.embed_subs)
        if non_interactive:
            try:
                content = detect(args.url, cookies_browser=config.get("cookies_browser"))
            except DetectionError as e:
                console.print(f"[red]{e}[/red]")
                return 1
            choice = build_choice_from_args(content, args)
            ok = process_url(args.url, config, choice_override=choice, auto_confirm=True, playlist_mode=args.playlist)
            return 0 if ok else 1
        process_url(args.url, config, playlist_mode=args.playlist)
        return 0

    options.show_header(VERSION)
    has_update, installed_version, latest_version = update_checker.check_for_update()
    if has_update and latest_version:
        options.show_update_notice(installed_version, latest_version)

    last_clip_prompted: str | None = None

    while True:
        clip_url, last_clip_prompted = try_clipboard_url(config, last_clip_prompted)

        raw = clip_url or Prompt.ask("\nMasukkan URL [dim](q: keluar, history, settings, help)[/dim]").strip()

        if raw.lower() in ("q", "quit"):
            console.print("\n👋 Sampai jumpa!")
            break
        if raw.lower() == "history":
            options.show_history_table(config.get("history", []))
            continue
        if raw.lower() == "settings":
            config = handle_settings(config)
            continue
        if raw.lower() == "help":
            options.show_help()
            continue
        if not raw:
            continue

        try:
            process_url(raw, config)
        except Exception as e:  # noqa: BLE001
            console.print(f"[red]❌ Terjadi kesalahan tak terduga: {e}[/red]")

        if not options.ask_again():
            console.print("\n👋 Sampai jumpa!")
            break
    return 0


if __name__ == "__main__":
    import sys as _sys

    try:
        raise SystemExit(main(_sys.argv[1:]))
    except KeyboardInterrupt:
        console.print("\n\n👋 Dipaksa keluar. Sampai jumpa!")
