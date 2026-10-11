"""
test_lumenfetch.py
Unit test untuk fungsi-fungsi inti (sanitasi nama file, format ukuran,
naming template, resolve duplikat, config, validasi URL, dll).
"""

from pathlib import Path
from unittest import mock

import pytest

from core import downloader, options
from core.options import DownloadChoice

# ---------------------------------------------------------------------------
# downloader._quality_to_format_selector
# ---------------------------------------------------------------------------

def test_format_selector_prefers_compatible_codecs_for_mp4():
    selector = downloader._quality_to_format_selector("Best", "mp4")
    assert "ext=mp4" in selector
    assert "ext=m4a" in selector


def test_format_selector_falls_back_for_non_mp4():
    selector = downloader._quality_to_format_selector("Best", "webm")
    assert "ext=mp4" not in selector


def test_format_selector_applies_height_filter():
    selector = downloader._quality_to_format_selector("720p", "mp4")
    assert "height<=720" in selector


def test_format_selector_worst_quality():
    selector = downloader._quality_to_format_selector("Worst", "mp4")
    assert "worstvideo" in selector and "worstaudio" in selector


# ---------------------------------------------------------------------------
# downloader.download() - konversi format gambar (bug: diabaikan di luar Instagram)
# ---------------------------------------------------------------------------

def test_download_image_converts_to_requested_format(tmp_path, monkeypatch):
    """
    Regresi bug: menu ask_image_choice() menawarkan JPG/PNG/WEBP untuk semua
    sumber gambar (bukan cuma Instagram), tapi dulu _build_ydl_opts() untuk
    output_kind="image" cuma set format="best" tanpa postprocessor konversi
    apa pun. Akibatnya pilihan PNG/WEBP diam-diam diabaikan - file yang
    tersimpan selalu dalam format asli sumbernya (biasanya JPG), padahal
    menu sudah menjanjikan konversi.
    """
    calls = []

    def fake_convert_image(src, target_ext):
        calls.append((src, target_ext))
        converted = src.with_suffix(f".{target_ext}")
        src.rename(converted)
        return converted

    monkeypatch.setattr(downloader, "convert_image", fake_convert_image)

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            # yt-dlp nyimpen file dalam ekstensi ASLI sumbernya (jpg),
            # meski outtmpl dituju ke ekstensi target user (png)
            base = self.opts["outtmpl"].rsplit(".", 1)[0]
            Path(f"{base}.jpg").write_bytes(b"fake-jpg-bytes")

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYDL)

    class FakeContent:
        url = "https://pinterest.com/pin/123"
        platform = "Pinterest"
        title = "Contoh Gambar"
        entries = []  # single image, bukan multi-item

    choice = DownloadChoice(output_kind="image", fmt="png")

    result = downloader.download(FakeContent(), choice, tmp_path, "%(platform)s_%(title)s_%(year)s")

    assert calls, "convert_image() tidak pernah dipanggil - bug konversi masih ada"
    assert calls[0][1] == "png"
    assert result.filepath.suffix == ".png"


def test_download_image_skips_conversion_when_format_already_matches(tmp_path, monkeypatch):
    calls = []

    def fake_convert_image(src, target_ext):
        calls.append(target_ext)
        return src  # sudah jpg, gak perlu convert

    monkeypatch.setattr(downloader, "convert_image", fake_convert_image)

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            base = self.opts["outtmpl"].rsplit(".", 1)[0]
            Path(f"{base}.jpg").write_bytes(b"fake-jpg-bytes")

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYDL)

    class FakeContent:
        url = "https://pinterest.com/pin/123"
        platform = "Pinterest"
        title = "Contoh Gambar"
        entries = []

    choice = DownloadChoice(output_kind="image", fmt="jpg")

    result = downloader.download(FakeContent(), choice, tmp_path, "%(platform)s_%(title)s_%(year)s")

    assert calls == ["jpg"]  # convert_image tetap dipanggil (biar konsisten), tapi hasilnya sama
    assert result.filepath.suffix == ".jpg"


# ---------------------------------------------------------------------------
# downloader._build_ydl_opts
# ---------------------------------------------------------------------------

def test_video_thumbnail_does_not_download_full_video(tmp_path):
    """
    Regresi bug: menu VIDEO -> [3] Gambar (thumbnail) dulu diproses lewat
    jalur output_kind="image" yang sama persis dengan gallery gambar asli
    (format="best", skip_download=False) - ini bikin yt-dlp download VIDEO
    UTUH kualitas terbaik, bukan cuma ambil thumbnail resminya. Dengan
    is_video_thumbnail=True, harus pakai skip_download+writethumbnail dan
    TIDAK mencantumkan "format" sama sekali.
    """
    choice = DownloadChoice(output_kind="image", fmt="jpg", is_video_thumbnail=True)
    opts = downloader._build_ydl_opts(choice, tmp_path / "thumb.jpg")

    assert opts["skip_download"] is True
    assert opts["writethumbnail"] is True
    assert "format" not in opts


def test_regular_image_download_unaffected_by_thumbnail_flag(tmp_path):
    """Behavior gallery/carousel gambar asli (bukan thumbnail video) tidak boleh berubah."""
    choice = DownloadChoice(output_kind="image", fmt="jpg", is_video_thumbnail=False)
    opts = downloader._build_ydl_opts(choice, tmp_path / "foto.jpg")

    assert opts["format"] == "best"
    assert opts["skip_download"] is False
    assert "writethumbnail" not in opts


def test_resolve_choice_sets_is_video_thumbnail_flag(monkeypatch):
    """Test integrasi: alur menu VIDEO -> [3] harus benar-benar set is_video_thumbnail=True."""
    from core.detector import DetectedContent

    content = DetectedContent(
        url="https://youtube.com/watch?v=abc",
        platform="YouTube",
        title="Judul Video",
        content_type="VIDEO",
        duration=120,
        entries=[],
        raw_info={},
    )

    responses = iter(["3", "1"])  # [3] Gambar (thumbnail), lalu format JPG
    monkeypatch.setattr(options.Prompt, "ask", lambda *a, **k: next(responses))

    choice = options.resolve_choice(content)

    assert choice.output_kind == "image"
    assert choice.is_video_thumbnail is True


def test_ask_image_choice_default_not_video_thumbnail():
    """Konten IMAGE asli (bukan dari menu video) harus tetap is_video_thumbnail=False."""
    from core.detector import DetectedContent

    content = DetectedContent(
        url="https://pinterest.com/pin/1",
        platform="Pinterest",
        title="Gambar",
        content_type="IMAGE",
        duration=None,
        entries=[],
        raw_info={},
    )


    with mock.patch.object(options.Prompt, "ask", return_value="1"):
        choice = options.ask_image_choice(content)

    assert choice.is_video_thumbnail is False


def test_ask_image_choice_filters_out_of_range_indices():
    """
    Regresi minor: nomor gambar yang di luar jangkauan entries (mis. ketik
    "99" padahal cuma ada 5 gambar) dulu tetap lolos ke selected_indices
    tanpa validasi, ujung-ujungnya bikin "0 gambar terdownload" tanpa
    penjelasan. Sekarang di-filter dan fallback ke download semua kalau
    semua nomor yang diketik ternyata invalid - konsisten sama behavior
    instagram_fallback.py yang sudah punya bounds-check serupa.
    """
    from core.detector import DetectedContent

    content = DetectedContent(
        url="https://reddit.com/gallery/xyz",
        platform="Reddit",
        title="Galeri",
        content_type="IMAGE",
        duration=None,
        entries=[{"url": "a"}, {"url": "b"}, {"url": "c"}, {"url": "d"}, {"url": "e"}],
        raw_info={},
    )


    with mock.patch.object(options.Prompt, "ask", side_effect=["1", "2", "99,100"]):
        choice = options.ask_image_choice(content)

    assert choice.selected_indices is None  # fallback ke download semua


def test_ask_image_choice_keeps_only_valid_indices():
    """Nomor yang valid tetap dipakai, yang di luar jangkauan didrop (bukan bikin semua batal)."""
    from core.detector import DetectedContent

    content = DetectedContent(
        url="https://reddit.com/gallery/xyz",
        platform="Reddit",
        title="Galeri",
        content_type="IMAGE",
        duration=None,
        entries=[{"url": "a"}, {"url": "b"}, {"url": "c"}],
        raw_info={},
    )


    with mock.patch.object(options.Prompt, "ask", side_effect=["1", "2", "1,99,2"]):
        choice = options.ask_image_choice(content)

    assert choice.selected_indices == [0, 1]  # nomor 1 dan 2 valid, "99" didrop


# ---------------------------------------------------------------------------
# downloader._classify_error - pesan error lebih akurat, bukan generik semua
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "error_msg,expected_kind",
    [
        ("HTTP Error 429: Too Many Requests", "rate_limit"),
        ("rate-limit reached, try again later", "rate_limit"),
        ("This video has been removed by the uploader", "removed"),
        ("Content deleted by owner", "removed"),
        ("no longer available in your country", "removed"),
        ("Connection timed out", "connection"),
        ("Private video, sign in required", "private"),
        ("No space left on device", "disk"),
        ("some completely unrecognized error message", "unknown"),
    ],
)
def test_classify_error_distinguishes_rate_limit_and_removed(error_msg, expected_kind):
    """
    Regresi minor: dulu error yang gak cocok pola apa pun (rate-limit 429,
    konten dihapus, dll) semuanya dilabeli "Koneksi internet bermasalah" -
    padahal itu bukan masalah koneksi sama sekali. Sekarang dibedakan biar
    pesannya gak menyesatkan user.
    """
    assert downloader._classify_error(Exception(error_msg)) == expected_kind


def test_embed_thumbnail_skipped_for_webm(tmp_path):
    """
    Regresi bug: EmbedThumbnailPP milik yt-dlp cuma support mp3, mkv/mka,
    ogg/opus/flac, m4a/mp4/m4v/mov - WEBM tidak ada di daftar itu dan dulu
    selalu raise EmbedThumbnailPPError meski video-nya sendiri sukses utuh
    ter-download, bikin user salah lihat pesan "gagal" padahal filenya ada.
    """
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="webm")
    opts = downloader._build_ydl_opts(choice, tmp_path / "video.webm")

    assert opts["postprocessors"] == []
    assert opts["writethumbnail"] is False


@pytest.mark.parametrize("fmt", ["mp4", "mkv"])
def test_embed_thumbnail_kept_for_supported_formats(tmp_path, fmt):
    choice = DownloadChoice(output_kind="video", quality="Best", fmt=fmt)
    opts = downloader._build_ydl_opts(choice, tmp_path / f"video.{fmt}")

    assert {"key": "EmbedThumbnail"} in opts["postprocessors"]
    assert opts["writethumbnail"] is True


def test_noplaylist_true_by_default(tmp_path):
    """
    Regresi potensi bug: default yt-dlp untuk noplaylist itu False. Kalau
    Lumenfetch tidak eksplisit menonaktifkannya, URL yang kebetulan
    mengandung parameter playlist bisa diam-diam mendownload banyak entry
    dan saling menimpa nama file yang sama (app ini didesain single-item,
    bukan playlist manager).
    """
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    opts = downloader._build_ydl_opts(choice, tmp_path / "video.mp4")
    assert opts["noplaylist"] is True


def test_noplaylist_false_for_multi_item(tmp_path):
    choice = DownloadChoice(output_kind="image", fmt="jpg")
    opts = downloader._build_ydl_opts(choice, tmp_path / "foto.jpg", multi_item=True)
    assert opts["noplaylist"] is False


def test_multi_item_outtmpl_has_unique_index(tmp_path):
    """Tanpa index unik, semua entry carousel/galeri saling timpa jadi 1 file."""
    choice = DownloadChoice(output_kind="image", fmt="jpg")
    opts = downloader._build_ydl_opts(choice, tmp_path / "foto.jpg", multi_item=True)
    assert "playlist_index" in opts["outtmpl"] or "autonumber" in opts["outtmpl"]


def test_multi_item_respects_selected_indices(tmp_path):
    """
    Regresi bug: selected_indices dari "pilih nomor tertentu" dulu cuma
    dipakai di jalur instaloader, diabaikan total di jalur yt-dlp normal
    (mis. galeri Reddit/X multi-gambar) - user pilih nomor tertentu tapi
    yang kedownload tetap semua atau cuma 1 item pertama.
    """
    choice = DownloadChoice(output_kind="image", fmt="jpg", selected_indices=[0, 2, 4])
    opts = downloader._build_ydl_opts(choice, tmp_path / "foto.jpg", multi_item=True)
    assert opts["playlist_items"] == "1,3,5"  # dikonversi ke 1-indexed buat yt-dlp


def test_multi_item_no_selection_downloads_all(tmp_path):
    choice = DownloadChoice(output_kind="image", fmt="jpg", selected_indices=None)
    opts = downloader._build_ydl_opts(choice, tmp_path / "foto.jpg", multi_item=True)
    assert "playlist_items" not in opts


# ---------------------------------------------------------------------------
# downloader._build_ydl_opts - force_single_item (bug playlist murni)
# ---------------------------------------------------------------------------

def test_force_single_item_sets_playlist_items_to_one(tmp_path):
    """
    Regresi bug: "noplaylist" TIDAK berefek buat URL playlist murni (tanpa
    "v="), dikonfirmasi maintainer yt-dlp sendiri (issue #5215, di-close
    sebagai "expected behavior" bukan bug). Tanpa force_single_item, kalau
    content_type VIDEO/AUDIO ternyata punya banyak entries (URL-nya
    sebenarnya playlist murni), seluruh playlist bakal kedownload dan semua
    entry saling menimpa nama file yang sama (outtmpl gak punya index unik
    buat kasus non-gambar) - cuma video terakhir yang tersisa di disk,
    padahal app melaporkan "sukses" pakai judul playlist.
    """
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    opts = downloader._build_ydl_opts(choice, tmp_path / "video.mp4", force_single_item=True)
    assert opts["playlist_items"] == "1"


def test_force_single_item_not_set_by_default(tmp_path):
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    opts = downloader._build_ydl_opts(choice, tmp_path / "video.mp4")
    assert "playlist_items" not in opts


def test_force_single_item_does_not_conflict_with_gallery_selection(tmp_path):
    """force_single_item dan selected_indices gallery TIDAK PERNAH aktif bersamaan (mutually exclusive by design)."""
    choice = DownloadChoice(output_kind="image", fmt="jpg", selected_indices=[0, 2])
    opts = downloader._build_ydl_opts(choice, tmp_path / "foto.jpg", multi_item=True, force_single_item=False)
    assert opts["playlist_items"] == "1,3"  # tetap dari selected_indices, bukan "1" doang


def test_download_forces_single_item_for_pure_playlist_video(tmp_path, monkeypatch):
    """
    Test integrasi end-to-end: download() dengan content_type VIDEO yang
    punya banyak entries (playlist murni, bukan galeri gambar) harus
    benar-benar mengirim playlist_items="1" ke yt-dlp - bukan cuma diuji di
    level _build_ydl_opts yang terisolasi.
    """
    captured_opts = {}

    class FakeYDL:
        def __init__(self, opts):
            captured_opts.update(opts)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            (tmp_path / "Judul-Playlist_2026.mp4").write_bytes(b"video pertama doang")

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYDL)

    class FakePlaylistContent:
        url = "https://www.youtube.com/playlist?list=PLxxxxxx"
        platform = "YouTube"
        title = "Judul Playlist"
        entries = [{"url": "video1"}, {"url": "video2"}, {"url": "video3"}]

    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")

    downloader.download(FakePlaylistContent(), choice, tmp_path, "%(platform)s_%(title)s_%(year)s")

    assert captured_opts.get("playlist_items") == "1"


def test_download_does_not_force_single_item_for_single_video(tmp_path, monkeypatch):
    """Video biasa (entries kosong/1) tidak boleh ke-treat sebagai playlist."""
    captured_opts = {}

    class FakeYDL:
        def __init__(self, opts):
            captured_opts.update(opts)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            (tmp_path / "Judul-Video_2026.mp4").write_bytes(b"video biasa")

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYDL)

    class FakeSingleVideoContent:
        url = "https://www.youtube.com/watch?v=abc"
        platform = "YouTube"
        title = "Judul Video"
        entries = []

    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")

    downloader.download(FakeSingleVideoContent(), choice, tmp_path, "%(platform)s_%(title)s_%(year)s")

    assert "playlist_items" not in captured_opts


def test_download_forces_single_item_for_video_thumbnail_from_playlist(tmp_path, monkeypatch):
    """Thumbnail video (bukan galeri gambar) dari playlist URL juga harus dilindungi, bukan cuma video/audio biasa."""
    captured_opts = {}

    class FakeYDL:
        def __init__(self, opts):
            captured_opts.update(opts)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            (tmp_path / "Judul-Playlist_2026.jpg").write_bytes(b"thumbnail")

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYDL)

    class FakePlaylistContent:
        url = "https://www.youtube.com/playlist?list=PLxxxxxx"
        platform = "YouTube"
        title = "Judul Playlist"
        entries = [{"url": "video1"}, {"url": "video2"}]

    choice = DownloadChoice(output_kind="image", fmt="jpg", is_video_thumbnail=True)

    downloader.download(FakePlaylistContent(), choice, tmp_path, "%(platform)s_%(title)s_%(year)s")

    assert captured_opts.get("playlist_items") == "1"


def test_download_computes_multi_item_before_resolve_duplicate(tmp_path, monkeypatch):
    """
    Regresi integrasi: memastikan download() betul-betul menghitung
    is_multi_item SEBELUM memanggil resolve_duplicate() dan meneruskannya -
    bukan cuma unit test terisolasi pada resolve_duplicate() sendirian yang
    bisa saja tetap "pass" meski urutan pemanggilannya di download() salah.
    """
    captured = {}

    def fake_resolve_duplicate(path, multi_item=False):
        captured["multi_item"] = multi_item
        return path

    monkeypatch.setattr(downloader, "resolve_duplicate", fake_resolve_duplicate)

    class FakeYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            # Cukup berhenti di sini - yang mau diverifikasi adalah argumen
            # resolve_duplicate() yang sudah terpanggil SEBELUM baris ini.
            raise downloader.yt_dlp.utils.DownloadError("stop early buat testing")

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYDL)

    class FakeGalleryContent:
        url = "https://example.com/gallery-post"
        platform = "Reddit"
        title = "Galeri Foto"
        entries = [{"url": "a"}, {"url": "b"}, {"url": "c"}]  # >1 entry -> harus multi_item

    choice = DownloadChoice(output_kind="image", fmt="jpg", selected_indices=None)

    with pytest.raises(downloader.DownloadFailed):
        downloader.download(FakeGalleryContent(), choice, tmp_path, "%(platform)s_%(title)s_%(year)s", max_retry=0)

    assert captured["multi_item"] is True


def test_download_single_image_not_treated_as_multi_item(tmp_path, monkeypatch):
    captured = {}

    def fake_resolve_duplicate(path, multi_item=False):
        captured["multi_item"] = multi_item
        return path

    monkeypatch.setattr(downloader, "resolve_duplicate", fake_resolve_duplicate)

    class FakeYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            raise downloader.yt_dlp.utils.DownloadError("stop early buat testing")

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYDL)

    class FakeSingleImageContent:
        url = "https://example.com/single-photo"
        platform = "Pinterest"
        title = "Satu Foto"
        entries = []  # cuma 1 gambar / tidak ada entries -> bukan multi_item

    choice = DownloadChoice(output_kind="image", fmt="jpg", selected_indices=None)

    with pytest.raises(downloader.DownloadFailed):
        downloader.download(FakeSingleImageContent(), choice, tmp_path, "%(platform)s_%(title)s_%(year)s", max_retry=0)

    assert captured["multi_item"] is False


# ---------------------------------------------------------------------------
# downloader._resolve_final_path
# ---------------------------------------------------------------------------

def test_resolve_final_path_single_item_exact_match(tmp_path):
    dest = tmp_path / "video.mp4"
    dest.write_bytes(b"fake-video-content")

    path, size, count = downloader._resolve_final_path(dest)

    assert path == dest
    assert size == len(b"fake-video-content")
    assert count == 1


def test_resolve_final_path_single_item_changed_extension(tmp_path):
    """yt-dlp kadang ganti ekstensi dari yang diminta (mis. setelah postprocessing)."""
    dest = tmp_path / "video.mp4"
    actual = tmp_path / "video.mkv"
    actual.write_bytes(b"fake-video-content")

    path, size, count = downloader._resolve_final_path(dest)

    assert path == actual
    assert count == 1


def test_resolve_final_path_ignores_leftover_thumbnail(tmp_path):
    dest = tmp_path / "video.mp4"
    (tmp_path / "video.jpg").write_bytes(b"thumbnail-sisa")  # thumbnail yang ketinggalan
    (tmp_path / "video.mkv").write_bytes(b"video-asli-lebih-besar")

    path, size, count = downloader._resolve_final_path(dest)

    assert path.suffix == ".mkv"  # bukan .jpg thumbnail
    assert count == 1


def test_resolve_final_path_no_file_found(tmp_path):
    path, size, count = downloader._resolve_final_path(tmp_path / "tidak-ada.mp4")
    assert size == 0
    assert count == 0


def test_resolve_final_path_multi_item_finds_all_files(tmp_path):
    """
    Regresi: fix multi-item ngubah outtmpl jadi punya suffix index
    ("Judul-1.jpg", "Judul-2.jpg", dst), tapi _resolve_final_path() dulu masih
    nyari pola tanpa suffix ("Judul.*") - jadi SELALU gagal ketemu file
    meskipun semua gambar sukses didownload, akibatnya dilaporkan sukses tapi
    dengan path yang gak exist dan ukuran 0 byte.
    """
    dest = tmp_path / "Judul.jpg"
    (tmp_path / "Judul-1.jpg").write_bytes(b"gambar-satu")
    (tmp_path / "Judul-2.jpg").write_bytes(b"gambar-dua-lebih-panjang")
    (tmp_path / "Judul-3.jpg").write_bytes(b"gambar-tiga")

    path, size, count = downloader._resolve_final_path(dest, multi_item=True)

    assert count == 3
    assert path.exists()
    assert size == len(b"gambar-satu") + len(b"gambar-dua-lebih-panjang") + len(b"gambar-tiga")


def test_resolve_final_path_multi_item_no_files_found(tmp_path):
    dest = tmp_path / "Judul.jpg"
    path, size, count = downloader._resolve_final_path(dest, multi_item=True)
    assert count == 0
    assert size == 0


def test_resolve_final_path_multi_item_no_false_positive_from_other_content(tmp_path):
    """
    Regresi edge case: file punya konten LAIN yang judulnya numpuk sebagai
    prefix (mis. "Sunset-Beach-1.jpg" milik konten "Sunset-Beach") tidak
    boleh ikut kehitung sebagai hasil download konten "Sunset" yang beda.
    """
    dest = tmp_path / "Sunset.jpg"
    (tmp_path / "Sunset-Beach-1.jpg").write_bytes(b"punya-konten-lain")
    (tmp_path / "Sunset-Beach-2.jpg").write_bytes(b"punya-konten-lain-juga")

    path, size, count = downloader._resolve_final_path(dest, multi_item=True)

    assert count == 0  # "Sunset" sendiri belum ada file-nya
    assert size == 0


