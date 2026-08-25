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

from core import instagram_fallback, options, update_checker, utils
from core.detector import DetectionError, detect, is_valid_url
from core.downloader import DownloadCancelled, DownloadFailed, download

console = Console()

VERSION = "1.0.0"


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

    try:
        clip = pyperclip.paste().strip()
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
    while True:
        choice = options.show_settings_menu(config)
        if choice == "1":
            new_folder = Prompt.ask("Folder download baru", default=config["download_folder"])
            # expanduser() biar "~/Documents/MyDownloads" beneran ke-resolve
            # ke home folder user, bukan diperlakukan sebagai nama folder
            # relatif literal bernama "~"
            config["download_folder"] = str(Path(new_folder).expanduser())
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
            if utils.is_valid_naming_template(new_template):
                config["naming_template"] = new_template
                utils.save_config(config)
            else:
                console.print(
                    "[red]Template tidak valid - pastikan cuma pakai "
                    "%(platform)s, %(title)s, dan %(year)s.[/red]"
                )
        elif choice == "5":
            config["cookies_browser"] = options.ask_cookies_browser()
            utils.save_config(config)
        elif choice == "6":
            config.clear()
            config.update(utils.get_default_config())
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

    output_folder = Path(config["download_folder"]).expanduser()
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
        if content.raw_info.get("source") == "instaloader":
            result = instagram_fallback.download_photos(
                content,
                choice.selected_indices,
                choice.fmt,
                output_folder,
                config["naming_template"],
            )
            total_size = sum(p.stat().st_size for p in result.paths if p.exists())
            entry["size"] = utils.format_size(total_size)
            entry["success"] = result.success_count > 0

            if result.failed_count == 0:
                console.print(
                    f"\n✅ Selesai!\n"
                    f"   File  : {result.success_count} gambar tersimpan di {output_folder}\n"
                    f"   Ukuran total: {utils.format_size(total_size)}"
                )
            elif result.success_count > 0:
                # Partial success - dilaporkan APA ADANYA, bukan disamarkan
                # jadi "sukses penuh" ataupun "gagal total".
                console.print(
                    f"\n⚠️  Selesai sebagian!\n"
                    f"   File  : {result.success_count}/{result.total_count} gambar berhasil "
                    f"tersimpan di {output_folder}\n"
                    f"   Ukuran total: {utils.format_size(total_size)}\n"
                    f"   [yellow]{result.failed_count} gambar gagal didownload[/yellow]"
                )
            else:
                console.print("[red]❌ Semua gambar gagal didownload[/red]")
        else:
            result = download(
                content,
                choice,
                output_folder,
                config["naming_template"],
                max_retry=config.get("max_retry", 3),
                cookies_browser=config.get("cookies_browser"),
            )
            entry["size"] = utils.format_size(result.size_bytes)
            entry["success"] = result.file_count > 0

            if not entry["success"]:
                console.print("[red]❌ Terjadi kesalahan saat download - file hasil tidak ditemukan[/red]")
            elif result.file_count > 1:
                # Hasil multi-item (galeri/carousel, bukan single video/audio/gambar)
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
    except DownloadCancelled:
        console.print("[yellow]❌ Download dibatalkan oleh user[/yellow]")
    except DownloadFailed as e:
        console.print(f"[red]{e}[/red]")
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]❌ Gagal download: {e}[/red]")
    finally:
        utils.add_history_entry(config, entry)


def main() -> None:
    console.print("[dim]Menyiapkan ffmpeg...[/dim]")
    try:
        static_ffmpeg.add_paths()  # Download/pasang ffmpeg bundled kalau belum ada, tambahkan ke PATH
    except Exception as e:  # noqa: BLE001
        # static_ffmpeg butuh internet buat download binary ffmpeg di
        # percobaan PERTAMA (kalau belum pernah ke-download di komputer
        # ini). Kalau gagal (offline, GitHub diblokir firewall kantor/
        # kampus, dll), TIDAK BOLEH bikin seluruh aplikasi gagal dibuka -
        # banyak fitur (deteksi konten, download gambar tunggal, dll)
        # sama sekali gak butuh ffmpeg. Cukup kasih tau, lanjut jalan.
        console.print(f"[yellow]⚠️  Gagal menyiapkan ffmpeg bundled: {e}[/yellow]")
        console.print(
            "[dim]Fitur yang butuh ffmpeg (merge video+audio, convert format gambar, "
            "embed thumbnail) mungkin gagal sampai ffmpeg berhasil disiapkan.[/dim]"
        )

    has_update, installed_version, latest_version = update_checker.check_for_update()
    if has_update and latest_version:
        options.show_update_notice(installed_version, latest_version)

    config = utils.load_config()
    options.show_header(VERSION)

    last_clip_prompted: str | None = None

    while True:
        clip_url, last_clip_prompted = try_clipboard_url(config, last_clip_prompted)

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

        try:
            process_url(raw, config)
        except Exception as e:  # noqa: BLE001
            # Lapisan pertahanan terakhir - apa pun yang lolos dari semua
            # penanganan error di process_url() TIDAK BOLEH bikin seluruh
            # aplikasi crash dan kehilangan config/history yang belum tersimpan.
            console.print(f"[red]❌ Terjadi kesalahan tak terduga: {e}[/red]")

        if not options.ask_again():
            console.print("\n👋 Sampai jumpa!")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n👋 Dipaksa keluar. Sampai jumpa!")
