"""
instagram_fallback.py
Fallback khusus untuk postingan foto Instagram yang tidak didukung yt-dlp
(yt-dlp memang punya keterbatasan lama untuk post foto standalone di Instagram).
Pakai instaloader buat ambil metadata & URL media asli, lalu didownload manual.
"""

from __future__ import annotations

import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Callable

import instaloader

from core.utils import build_filename, resolve_duplicate

SHORTCODE_PATTERN = re.compile(r"instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)")


def is_instagram_url(url: str) -> bool:
    return "instagram.com" in url.lower()


def extract_shortcode(url: str) -> str | None:
    match = SHORTCODE_PATTERN.search(url)
    return match.group(1) if match else None


def detect_photo(url: str):
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
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
    except instaloader.exceptions.LoginRequiredException as e:
        raise DetectionError("Konten ini private / tidak bisa diakses") from e
    except instaloader.exceptions.ConnectionException as e:
        raise DetectionError("Koneksi internet bermasalah, coba lagi") from e
    except instaloader.exceptions.InstaloaderException as e:
        raise DetectionError("URL tidak valid atau tidak didukung") from e

    entries = []
    if post.typename == "GraphSidecar":
        for node in post.get_sidecar_nodes():
            if not node.is_video:
                entries.append({"url": node.display_url})
    elif not post.is_video:
        entries.append({"url": post.url})

    if not entries:
        raise DetectionError("Postingan ini tidak berisi foto yang bisa didownload")

    raw_title = (post.caption or "").strip().splitlines()[0] if post.caption else ""
    title = raw_title or f"Post by {post.owner_username}"

    return DetectedContent(
        url=url,
        platform="Instagram",
        title=title,
        content_type="IMAGE",
        duration=None,
        entries=entries,
        raw_info={"source": "instaloader"},
    )


def _convert_image(src: Path, target_ext: str) -> Path:
    """Convert jpg (format asli Instagram) ke png/webp pakai ffmpeg bundled, kalau perlu."""
    if target_ext in ("jpg", "jpeg") or src.suffix.lstrip(".").lower() == target_ext:
        return src

    dest = src.with_suffix(f".{target_ext}")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(src), str(dest)],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return src  # gagal konversi, tetap simpan versi jpg aslinya

    src.unlink(missing_ok=True)
    return dest


def download_photos(
    content,
    selected_indices: list[int] | None,
    target_ext: str,
    output_folder: Path,
    naming_template: str,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[Path]:
    """Download semua/foto tertentu dari carousel/single-photo Instagram."""
    output_folder.mkdir(parents=True, exist_ok=True)

    entries = content.entries
    if selected_indices:
        entries = [entries[i] for i in selected_indices if 0 <= i < len(entries)]

    if not entries:
        entries = content.entries  # index tidak valid semua -> fallback ke semua

    results: list[Path] = []
    total = len(entries)

    for idx, entry in enumerate(entries, start=1):
        title = f"{content.title}-{idx}" if total > 1 else content.title
        filename = build_filename(content.platform, title, "jpg", naming_template)
        dest = resolve_duplicate(output_folder / filename)

        urllib.request.urlretrieve(entry["url"], dest)  # noqa: S310 - URL dari instaloader (CDN Instagram resmi)
        final_path = _convert_image(dest, target_ext)
        results.append(final_path)

        if on_progress:
            on_progress(idx, total)

    return results
