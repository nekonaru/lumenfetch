#!/usr/bin/env python3
"""
Lumenfetch - Universal Media Downloader (CLI)
Entry point aplikasi.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pyperclip
import static_ffmpeg
from rich.console import Console
from rich.prompt import Prompt

from core import options, utils
from core.detector import DetectionError, detect, is_valid_url
from core.downloader import DownloadCancelled, DownloadFailed, download

console = Console()

VERSION = "1.0.0"


def try_clipboard_url(config: dict) -> str | None:
    if not config.get("auto_paste", True):
        return None
    try:
        clip = pyperclip.paste().strip()
    except Exception:  # noqa: BLE001
        return None

    if clip and is_valid_url(clip):
        console.print(f"\n📋 Clipboard terdeteksi: {clip}")
        if Prompt.ask("Gunakan URL ini? [Y/n]", default="y").lower().startswith("y"):
            return clip
    return None


def handle_settings(config: dict) -> dict:
    while True:
        choice = options.show_settings_menu(config)
        if choice == "1":
            new_folder = Prompt.ask("Folder download baru", default=config["download_folder"])
            config["download_folder"] = new_folder
            utils.save_config(config)
        elif choice == "2":
            raw = Prompt.ask("Max retry baru", default=str(config["max_retry"]))
            if raw.isdigit():
                config["max_retry"] = int(raw)
                utils.save_config(config)
        elif choice == "3":
            config["auto_paste"] = not config.get("auto_paste", True)
            utils.save_config(config)
        elif choice == "4":
            new_template = Prompt.ask("Naming template baru", default=config["naming_template"])
            config["naming_template"] = new_template
            utils.save_config(config)
        elif choice == "5":
            config["cookies_browser"] = options.ask_cookies_browser()
            utils.save_config(config)
        elif choice == "6":
            config.clear()
            config.update(utils.DEFAULT_CONFIG.copy())
            utils.save_config(config)
            console.print("[green]Config direset ke default.[/green]")
        elif choice == "7":
            return config
        else:
            return config


def process_url(url: str, config: dict) -> None:
    console.print("\n🔍 Mendeteksi konten...")
    try:
        content = detect(url, cookies_browser=config.get("cookies_browser"))
    except DetectionError as e:
        console.print(f"[red]{e}[/red]")
        return

    options.show_content_panel(content)
    choice = options.resolve_choice(content)

    output_folder = Path(config["download_folder"])
    filename_preview = utils.build_filename(content.platform, content.title, choice.fmt, config["naming_template"])

    if not options.confirm_filename(filename_preview):
        return

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
            config["naming_template"],
            max_retry=config.get("max_retry", 3),
            cookies_browser=config.get("cookies_browser"),
        )
        entry["size"] = utils.format_size(result.size_bytes)
        entry["success"] = True
        console.print(
            f"\n✅ Selesai!\n"
            f"   File  : {result.filepath}\n"
            f"   Ukuran: {utils.format_size(result.size_bytes)}\n"
            f"   Waktu : {result.elapsed_seconds:.0f} detik"
        )
    except DownloadCancelled:
        console.print("[yellow]❌ Download dibatalkan oleh user[/yellow]")
    except DownloadFailed as e:
        console.print(f"[red]{e}[/red]")
    finally:
        utils.add_history_entry(config, entry)


def main() -> None:
    console.print("[dim]Menyiapkan ffmpeg...[/dim]")
    static_ffmpeg.add_paths()  # Download/pasang ffmpeg bundled kalau belum ada, tambahkan ke PATH

    config = utils.load_config()
    options.show_header(VERSION)

    while True:
        clip_url = try_clipboard_url(config)

        raw = clip_url or Prompt.ask(
            "\nMasukkan URL [dim](q: keluar, history, settings, help)[/dim]"
        ).strip()

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

        process_url(raw, config)

        if not options.ask_again():
            console.print("\n👋 Sampai jumpa!")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n👋 Dipaksa keluar. Sampai jumpa!")
