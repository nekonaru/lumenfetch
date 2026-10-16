"""i18n.py - CLI display-text catalog (English default, Indonesian optional).

Language priority (like wattpdl): --ui-lang > env LUMENFETCH_LANG >
config ui_lang > default "en".
"""

from __future__ import annotations

import os

LANG_EN = "en"
LANG_ID = "id"
SUPPORTED_LANGS = (LANG_EN, LANG_ID)
DEFAULT_LANG = LANG_EN
ENV_VAR = "LUMENFETCH_LANG"

_current = DEFAULT_LANG

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "update.title": "🔔 yt-dlp update available",
        "update.body": (
            "Your yt-dlp is version [bold]{installed}[/bold], "
            "version [bold green]{latest}[/bold green] is out.\n"
            "[dim]YouTube changes its systems often, "
            "so updating is recommended to stay compatible:[/dim]\n"
            "[bold cyan]pip install --upgrade yt-dlp[/bold cyan]"
        ),
        "panel.title": "✅ Video Detected",
        "panel.title_label": "Title",
        "panel.type_label": "Type",
        "panel.duration_label": "Duration",
        "panel.video_one": "({n} video)",
        "panel.video_many": "({n} videos)",
        "out.prompt": "\nChoose output type:",
        "out.video": "Video (MP4)",
        "out.audio": "Audio (MP3)",
        "pl.prompt": "\nThis playlist URL contains {total} videos:",
        "pl.single": "Download the first video only  (default)",
        "pl.all": "Download all ({total} videos)",
        "subs.prompt": "\nDownload subtitles?",
        "subs.no": "No  (default)",
        "subs.yes": "Yes, download subtitle files",
        "subs.langs": "Subtitle languages (comma, e.g. en,id)",
        "subs.embed": "Embed subtitles into the MP4 file?",
        "meta.prompt": "Embed metadata (title/artist) into the output file?",
        "q.video": "Choose Quality:",
        "q.audio": "Choose Quality (MP3 bitrate):",
        "confirm.file": "\n📄 Filename: [bold]{name}[/bold]",
        "confirm.go": "Continue?",
        "again.prompt": "\nDownload again? [y/n] [dim](or paste a URL directly)[/dim]",
        "again.invalid": "[red]Answer y/n, or paste a URL directly.[/red]",
        "again.ask": "\nDownload again?",
        "hist.empty": "[dim]No download history yet.[/dim]",
        "hist.title": "Last 20 Downloads",
        "hist.col_no": "No",
        "hist.col_date": "Date",
        "hist.col_title": "Title",
        "hist.col_format": "Format",
        "hist.col_size": "Size",
        "hist.col_status": "Status",
        "hist.clear_confirm": "Clear all {n} history entries?",
        "hist.cleared": "History cleared.",
        "help.title": "📖 Lumenfetch Help",
        "help.text": (
            "[bold]AVAILABLE COMMANDS[/bold]\n"
            "history   Show download history\n"
            "settings  Open settings\n"
            "doctor    Diagnose setup\n"
            "help      Show this page\n"
            "q/quit    Quit the app\n\n"
            "[bold]HOW TO USE[/bold]\n"
            "1. Paste a YouTube video link\n"
            "2. Pick Video (MP4) / Audio (MP3) output\n"
            "3. Pick a quality\n"
            "4. Wait for the download to finish\n\n"
            "[bold]CANCEL DOWNLOAD[/bold]\n"
            "Press Ctrl+C anytime"
        ),
        "set.title": "\n[bold]Settings[/bold]",
        "set.folder": "Change default download folder",
        "set.retry": "Change max retry",
        "set.autopaste": "Toggle clipboard auto-paste",
        "set.template": "Change naming template",
        "set.cookies": "Use browser/file cookies",
        "set.language": "Display language",
        "set.current_mark": "(current)",
        "set.reset": "Reset to defaults",
        "set.back": "Back",
        "set.current": "[dim](current: {v})[/dim]",
        "set.on": "ON",
        "set.off": "OFF",
        "cookie.info1": "\n[dim]Used for videos that require login / are age-restricted.[/dim]",
        "cookie.info2": "[dim]Make sure you're logged into YouTube in the chosen browser.[/dim]",
        "cookie.disable": "Disable",
        "clip.found": "\n📋 Clipboard detected: {url}",
        "clip.use": "Use this URL? [Y/n]",
        "main.url_prompt": "\nEnter YouTube URL [dim](q: quit, history, settings, help)[/dim]",
        "main.bye": "\n👋 Goodbye!",
        "main.kicked": "\n\n👋 Force-quit. Goodbye!",
        "main.detecting": "\n🔍 Detecting content...",
        "main.done": "\n✅ Done!",
        "main.files_in": "videos saved in",
        "main.total_size": "Total size",
        "main.size": "Size",
        "main.time": "Time",
        "main.seconds": "seconds",
        "main.not_found": "[red]❌ Download error - output file not found[/red]",
        "main.cancelled": "[yellow]❌ Download cancelled by user[/yellow]",
        "main.failed": "[red]❌ Download failed: {e}[/red]",
        "main.unexpected": "[red]❌ Unexpected error: {e}[/red]",
        "main.batch_done": "\nBatch finished: {ok}/{total} succeeded.",
        "main.batch_failed_urls": "Failed URLs:",
        "main.batch_empty": "[yellow]Batch file is empty.[/yellow]",
        "main.batch_read_fail": "[red]Failed to read batch file: {e}[/red]",
        "main.warn_single": (
            "[yellow]⚠️  This playlist URL contains {n} videos - "
            "only the first one will be downloaded. (Use --playlist all for all.)[/yellow]"
        ),
        "main.warn_all": "[cyan]ℹ️  Playlist detected: {n} videos will all be downloaded.[/cyan]",
        "main.reset_done": "[green]Config reset to defaults.[/green]",
        "main.bad_template": "[red]Invalid template - only %(platform)s, %(title)s, and %(year)s are allowed.[/red]",
        "main.folder_prompt": "New download folder",
        "main.retry_prompt": "New max retry",
        "main.template_prompt": "New naming template",
        "main.cookiefile_prompt": "Netscape cookie file (optional, leave empty to skip) [dim](export via the 'Get cookies.txt LOCALLY' extension)[/dim]",
        "main.ffmpeg_missing": "[yellow]⚠️  ffmpeg not found (neither system nor bundled).[/yellow]",
        "main.ffmpeg_fail": "[yellow]⚠️  Failed to set up bundled ffmpeg: {e}[/yellow]",
        "eta.second": "~{n} seconds",
        "eta.minute": "~{n} minutes",
        "eta.hour": "~{n} hours",
        "err.connection": "❌ Connection trouble, try again",
        "err.private": "❌ This content is private / unavailable - try enabling Browser Cookies in settings",
        "err.format": "❌ No matching format available right now - please retry",
        "err.disk": "❌ Not enough disk space",
        "err.rate_limit": "❌ Too many requests to this platform - wait a bit then retry",
        "err.removed": "❌ This content was deleted / is no longer available",
        "err.unsupported": "❌ Invalid or unsupported URL",
        "err.blocked": (
            "❌ Platform is blocking automated requests (bot-check) - update yt-dlp "
            "(pip install --upgrade yt-dlp) then enable Browser Cookies in settings"
        ),
        "err.blocked_curl": " + install the 'curl_cffi' package (pip install curl_cffi)",
        "err.cookies": (
            "❌ Failed to read browser cookies - close the browser completely "
            "(check Task Manager), then try again"
        ),
        "err.jsruntime": (
            "❌ YouTube needs a JavaScript runtime (Deno or Node.js) - install one, "
            "e.g. winget install DenoLand.Deno, then retry"
        ),
        "err.unknown": "❌ Download error occurred",
        "err.unknown_detect": "Not a valid YouTube URL or unsupported",
        "dl.cookie_retry": "continuing without cookies...",
        "dl.retry": "🔄 Retry {a}/{m} in {d:.0f}s...",
        "dl.pp_warning": "⚠️ Post-processing failed (e.g. thumbnail embed) - but the video file itself is fine and kept.",
        "dl.empty_result": "❌ Download produced no data (stream links may have expired) - please retry",
        "doctor.title": "🩺 Lumenfetch Doctor",
        "doctor.col_check": "Check",
        "doctor.col_result": "Result",
        "doctor.col_detail": "Detail",
        "doctor.col_hint": "Fix",
        "doctor.python": "Python >= 3.9",
        "doctor.python_hint": "Install Python 3.9+ from python.org",
        "doctor.ffmpeg": "ffmpeg",
        "doctor.ffmpeg_bundled": "bundled (static-ffmpeg)",
        "doctor.ffmpeg_hint": "Install system ffmpeg or pip install static-ffmpeg",
        "doctor.curl": "curl_cffi (bot-check bypass)",
        "doctor.js": "JS runtime (Deno/Node for challenges)",
        "doctor.js_hint": "install Deno (winget install DenoLand.Deno) or Node.js",
        "doctor.installed": "installed",
        "doctor.missing": "missing",
        "doctor.curl_hint": "pip install curl_cffi",
        "doctor.ytdlp": "yt-dlp",
        "doctor.ytdlp_hint": "pip install yt-dlp",
        "doctor.ytdlp_update": "newer {latest} available: pip install --upgrade yt-dlp",
        "doctor.self": "lumenfetch",
        "doctor.self_update": "newer {latest} available: pip install --upgrade lumenfetch",
        "doctor.network": "YouTube reachable",
        "doctor.network_hint": "Check your internet connection / VPN",
        "doctor.cookies": "Browser cookies",
        "doctor.cookies_off": "off",
        "doctor.cookies_hint": "Close the browser fully or use --cookies-file",
        "doctor.config": "Config writable",
        "doctor.config_hint": "Check folder permissions",
        "selfupdate.title": "🔔 Lumenfetch update available",
        "selfupdate.body": (
            "You have lumenfetch [bold]{installed}[/bold], "
            "version [bold green]{latest}[/bold green] is out.\n"
            "[bold cyan]pip install --upgrade lumenfetch[/bold cyan]"
        ),
        "err.no_video": "This content has no downloadable video",
        "err.not_youtube_url": "Not a valid YouTube URL",
    },
    "id": {
        "update.title": "🔔 Update yt-dlp tersedia",
        "update.body": (
            "yt-dlp kamu versi [bold]{installed}[/bold], "
            "versi terbaru [bold green]{latest}[/bold green] sudah tersedia.\n"
            "[dim]YouTube sering ubah sistemnya, "
            "jadi update disarankan biar tetap kompatibel:[/dim]\n"
            "[bold cyan]pip install --upgrade yt-dlp[/bold cyan]"
        ),
        "panel.title": "✅ Video Terdeteksi",
        "panel.title_label": "Judul",
        "panel.type_label": "Tipe",
        "panel.duration_label": "Durasi",
        "panel.video_one": "({n} video)",
        "panel.video_many": "({n} video)",
        "out.prompt": "\nPilih tipe output:",
        "out.video": "Video (MP4)",
        "out.audio": "Audio (MP3)",
        "pl.prompt": "\nURL ini playlist berisi {total} video:",
        "pl.single": "Download video pertama saja  (default)",
        "pl.all": "Download semua ({total} video)",
        "subs.prompt": "\nDownload subtitle?",
        "subs.no": "Tidak  (default)",
        "subs.yes": "Ya, download file subtitle",
        "subs.langs": "Bahasa subtitle (koma, mis. en,id)",
        "subs.embed": "Embed subtitle ke file MP4?",
        "meta.prompt": "Embed metadata (judul/artis) ke file hasil?",
        "q.video": "Pilih Quality:",
        "q.audio": "Pilih Quality (bitrate MP3):",
        "confirm.file": "\n📄 Nama file: [bold]{name}[/bold]",
        "confirm.go": "Lanjutkan?",
        "again.prompt": "\nDownload lagi? [y/n] [dim](atau paste URL langsung)[/dim]",
        "again.invalid": "[red]Jawab y/n, atau paste URL langsung.[/red]",
        "again.ask": "\nDownload lagi?",
        "hist.empty": "[dim]Belum ada riwayat download.[/dim]",
        "hist.title": "Riwayat Download (20 terakhir)",
        "hist.col_no": "No",
        "hist.col_date": "Tanggal",
        "hist.col_title": "Judul",
        "hist.col_format": "Format",
        "hist.col_size": "Ukuran",
        "hist.col_status": "Status",
        "hist.clear_confirm": "Hapus semua {n} entri riwayat?",
        "hist.cleared": "Riwayat dihapus.",
        "help.title": "📖 Lumenfetch Help",
        "help.text": (
            "[bold]COMMAND TERSEDIA[/bold]\n"
            "history   Lihat riwayat download\n"
            "settings  Buka pengaturan\n"
            "doctor    Diagnosa setup\n"
            "help      Tampilkan halaman ini\n"
            "q/quit    Keluar dari aplikasi\n\n"
            "[bold]CARA PAKAI[/bold]\n"
            "1. Paste link video YouTube\n"
            "2. Pilih output Video (MP4) / Audio (MP3)\n"
            "3. Pilih quality\n"
            "4. Tunggu download selesai\n\n"
            "[bold]CANCEL DOWNLOAD[/bold]\n"
            "Tekan Ctrl+C kapan saja"
        ),
        "set.title": "\n[bold]Settings[/bold]",
        "set.folder": "Ganti folder download default",
        "set.retry": "Ganti max retry",
        "set.autopaste": "Toggle auto-paste clipboard",
        "set.template": "Ganti naming template",
        "set.cookies": "Pakai cookies dari browser/file",
        "set.language": "Bahasa tampilan",
        "set.current_mark": "(saat ini)",
        "set.reset": "Reset ke default",
        "set.back": "Kembali",
        "set.current": "[dim](saat ini: {v})[/dim]",
        "set.on": "ON",
        "set.off": "OFF",
        "cookie.info1": "\n[dim]Dipakai buat video yang minta login / age-restricted.[/dim]",
        "cookie.info2": "[dim]Pastikan kamu sudah login ke YouTube di browser pilihanmu.[/dim]",
        "cookie.disable": "Nonaktifkan",
        "clip.found": "\n📋 Clipboard terdeteksi: {url}",
        "clip.use": "Gunakan URL ini? [Y/n]",
        "main.url_prompt": "\nMasukkan URL YouTube [dim](q: keluar, history, settings, help)[/dim]",
        "main.bye": "\n👋 Sampai jumpa!",
        "main.kicked": "\n\n👋 Dipaksa keluar. Sampai jumpa!",
        "main.detecting": "\n🔍 Mendeteksi konten...",
        "main.done": "\n✅ Selesai!",
        "main.files_in": "video tersimpan di",
        "main.total_size": "Ukuran total",
        "main.size": "Ukuran",
        "main.time": "Waktu",
        "main.seconds": "detik",
        "main.not_found": "[red]❌ Terjadi kesalahan saat download - file hasil tidak ditemukan[/red]",
        "main.cancelled": "[yellow]❌ Download dibatalkan oleh user[/yellow]",
        "main.failed": "[red]❌ Gagal download: {e}[/red]",
        "main.unexpected": "[red]❌ Terjadi kesalahan tak terduga: {e}[/red]",
        "main.batch_done": "\nBatch selesai: {ok}/{total} sukses.",
        "main.batch_failed_urls": "URL yang gagal:",
        "main.batch_empty": "[yellow]Batch file kosong.[/yellow]",
        "main.batch_read_fail": "[red]Gagal baca batch file: {e}[/red]",
        "main.warn_single": (
            "[yellow]⚠️  URL ini playlist berisi {n} video - "
            "cuma video pertama yang didownload. (Gunakan --playlist all untuk semua.)[/yellow]"
        ),
        "main.warn_all": "[cyan]ℹ️  Playlist terdeteksi: {n} video akan didownload semua.[/cyan]",
        "main.reset_done": "[green]Config direset ke default.[/green]",
        "main.bad_template": "[red]Template tidak valid - pastikan cuma pakai %(platform)s, %(title)s, dan %(year)s.[/red]",
        "main.folder_prompt": "Folder download baru",
        "main.retry_prompt": "Max retry baru",
        "main.template_prompt": "Naming template baru",
        "main.cookiefile_prompt": "File cookies Netscape (opsional, kosongkan bila tidak pakai) [dim](export via extension 'Get cookies.txt LOCALLY')[/dim]",
        "main.ffmpeg_missing": "[yellow]⚠️  ffmpeg tidak ditemukan (sistem maupun bundled).[/yellow]",
        "main.ffmpeg_fail": "[yellow]⚠️  Gagal menyiapkan ffmpeg bundled: {e}[/yellow]",
        "eta.second": "~{n} detik",
        "eta.minute": "~{n} menit",
        "eta.hour": "~{n} jam",
        "err.connection": "❌ Koneksi internet bermasalah, coba lagi",
        "err.private": "❌ Konten ini private / tidak bisa diakses - coba aktifkan Cookies dari Browser di settings",
        "err.format": "❌ Format tidak tersedia saat ini - coba lagi",
        "err.disk": "❌ Tidak cukup ruang disk",
        "err.rate_limit": "❌ Terlalu banyak request ke platform ini - tunggu sebentar lalu coba lagi",
        "err.removed": "❌ Konten ini sudah dihapus / tidak lagi tersedia",
        "err.unsupported": "❌ URL tidak valid atau tidak didukung",
        "err.blocked": (
            "❌ Platform memblokir request otomatis (bot-check) - update yt-dlp "
            "(pip install --upgrade yt-dlp) lalu aktifkan Cookies dari Browser di settings"
        ),
        "err.blocked_curl": " + install paket 'curl_cffi' (pip install curl_cffi)",
        "err.cookies": (
            "❌ Gagal membaca cookies dari browser - tutup browser-nya sampai "
            "benar-benar tertutup (cek Task Manager), lalu coba lagi"
        ),
        "err.jsruntime": (
            "❌ YouTube butuh JavaScript runtime (Deno atau Node.js) - install salah satu, "
            "mis. winget install DenoLand.Deno, lalu coba lagi"
        ),
        "err.unknown": "❌ Terjadi kesalahan saat download",
        "err.unknown_detect": "URL bukan link YouTube yang valid atau tidak didukung",
        "dl.cookie_retry": "lanjut tanpa cookies...",
        "dl.retry": "🔄 Retry {a}/{m} dalam {d:.0f}s...",
        "dl.pp_warning": "⚠️ Post-processing gagal (mis. embed thumbnail) - tapi file videonya utuh dan disimpan.",
        "dl.empty_result": "❌ Download tidak menghasilkan data (link stream mungkin kedaluwarsa) - coba lagi",
        "doctor.title": "🩺 Lumenfetch Doctor",
        "doctor.col_check": "Cek",
        "doctor.col_result": "Hasil",
        "doctor.col_detail": "Detail",
        "doctor.col_hint": "Solusi",
        "doctor.python": "Python >= 3.9",
        "doctor.python_hint": "Install Python 3.9+ dari python.org",
        "doctor.ffmpeg": "ffmpeg",
        "doctor.ffmpeg_bundled": "bundled (static-ffmpeg)",
        "doctor.ffmpeg_hint": "Install ffmpeg sistem atau pip install static-ffmpeg",
        "doctor.curl": "curl_cffi (lolos bot-check)",
        "doctor.js": "JS runtime (Deno/Node untuk challenge)",
        "doctor.js_hint": "install Deno (winget install DenoLand.Deno) atau Node.js",
        "doctor.installed": "terinstall",
        "doctor.missing": "hilang",
        "doctor.curl_hint": "pip install curl_cffi",
        "doctor.ytdlp": "yt-dlp",
        "doctor.ytdlp_hint": "pip install yt-dlp",
        "doctor.ytdlp_update": "ada {latest} yang baru: pip install --upgrade yt-dlp",
        "doctor.self": "lumenfetch",
        "doctor.self_update": "ada {latest} yang baru: pip install --upgrade lumenfetch",
        "doctor.network": "YouTube terjangkau",
        "doctor.network_hint": "Cek koneksi internet / VPN",
        "doctor.cookies": "Cookies browser",
        "doctor.cookies_off": "nonaktif",
        "doctor.cookies_hint": "Tutup browser total atau pakai --cookies-file",
        "doctor.config": "Config bisa ditulis",
        "doctor.config_hint": "Cek izin folder",
        "selfupdate.title": "🔔 Update Lumenfetch tersedia",
        "selfupdate.body": (
            "Lumenfetch kamu versi [bold]{installed}[/bold], "
            "versi [bold green]{latest}[/bold green] sudah tersedia.\n"
            "[bold cyan]pip install --upgrade lumenfetch[/bold cyan]"
        ),
        "err.no_video": "Konten ini tidak berisi video yang bisa didownload",
        "err.not_youtube_url": "URL bukan link YouTube yang valid",
    },
}


def set_lang(code: str | None) -> str:
    """Set the active language. Return the code in use (fallback to default if invalid)."""
    global _current
    code = (code or "").strip().lower()
    _current = code if code in SUPPORTED_LANGS else DEFAULT_LANG
    return _current


def get_lang() -> str:
    return _current


def t(key: str, **kwargs) -> str:
    """Get the UI string for the active language (fallback: English, then the key itself)."""
    template = STRINGS.get(_current, {}).get(key)
    if template is None:
        template = STRINGS[DEFAULT_LANG].get(key, key)
    try:
        return template.format(**kwargs) if kwargs else template
    except (KeyError, IndexError, ValueError):
        return template


def resolve_lang(cli: str | None = None, config: dict | None = None) -> str:
    """Order: --ui-lang > env LUMENFETCH_LANG > config ui_lang > default."""
    if (cli or "").strip().lower() in SUPPORTED_LANGS:
        return cli.strip().lower()  # type: ignore[union-attr]
    env = os.environ.get(ENV_VAR, "").strip().lower()
    if env in SUPPORTED_LANGS:
        return env
    if isinstance(config, dict) and str(config.get("ui_lang", "")).strip().lower() in SUPPORTED_LANGS:
        return str(config.get("ui_lang")).strip().lower()
    return DEFAULT_LANG


__all__ = [
    "DEFAULT_LANG",
    "ENV_VAR",
    "LANG_EN",
    "LANG_ID",
    "STRINGS",
    "SUPPORTED_LANGS",
    "get_lang",
    "resolve_lang",
    "set_lang",
    "t",
]
