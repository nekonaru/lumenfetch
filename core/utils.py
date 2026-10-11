"""
utils.py
Kumpulan fungsi bantu: sanitasi nama file, format ukuran,
dan baca/tulis config.json.

Fasad kompatibel: nilai kanonis tinggal di core.constants,
tapi tetap di-re-export dari sini agar import lama
(`from core.utils import MAX_TITLE_LEN`, dll) tidak rusak.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
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
    "convert_image",
    "format_size",
    "format_duration",
    "estimate_video_size_bytes",
    "estimate_audio_size_bytes",
    "estimate_average_speed_bps",
    "format_eta",
]

# Re-export agar `utils.MAX_TITLE_LEN` dkk tetap tersedia.
# (Nilai kanonisnya di core.constants)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _user_data_dir() -> Path:
    """Direktori data user per-OS (tanpa dependency platformdirs)."""
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
    """Prioritas: CONFIG_PATH yang di-monkeypatch test > user dir.

    Fungsi ini dipanggil dinamis (bukan sekali di import) agar
    `monkeypatch.setattr(utils, "CONFIG_PATH", ...)` tetap dihormati.
    """
    return CONFIG_PATH


# Lokasi kanonis: user dir. File lama di project root dimigrasi otomatis
# sekali saat load pertama (lihat _migrate_legacy_config).
CONFIG_PATH = _user_data_dir() / "config.json"


def get_default_download_folder() -> str:
    """
    Folder download default: folder "Downloads" asli sistem operasi user
    (sama seperti browser lain - Chrome, Firefox, Edge, dll - defaultnya
    selalu ke situ), BUKAN folder relatif "downloads/" di dalam folder
    project. User tetap bisa ganti ke folder lain kapan saja lewat command
    settings > [1] Ganti folder download default.
    """
    return str(Path.home() / "Downloads")


DEFAULT_CONFIG = {
    "version": CONFIG_VERSION,
    "download_folder": get_default_download_folder(),
    "auto_paste": True,
    "naming_template": "%(platform)s_%(title)s_%(year)s",
    "max_retry": 3,
    "cookies_browser": None,
    "history": [],
}


def get_default_config() -> dict:
    """
    Return salinan BENAR-BENAR terpisah dari DEFAULT_CONFIG (deep copy).

    Wajib pakai ini (bukan DEFAULT_CONFIG.copy()) di manapun butuh config default,
    karena "history" adalah list - shallow copy cuma menyalin referensinya,
    bukan isinya. Kalau nanti list itu dimutasi (mis. lewat add_history_entry),
    DEFAULT_CONFIG module-level ikut "tercemar" dan bocor ke semua config baru
    yang dibuat sesudahnya, termasuk pas user reset ke default.
    """
    return copy.deepcopy(DEFAULT_CONFIG)


def _coerce_config(data: dict) -> dict:
    """Validasi ringan untuk config hasil load / edit manual."""
    merged = get_default_config()
    if not isinstance(data, dict):
        return merged
    merged.update(data)
    # max_retry harus int >= 0, kalau rusak fallback ke default.
    try:
        merged["max_retry"] = max(0, int(merged.get("max_retry", 3)))
    except (TypeError, ValueError):
        merged["max_retry"] = 3
    if not isinstance(merged.get("history"), list):
        merged["history"] = []
    # Normalisasi cookies_browser: "none"/"" dianggap None (nonaktif).
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
    return merged


def _canonical_config_path() -> Path:
    return _user_data_dir() / "config.json"


def _migrate_legacy_config() -> None:
    """Salin config lama (project root) ke user dir bila user dir belum ada.

    Dilewati bila CONFIG_PATH sedang di-monkeypatch test ke lokasi lain.
    """
    try:
        target = _resolve_config_path()
        if target.resolve() != _canonical_config_path().resolve():
            return
        if target.exists():
            return
        legacy = _legacy_config_path()
        # Jangan migrasi file yang cuma berisi default/Contoh history lokal dev.
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
    """Baca config.json, buat default kalau belum ada / rusak."""
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
    Simpan config ke config.json. Gagal simpan (mis. folder tempat app
    dijalankan read-only) TIDAK raise - aplikasi tetap jalan pakai config
    in-memory, cuma perubahannya gak ke-persist ke disk. Fail-safe di sini
    otomatis melindungi SEMUA pemanggilnya (load_config, handle_settings di
    main.py, add_history_entry) tanpa perlu tiap caller bungkus try/except
    masing-masing.

    utils.py sengaja tidak nge-print apa pun ke user (module ini "helper
    murni" - lihat CONTRIBUTING.md, tidak boleh tahu soal CLI/rich) - kalau
    perlu notifikasi ke user, itu tanggung jawab caller.

    Thread-safe untuk batch paralel via lock proses-lokal.
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
    """Tambah entri riwayat baru, maksimal simpan HISTORY_LIMIT entri terakhir."""
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
    """Bersihkan nama file dari karakter ilegal & spasi, truncate max 80 char."""
    if not name:
        name = "untitled"
    name = re.sub(ILLEGAL_CHARS, "_", name)
    # Ganti SEMUA whitespace (spasi, tab, newline) jadi "-", bukan cuma " ".
    name = re.sub(r"\s+", "-", name.strip())
    name = re.sub(r"-{2,}", "-", name)
    # Windows melarang nama diakhiri titik/spasi.
    name = name.strip(" .")
    if not name:
        name = "untitled"
    # Nama reserved Windows (CON, PRN, ...) tidak boleh dipakai polos.
    if name.upper() in WINDOWS_RESERVED_NAMES:
        name = f"_{name}"
    return name[:MAX_TITLE_LEN]


def is_valid_naming_template(template: str) -> bool:
    """
    Cek apakah naming template valid sebelum disimpan ke config - dipakai di
    handle_settings() supaya user tidak bisa nyimpen template yang bakal
    bikin build_filename() crash (mis. placeholder salah ketik seperti
    %(titel)s bukannya %(title)s).
    """
    try:
        template % {"platform": "x", "title": "x", "year": 2026}
    except (KeyError, ValueError, TypeError):
        return False
    return True


def build_filename(platform: str, title: str, ext: str, template: str) -> str:
    """
    Susun nama file berdasarkan naming template dari config.

    Fail-safe: kalau template ternyata tidak valid (mis. lolos tervalidasi
    saat disimpan tapi rusak lewat edit manual config.json), otomatis
    fallback ke template default - supaya kesalahan konfigurasi TIDAK PERNAH
    bikin seluruh aplikasi crash pas lagi proses download.
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
    Cari file hasil outtmpl multi-item: pola "{stem}-<angka>.<ext>" persis
    (index-nya dari %(playlist_index,autonumber)d di yt-dlp, jadi selalu
    angka murni).

    SENGAJA pakai regex yang di-anchor ke akhir nama file, BUKAN glob
    "{stem}-*.*" biasa - glob polos itu false-positive kalau ada konten lain
    yang judulnya kebetulan numpuk sebagai prefix. Misal stem "Sunset" bakal
    salah kena "Sunset-Beach-1.jpg" (padahal itu punya konten LAIN yang
    judulnya "Sunset-Beach"), karena "Beach-1.jpg" tetap cocok pola glob
    "*.*" longgar. Dengan regex `-\\d+\\.` di akhir, "Sunset-Beach-1.jpg"
    tidak match untuk stem "Sunset" (karena setelah "Sunset-" karakternya
    "B", bukan digit), tapi tetap match buat stem "Sunset-Beach" itu sendiri.

    Hasilnya diurutkan NUMERIK berdasarkan angka index-nya (bukan alfabetis
    dari nama file) - kalau pakai sorted() string biasa, "Galeri-10.jpg"
    bakal muncul SEBELUM "Galeri-2.jpg" (perbandingan karakter '1' < '2'),
    padahal urutan aslinya seharusnya 2 dulu baru 10.

    FIX: tidak pakai `glob(f"{stem}-*.*")` mentah karena stem bisa mengandung
    karakter glob (`[`, `*`, `?`) dari judul asli (mis. "Video [Official]").
    Pakai iterdir + regex agar aman untuk semua judul.
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
    Kalau nama file sudah ada, tambahin suffix (1), (2), dst ke base filename.

    multi_item=True dipakai khusus buat galeri/carousel (outtmpl-nya nanti
    dikasih suffix index seperti "-1.jpg", "-2.jpg" - lihat _build_ydl_opts
    di downloader.py). File persis "{stem}.{ext}" TIDAK PERNAH benar-benar
    dibuat untuk kasus ini, jadi mengecek exists() pada path itu sendiri
    salah - selalu balik False meski sudah pernah didownload sebelumnya.
    Yang perlu dicek adalah apakah ADA file terindeks dengan stem itu di
    folder tujuan (lihat find_indexed_files). Tanpa ini, download galeri
    yang sama dua kali diam-diam menimpa hasil download pertama, alih-alih
    dapat suffix (1) seperti perilaku normal untuk konten single-item.
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
    Ubah nama browser dari config jadi format yang dipahami yt-dlp
    (opsi 'cookiesfrombrowser'). Return None kalau fitur nonaktif.
    """
    if not browser:
        return None
    normalized = str(browser).strip().lower()
    if normalized in ("", "none"):
        return None
    if normalized not in SUPPORTED_COOKIE_BROWSERS:
        return None
    return (normalized, None, None, None)


def convert_image(src: Path, target_ext: str) -> Path:
    """
    Convert gambar ke format lain (jpg/png/webp) pakai ffmpeg yang sudah
    di-bundle otomatis (static_ffmpeg, lihat main.py). Dipakai bersama oleh
    downloader.py (gambar dari yt-dlp: thumbnail YouTube, galeri Pinterest/
    Reddit/X, dll) dan instagram_fallback.py (foto Instagram), supaya
    pilihan format PNG/WEBP di menu beneran dikonversi di SEMUA jalur
    download gambar, bukan cuma satu platform tertentu.

    Kalau target sudah sama dengan ekstensi asli, atau ffmpeg gagal/tidak
    ketemu, file ASLI dikembalikan apa adanya - gagal konversi TIDAK BOLEH
    bikin seluruh download dianggap gagal (gambarnya sendiri tetap
    tersimpan utuh, cuma formatnya beda dari yang diminta).
    """
    from core.constants import FFMPEG_TIMEOUT_SECONDS

    target_ext = target_ext.lower().lstrip(".")
    current_ext = src.suffix.lower().lstrip(".")

    # jpg dan jpeg dianggap format yang sama
    if {target_ext, current_ext} <= {"jpg", "jpeg"}:
        return src
    if target_ext == current_ext:
        return src

    dest = src.with_suffix(f".{target_ext}")
    if dest.exists():
        # Hindari overwrite file orang lain; cari nama unik.
        dest = resolve_duplicate(dest)
    try:
        from core.ffmpeg import exe as _ffmpeg_exe  # noqa: PLC0415 - hindari circular import

        subprocess.run(
            [_ffmpeg_exe(), "-y", "-i", str(src), str(dest)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=FFMPEG_TIMEOUT_SECONDS,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError, subprocess.TimeoutExpired):
        # Bersihkan file parsial hasil convert yang gagal, lalu fallback ke asli.
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            pass
        return src

    try:
        src.unlink(missing_ok=True)
    except OSError:
        pass
    return dest


def format_size(num_bytes: float | None) -> str:
    """Format bytes jadi human-readable (KB/MB/GB)."""
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
    """Format detik jadi H:MM:SS atau M:SS."""
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
    Ambil ukuran (bytes) dari satu format yt-dlp. "filesize" itu ukuran
    exact yang dilaporkan platform, "filesize_approx" perkiraan yt-dlp
    sendiri. Kalau dua-duanya gak ada (cukup umum, banyak platform gak
    ngasih tau ukuran di metadata), fallback hitung dari bitrate (tbr,
    satuan kbit/s) dikali durasi video.
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
    Estimasi ukuran total (video + audio yang bakal digabung) buat satu
    opsi quality, berdasarkan daftar format yang sudah didapat yt-dlp pas
    deteksi (tanpa perlu request tambahan ke platform). Return None kalau
    datanya gak cukup buat ngasih estimasi (mis. platform gak expose
    filesize/bitrate sama sekali) - lebih baik gak nampilin estimasi
    daripada nampilin angka ngasal.
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
                # Tier ini kemungkinan besar gak tersedia buat konten ini
                # (mis. sumbernya cuma sampai 720p, gak ada opsi 360p) -
                # mending gak nampilin estimasi sama sekali daripada nebak
                # pakai ukuran tier LAIN yang bisa menyesatkan (kelihatan
                # kayak "360p ukurannya segede 1080p").
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
    Estimasi ukuran hasil ekstraksi audio. Untuk quality dengan bitrate
    tetap (320/192/128 kbps), dihitung langsung dari bitrate target itu
    sendiri (lebih akurat, karena itu memang bitrate output-nya setelah
    ffmpeg convert - bukan bitrate sumbernya). Untuk "Best", dipakai
    estimasi dari stream audio sumber terbaik yang ada.
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
    Kecepatan download rata-rata (bytes/detik) dari beberapa download
    terakhir yang sukses di riwayat - dipakai buat estimasi waktu download,
    lebih jujur daripada nebak angka kecepatan generik yang belum tentu
    sesuai koneksi user. Return None kalau belum ada riwayat yang punya
    data lengkap (mis. baru pertama kali pakai aplikasi).
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


def format_eta(size_bytes: int | None, speed_bps: float | None) -> str | None:
    """Ubah estimasi ukuran + kecepatan jadi teks perkiraan waktu ("~14 detik", "~2 menit"). None kalau datanya kurang."""
    try:
        if not size_bytes or not speed_bps or float(speed_bps) <= 0:
            return None
        seconds = float(size_bytes) / float(speed_bps)
    except (TypeError, ValueError):
        return None

    if seconds < 60:
        return f"~{seconds:.0f} detik"
    minutes = seconds / 60
    if minutes < 60:
        return f"~{minutes:.0f} menit"
    hours = minutes / 60
    return f"~{hours:.1f} jam"
