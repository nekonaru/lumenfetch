"""
utils.py
Kumpulan fungsi bantu: sanitasi nama file, format ukuran,
dan baca/tulis config.json.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path("config.json")


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
    "version": 1,
    "download_folder": get_default_download_folder(),
    "auto_paste": True,
    "naming_template": "%(platform)s_%(title)s_%(year)s",
    "max_retry": 3,
    "cookies_browser": None,
    "history": [],
}

# Browser yang didukung yt-dlp untuk ambil cookies (buat konten yang butuh login,
# misal Instagram). None/"none" berarti fitur ini nonaktif.
SUPPORTED_COOKIE_BROWSERS = ["none", "chrome", "firefox", "edge", "brave", "opera", "vivaldi", "safari"]

ILLEGAL_CHARS = r'[\\/:*?"<>|]'
MAX_TITLE_LEN = 80


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


def load_config() -> dict:
    """Baca config.json, buat default kalau belum ada / rusak."""
    if not CONFIG_PATH.exists():
        fresh = get_default_config()
        save_config(fresh)
        return fresh

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Isi field yang hilang biar tetap kompatibel ke depan
        merged = get_default_config()
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
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
    """
    try:
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def add_history_entry(config: dict, entry: dict) -> None:
    """Tambah entri riwayat baru, maksimal simpan 20 entri terakhir."""
    history = config.get("history", [])
    history.insert(0, entry)
    config["history"] = history[:20]
    save_config(config)


def clear_history(config: dict) -> None:
    config["history"] = []
    save_config(config)


def sanitize_filename(name: str) -> str:
    """Bersihkan nama file dari karakter ilegal & spasi, truncate max 80 char."""
    if not name:
        name = "untitled"
    name = re.sub(ILLEGAL_CHARS, "_", name)
    name = name.strip().replace(" ", "-")
    name = re.sub(r"-{2,}", "-", name)
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
    return f"{base}.{ext}"


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
    """
    pattern = re.compile(rf"^{re.escape(dest.stem)}-(\d+)\.[^.]+$")
    indexed_matches = []
    for p in dest.parent.glob(f"{dest.stem}-*.*"):
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
    if not browser or browser == "none":
        return None
    if browser not in SUPPORTED_COOKIE_BROWSERS:
        return None
    return (browser, None, None, None)


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
    target_ext = target_ext.lower().lstrip(".")
    current_ext = src.suffix.lower().lstrip(".")

    # jpg dan jpeg dianggap format yang sama
    if {target_ext, current_ext} <= {"jpg", "jpeg"}:
        return src
    if target_ext == current_ext:
        return src

    dest = src.with_suffix(f".{target_ext}")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(src), str(dest)],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return src  # gagal konversi, tetap simpan file asli

    src.unlink(missing_ok=True)
    return dest


def format_size(num_bytes: float) -> str:
    """Format bytes jadi human-readable (KB/MB/GB)."""
    if num_bytes is None:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def format_duration(seconds) -> str:
    """Format detik jadi H:MM:SS atau M:SS."""
    if not seconds:
        return "-"
    seconds = int(seconds)
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
    if fmt.get("filesize"):
        return int(fmt["filesize"])
    if fmt.get("filesize_approx"):
        return int(fmt["filesize_approx"])
    tbr = fmt.get("tbr")
    if tbr and duration:
        return int(tbr * 1000 / 8 * duration)
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

    height_limits = {"1080p": 1080, "720p": 720, "480p": 480, "360p": 360}
    limit = height_limits.get(quality)

    video_formats = [f for f in formats if f.get("vcodec") not in (None, "none") and f.get("height")]
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
        f for f in formats if f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none")
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

    kbps_map = {"320kbps": 320, "192kbps": 192, "128kbps": 128}
    target_kbps = kbps_map.get(quality)
    if target_kbps:
        return int(target_kbps * 1000 / 8 * duration)

    audio_formats = [f for f in (formats or []) if f.get("acodec") not in (None, "none")]
    if not audio_formats:
        return None
    audio_formats.sort(key=lambda f: f.get("abr") or 0, reverse=True)
    return _format_size_bytes_from_info(audio_formats[0], duration)


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
        if not entry.get("success"):
            continue
        size_bytes = entry.get("size_bytes")
        elapsed = entry.get("elapsed_seconds")
        if size_bytes and elapsed and elapsed > 0:
            speeds.append(size_bytes / elapsed)

    if not speeds:
        return None
    return sum(speeds) / len(speeds)


def format_eta(size_bytes: int | None, speed_bps: float | None) -> str | None:
    """Ubah estimasi ukuran + kecepatan jadi teks perkiraan waktu ("~14 detik", "~2 menit"). None kalau datanya kurang."""
    if not size_bytes or not speed_bps or speed_bps <= 0:
        return None

    seconds = size_bytes / speed_bps
    if seconds < 60:
        return f"~{seconds:.0f} detik"
    minutes = seconds / 60
    if minutes < 60:
        return f"~{minutes:.0f} menit"
    hours = minutes / 60
    return f"~{hours:.1f} jam"
