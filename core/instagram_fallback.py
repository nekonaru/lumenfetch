"""
instagram_fallback.py
Fallback khusus untuk postingan foto Instagram yang tidak didukung yt-dlp
(yt-dlp memang punya keterbatasan lama untuk post foto standalone di Instagram).
Pakai instaloader buat ambil metadata & URL media asli, lalu didownload manual.
"""

from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import instaloader

from core.utils import build_filename, convert_image, resolve_duplicate

SHORTCODE_PATTERN = re.compile(r"instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)")


def is_instagram_url(url: str) -> bool:
    return "instagram.com" in url.lower()


def extract_shortcode(url: str) -> str | None:
    match = SHORTCODE_PATTERN.search(url)
    return match.group(1) if match else None


def _load_cookies_from_browser(loader: instaloader.Instaloader, browser: str) -> None:
    """
    Muat cookies Instagram dari browser ke session instaloader, biar bisa
    akses post yang butuh login (mis. akun private yang sudah kamu follow).
    Meniru cara instaloader CLI sendiri (--load-cookies / import_session di
    __main__.py), TERMASUK memanggil test_login() sesudah update_cookies().

    Ini bukan langkah kosmetik: instaloader.context.is_logged_in didefinisikan
    sebagai `bool(self.username)` - kalau cuma update_cookies() dipanggil
    tanpa test_login(), cookies-nya beneran ke-suntik ke session tapi
    is_logged_in TETAP False selamanya. Instaloader punya pengecekan
    is_logged_in di jalur redirect handling (instaloadercontext.py):
    kalau Instagram redirect ke halaman login, is_logged_in yang False bikin
    LoginRequiredException langsung dilempar - persis kondisi gagal yang
    fitur cookies ini coba selesaikan, walau cookies-nya sendiri valid.

    Beda dari instaloader CLI, di sini test_login() dibungkus try/except -
    gagal cek status login (mis. rate-limit sesaat) TIDAK BOLEH bikin
    seluruh proses deteksi gagal; cookies yang sudah disuntik tetap dipakai
    apa adanya buat request berikutnya.
    """
    try:
        import browser_cookie3
    except ImportError:
        return

    browser_fn = getattr(browser_cookie3, browser, None)
    if browser_fn is None:
        return

    try:
        browser_cookies = list(browser_fn())
    except Exception:  # noqa: BLE001
        return

    cookies = {c.name: c.value for c in browser_cookies if "instagram" in c.domain}
    if not cookies:
        return

    loader.context.update_cookies(cookies)

    try:
        username = loader.context.test_login()
        if username:
            loader.context.username = username
    except Exception:  # noqa: BLE001
        pass  # cookies tetap kepakai apa adanya walau pengecekan status login gagal


def detect_photo(url: str, cookies_browser: str | None = None):
    """
    Ambil metadata post foto Instagram (single/carousel) via instaloader.
    Return DetectedContent (didefinisikan lazy-import biar tidak circular import
    dengan core.detector).
    """
    from core.detector import DetectedContent, DetectionError  # noqa: PLC0415

    shortcode = extract_shortcode(url)
    if not shortcode:
        raise DetectionError("URL tidak valid atau tidak didukung")

    try:
        loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            quiet=True,
        )
        if cookies_browser and cookies_browser != "none":
            # Sebelum ini ditambahkan, fitur "Cookies dari Browser" di menu
            # settings DIAM-DIAM TIDAK BERLAKU buat jalur foto Instagram
            # (satu-satunya alasan fallback instaloader ini ada) - padahal
            # README & menu settings sendiri bilang fitur ini "terutama buat
            # Instagram". Post foto private tetap gagal walau cookies aktif.
            _load_cookies_from_browser(loader, cookies_browser)
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
    except instaloader.exceptions.LoginRequiredException as e:
        raise DetectionError("Konten ini private / tidak bisa diakses") from e
    except instaloader.exceptions.ConnectionException as e:
        raise DetectionError("Koneksi internet bermasalah, coba lagi") from e
    except instaloader.exceptions.InstaloaderException as e:
        raise DetectionError("URL tidak valid atau tidak didukung") from e

    entries = []
    photo_count = 0
    video_count = 0

    if post.typename == "GraphSidecar":
        for node in post.get_sidecar_nodes():
            if node.is_video:
                # DULU video di dalam carousel campuran (foto+video) DIAM-DIAM
                # DI-SKIP TOTAL - user cuma dapet foto-fotonya doang, videonya
                # ilang tanpa pemberitahuan apa pun. Sekarang disertakan, dengan
                # video_url langsung dari instaloader (bukan display_url yang
                # cuma thumbnail-nya).
                entries.append({"url": node.video_url, "is_video": True})
                video_count += 1
            else:
                entries.append({"url": node.display_url, "is_video": False})
                photo_count += 1
    elif post.is_video:
        entries.append({"url": post.video_url, "is_video": True})
        video_count += 1
    else:
        entries.append({"url": post.url, "is_video": False})
        photo_count += 1

    if not entries:
        raise DetectionError("Postingan ini tidak berisi foto/video yang bisa didownload")

    raw_title = (post.caption or "").strip().splitlines()[0] if post.caption else ""
    title = raw_title or f"Post by {post.owner_username}"

    return DetectedContent(
        url=url,
        platform="Instagram",
        title=title,
        content_type="IMAGE",
        duration=None,
        entries=entries,
        raw_info={"source": "instaloader", "photo_count": photo_count, "video_count": video_count},
    )


@dataclass
class PhotoDownloadResult:
    paths: list[Path] = field(default_factory=list)
    failed_count: int = 0
    total_count: int = 0

    @property
    def success_count(self) -> int:
        return len(self.paths)


def download_photos(
    content,
    selected_indices: list[int] | None,
    target_ext: str,
    output_folder: Path,
    naming_template: str,
    on_progress: Callable[[int, int], None] | None = None,
) -> PhotoDownloadResult:
    """
    Download semua/foto tertentu dari carousel/single-photo Instagram.

    Tiap foto diunduh SECARA INDEPENDEN - kalau satu foto gagal (mis. koneksi
    putus di tengah carousel 5 foto), foto-foto lain tetap dilanjutkan, bukan
    membatalkan semuanya (dulu: satu error langsung raise dan foto yang
    sudah sempat kedownload sebelumnya jadi "yatim" - tersimpan di disk tapi
    tidak pernah dilaporkan ke user karena fungsinya keburu crash). Hasilnya
    melaporkan dengan akurat berapa yang sukses dan berapa yang gagal.
    """
    output_folder.mkdir(parents=True, exist_ok=True)

    entries = content.entries
    if selected_indices:
        entries = [entries[i] for i in selected_indices if 0 <= i < len(entries)]

    if not entries:
        entries = content.entries  # index tidak valid semua -> fallback ke semua

    results: list[Path] = []
    failed_count = 0
    total = len(entries)

    for idx, entry in enumerate(entries, start=1):
        title = f"{content.title}-{idx}" if total > 1 else content.title
        is_video_entry = entry.get("is_video", False)
        # Entry video di dalam carousel campuran disimpan APA ADANYA sebagai
        # .mp4 - TIDAK dipaksa lewat convert_image() (yang khusus buat
        # gambar), karena format target (target_ext) yang dipilih user itu
        # buat foto-fotonya, bukan buat video yang kebetulan ikut satu post.
        ext = "mp4" if is_video_entry else "jpg"
        filename = build_filename(content.platform, title, ext, naming_template)
        dest = resolve_duplicate(output_folder / filename)

        try:
            urllib.request.urlretrieve(entry["url"], dest)  # noqa: S310 - URL dari instaloader (CDN Instagram resmi)
            final_path = dest if is_video_entry else convert_image(dest, target_ext)
            results.append(final_path)
        except Exception:  # noqa: BLE001
            # urlretrieve() yang gagal di tengah transfer (bukan gagal total
            # dari awal) bisa saja sudah sempat nulis `dest` sebagian/korup
            # ke disk. Kalau tidak dibersihkan, file sampah 0-byte/korup ini
            # nyangkut di folder output dengan nama yang KELIHATAN sah -
            # bisa membingungkan kalau user buka foldernya manual.
            dest.unlink(missing_ok=True)
            failed_count += 1

        if on_progress:
            on_progress(idx, total)

    return PhotoDownloadResult(paths=results, failed_count=failed_count, total_count=total)
