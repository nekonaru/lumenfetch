"""
test_lumenfetch.py
Unit test untuk fungsi-fungsi inti (sanitasi nama file, format ukuran,
naming template, resolve duplikat, config, validasi URL, dll).
"""

from pathlib import Path

import pytest

from core import downloader, instagram_fallback, update_checker, utils
from core.detector import is_valid_url
from core.options import DownloadChoice

# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------

def test_sanitize_filename_replaces_illegal_chars():
    assert utils.sanitize_filename('a:b*c?d"e<f>g|h') == "a_b_c_d_e_f_g_h"


def test_sanitize_filename_replaces_spaces_with_dash():
    assert utils.sanitize_filename("Lofi Hip Hop Radio") == "Lofi-Hip-Hop-Radio"


def test_sanitize_filename_collapses_multiple_dashes():
    assert utils.sanitize_filename("Judul   Cerita") == "Judul-Cerita"


def test_sanitize_filename_truncates_to_max_length():
    long_name = "a" * 200
    result = utils.sanitize_filename(long_name)
    assert len(result) == utils.MAX_TITLE_LEN


def test_sanitize_filename_handles_empty_string():
    assert utils.sanitize_filename("") == "untitled"


def test_sanitize_filename_handles_none():
    assert utils.sanitize_filename(None) == "untitled"


# ---------------------------------------------------------------------------
# build_filename
# ---------------------------------------------------------------------------

def test_build_filename_uses_template():
    template = "%(platform)s_%(title)s_%(year)s"
    result = utils.build_filename("YouTube", "Judul Video", "mp4", template)
    assert result.startswith("YouTube_Judul-Video_")
    assert result.endswith(".mp4")


def test_build_filename_sanitizes_platform_and_title():
    template = "%(platform)s_%(title)s_%(year)s"
    result = utils.build_filename("Some:Platform", "Judul<Aneh>", "jpg", template)
    assert ":" not in result
    assert "<" not in result and ">" not in result


def test_build_filename_falls_back_when_empty():
    template = "%(platform)s_%(title)s_%(year)s"
    result = utils.build_filename("", "", "mp3", template)
    assert result.startswith("Unknown_untitled_")


def test_build_filename_never_crashes_on_invalid_template():
    """
    Regresi bug: user bebas ganti naming_template lewat settings tanpa
    validasi. Template dengan placeholder salah ketik (mis. %(titel)s bukan
    %(title)s) dulu bikin build_filename() raise KeyError mentah - dan
    karena pemanggilannya di main.py ada DI LUAR try/except, ini bikin
    seluruh aplikasi crash total. build_filename() sekarang WAJIB fail-safe:
    fallback ke template default, bukan raise exception.
    """
    result = utils.build_filename("YouTube", "Judul Video", "mp4", "%(platform)s_%(titel)s_%(year)s")
    assert result  # tidak raise, dan hasilnya tetap nama file yang valid
    assert result.endswith(".mp4")


def test_build_filename_falls_back_on_malformed_template():
    result = utils.build_filename("YouTube", "Judul", "mp4", "%(platform)s_%s_broken")
    assert result.endswith(".mp4")


# ---------------------------------------------------------------------------
# is_valid_naming_template
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "template,expected",
    [
        ("%(platform)s_%(title)s_%(year)s", True),
        ("%(title)s only", True),
        ("%(platform)s_%(titel)s_%(year)s", False),  # typo: titel bukan title
        ("%(platform)s_%s_broken", False),
        ("", True),  # string kosong valid (hasil filename cuma ".ext")
    ],
)
def test_is_valid_naming_template(template, expected):
    assert utils.is_valid_naming_template(template) == expected


# ---------------------------------------------------------------------------
# resolve_duplicate
# ---------------------------------------------------------------------------

def test_resolve_duplicate_returns_same_path_if_not_exists(tmp_path):
    target = tmp_path / "file.mp4"
    assert utils.resolve_duplicate(target) == target


def test_resolve_duplicate_adds_suffix_if_exists(tmp_path):
    target = tmp_path / "file.mp4"
    target.touch()
    result = utils.resolve_duplicate(target)
    assert result == tmp_path / "file(1).mp4"


def test_resolve_duplicate_increments_suffix(tmp_path):
    (tmp_path / "file.mp4").touch()
    (tmp_path / "file(1).mp4").touch()
    result = utils.resolve_duplicate(tmp_path / "file.mp4")
    assert result == tmp_path / "file(2).mp4"


def test_resolve_duplicate_multi_item_detects_existing_group(tmp_path):
    """
    Regresi: outtmpl multi-item (galeri/carousel) menghasilkan file dengan
    suffix index ("Judul-1.jpg", "Judul-2.jpg", dst) - file persis
    "Judul.jpg" TIDAK PERNAH benar-benar dibuat. Kalau resolve_duplicate()
    dipanggil tanpa tau ini, ia salah menyimpulkan "belum pernah didownload"
    padahal grupnya sudah ada, sehingga download kedua diam-diam menimpa
    hasil download pertama alih-alih dapat suffix (1).
    """
    (tmp_path / "Judul-1.jpg").touch()
    (tmp_path / "Judul-2.jpg").touch()

    result = utils.resolve_duplicate(tmp_path / "Judul.jpg", multi_item=True)

    assert result == tmp_path / "Judul(1).jpg"


def test_resolve_duplicate_multi_item_no_existing_group(tmp_path):
    result = utils.resolve_duplicate(tmp_path / "Judul.jpg", multi_item=True)
    assert result == tmp_path / "Judul.jpg"


def test_resolve_duplicate_multi_item_increments_when_both_groups_exist(tmp_path):
    (tmp_path / "Judul-1.jpg").touch()
    (tmp_path / "Judul(1)-1.jpg").touch()

    result = utils.resolve_duplicate(tmp_path / "Judul.jpg", multi_item=True)

    assert result == tmp_path / "Judul(2).jpg"


def test_resolve_duplicate_single_item_unaffected_by_multi_item_default():
    """multi_item default False - behavior lama untuk single-item tidak boleh berubah."""
    import inspect

    sig = inspect.signature(utils.resolve_duplicate)
    assert sig.parameters["multi_item"].default is False


# ---------------------------------------------------------------------------
# find_indexed_files
# ---------------------------------------------------------------------------

def test_find_indexed_files_matches_numeric_suffix(tmp_path):
    (tmp_path / "Judul-1.jpg").touch()
    (tmp_path / "Judul-2.jpg").touch()
    (tmp_path / "Judul-10.jpg").touch()

    result = utils.find_indexed_files(tmp_path / "Judul.jpg")

    assert len(result) == 3


def test_find_indexed_files_sorts_numerically_not_alphabetically(tmp_path):
    """
    Regresi: sorted() string biasa bikin "Galeri-10.jpg" muncul SEBELUM
    "Galeri-2.jpg" (perbandingan karakter '1' < '2'), padahal urutan aslinya
    seharusnya 2 dulu baru 10. Harus diurutkan numerik berdasarkan angka
    index-nya, bukan alfabetis dari nama file.
    """
    # sengaja dibuat gak berurutan biar gak kebetulan lolos meski logic salah
    (tmp_path / "Galeri-10.jpg").touch()
    (tmp_path / "Galeri-2.jpg").touch()
    (tmp_path / "Galeri-1.jpg").touch()

    result = utils.find_indexed_files(tmp_path / "Galeri.jpg")

    assert [p.name for p in result] == ["Galeri-1.jpg", "Galeri-2.jpg", "Galeri-10.jpg"]


def test_find_indexed_files_does_not_false_positive_on_prefix_overlap(tmp_path):
    """
    Regresi edge case: glob polos "{stem}-*.*" false-positive kalau ada
    konten LAIN yang judulnya kebetulan numpuk sebagai prefix. Stem "Sunset"
    tidak boleh ikut cocok ke "Sunset-Beach-1.jpg" (itu punya konten beda,
    judulnya "Sunset-Beach"), karena setelah "Sunset-" karakternya "B",
    bukan digit - regex `-\\d+\\.` di akhir yang jadi pembeda.
    """
    (tmp_path / "Sunset-Beach-1.jpg").touch()
    (tmp_path / "Sunset-Beach-2.jpg").touch()

    result = utils.find_indexed_files(tmp_path / "Sunset.jpg")

    assert result == []  # bukan punya "Sunset", jadi harus kosong


def test_find_indexed_files_still_matches_its_own_prefix_stem(tmp_path):
    """Stem "Sunset-Beach" itu sendiri tetap harus match filenya sendiri."""
    (tmp_path / "Sunset-Beach-1.jpg").touch()
    (tmp_path / "Sunset-Beach-2.jpg").touch()

    result = utils.find_indexed_files(tmp_path / "Sunset-Beach.jpg")

    assert len(result) == 2


def test_resolve_duplicate_multi_item_no_false_positive_from_other_content(tmp_path):
    """
    Regresi end-to-end: download galeri "Sunset-Beach" duluan, lalu download
    galeri BARU "Sunset" (belum pernah ada) - harus dapat nama polos tanpa
    suffix (1), karena ini memang belum pernah didownload sebelumnya.
    """
    (tmp_path / "Sunset-Beach-1.jpg").touch()
    (tmp_path / "Sunset-Beach-2.jpg").touch()

    result = utils.resolve_duplicate(tmp_path / "Sunset.jpg", multi_item=True)

    assert result == tmp_path / "Sunset.jpg"  # bukan Sunset(1).jpg


# ---------------------------------------------------------------------------
# format_size / format_duration
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "num_bytes,expected",
    [
        (500, "500.0 B"),
        (1536, "1.5 KB"),
        (1024 * 1024 * 2, "2.0 MB"),
        (1024 ** 3 * 3, "3.0 GB"),
    ],
)
def test_format_size(num_bytes, expected):
    assert utils.format_size(num_bytes) == expected


def test_format_size_none():
    assert utils.format_size(None) == "?"


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (0, "-"),
        (None, "-"),
        (45, "0:45"),
        (125, "2:05"),
        (3725, "1:02:05"),
    ],
)
def test_format_duration(seconds, expected):
    assert utils.format_duration(seconds) == expected


# ---------------------------------------------------------------------------
# config.json (load/save/history) — pakai tmp_path biar tidak sentuh file asli
# ---------------------------------------------------------------------------

def test_load_config_creates_default_if_missing(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path)

    config = utils.load_config()

    assert config_path.exists()
    assert config["download_folder"] == "downloads/"
    assert config["max_retry"] == 3


def test_load_config_merges_missing_fields(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"download_folder": "custom/"}', encoding="utf-8")
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path)

    config = utils.load_config()

    assert config["download_folder"] == "custom/"
    assert config["max_retry"] == 3  # field yang hilang tetap keisi default


def test_load_config_resets_on_corrupt_json(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text("bukan json valid {{{", encoding="utf-8")
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path)

    config = utils.load_config()

    assert config == utils.DEFAULT_CONFIG


def test_get_default_config_returns_independent_copy():
    """get_default_config() harus deep copy - mengubah hasilnya tidak boleh
    ikut mengubah DEFAULT_CONFIG module-level ataupun salinan lain."""
    a = utils.get_default_config()
    b = utils.get_default_config()

    a["history"].append({"title": "x"})

    assert b["history"] == []
    assert utils.DEFAULT_CONFIG["history"] == []


def test_load_config_does_not_leak_history_across_instances(tmp_path, monkeypatch):
    """
    Regresi buat bug shared-mutable-default: DEFAULT_CONFIG.copy() itu shallow
    copy, jadi list "history" di config hasil load_config() dulu nunjuk ke
    object YANG SAMA dengan DEFAULT_CONFIG["history"]. Begitu add_history_entry()
    memutasi list itu, DEFAULT_CONFIG ikut "tercemar" dan bocor ke SEMUA config
    baru berikutnya - termasuk pas user pilih Settings > Reset ke default,
    yang harusnya bersih total tapi malah masih bawa riwayat lama.
    """
    config_path_a = tmp_path / "a" / "config.json"
    config_path_a.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path_a)
    config_a = utils.load_config()
    utils.add_history_entry(config_a, {"title": "video-a"})

    # DEFAULT_CONFIG module-level tidak boleh ikut kotor
    assert utils.DEFAULT_CONFIG["history"] == []

    # Config baru (mis. simulasi "reset ke default") harus benar-benar bersih
    config_path_b = tmp_path / "b" / "config.json"
    config_path_b.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path_b)
    config_b = utils.load_config()

    assert config_b["history"] == []


def test_add_history_entry_keeps_max_20(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path)
    config = utils.get_default_config()

    for i in range(25):
        utils.add_history_entry(config, {"title": f"video-{i}"})

    assert len(config["history"]) == 20
    assert config["history"][0]["title"] == "video-24"  # entri terbaru di posisi awal


def test_clear_history(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path)
    config = utils.get_default_config()
    config["history"] = [{"title": "a"}, {"title": "b"}]

    utils.clear_history(config)

    assert config["history"] == []


# ---------------------------------------------------------------------------
# build_cookies_from_browser
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "browser,expected",
    [
        (None, None),
        ("none", None),
        ("", None),
        ("chrome", ("chrome", None, None, None)),
        ("firefox", ("firefox", None, None, None)),
        ("bukan-browser-valid", None),
    ],
)
def test_build_cookies_from_browser(browser, expected):
    assert utils.build_cookies_from_browser(browser) == expected


# ---------------------------------------------------------------------------
# instagram_fallback.is_instagram_url / extract_shortcode
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.instagram.com/p/DcVMpAwH6QC/", True),
        ("https://instagram.com/reel/DcVLBJUS4Ie/?utm_source=x", True),
        ("https://www.youtube.com/watch?v=abc", False),
        ("https://tiktok.com/@user/video/123", False),
    ],
)
def test_is_instagram_url(url, expected):
    assert instagram_fallback.is_instagram_url(url) == expected


@pytest.mark.parametrize(
    "url,expected_shortcode",
    [
        ("https://www.instagram.com/p/DcVMpAwH6QC/", "DcVMpAwH6QC"),
        ("https://www.instagram.com/p/DcVMpAwH6QC/?utm_source=ig_web_copy_link", "DcVMpAwH6QC"),
        ("https://www.instagram.com/reel/DcVLBJUS4Ie/?igsi=abc", "DcVLBJUS4Ie"),
        ("https://www.instagram.com/tv/AbC123_-xyz/", "AbC123_-xyz"),
        ("https://www.youtube.com/watch?v=abc", None),
    ],
)
def test_extract_shortcode(url, expected_shortcode):
    assert instagram_fallback.extract_shortcode(url) == expected_shortcode


def test_convert_image_skips_when_already_jpg(tmp_path):
    src = tmp_path / "foto.jpg"
    src.write_bytes(b"fake-jpg-content")
    result = utils.convert_image(src, "jpg")
    assert result == src
    assert result.exists()


def test_convert_image_skips_when_jpeg_alias(tmp_path):
    src = tmp_path / "foto.jpeg"
    src.write_bytes(b"fake-jpeg-content")
    result = utils.convert_image(src, "jpg")
    assert result == src  # jpg dan jpeg dianggap sama


def test_download_photos_respects_selected_indices(tmp_path, monkeypatch):
    calls = []

    def fake_urlretrieve(url, dest):
        calls.append(url)
        Path(dest).write_bytes(b"fake-image-bytes")

    monkeypatch.setattr(instagram_fallback.urllib.request, "urlretrieve", fake_urlretrieve)

    class FakeContent:
        platform = "Instagram"
        title = "Judul Post"
        entries = [{"url": "https://x/1.jpg"}, {"url": "https://x/2.jpg"}, {"url": "https://x/3.jpg"}]

    results = instagram_fallback.download_photos(
        FakeContent(),
        selected_indices=[0, 2],
        target_ext="jpg",
        output_folder=tmp_path,
        naming_template="%(platform)s_%(title)s_%(year)s",
    )

    assert len(results) == 2
    assert calls == ["https://x/1.jpg", "https://x/3.jpg"]


def test_download_photos_downloads_all_when_no_selection(tmp_path, monkeypatch):
    def fake_urlretrieve(url, dest):
        Path(dest).write_bytes(b"fake-image-bytes")

    monkeypatch.setattr(instagram_fallback.urllib.request, "urlretrieve", fake_urlretrieve)

    class FakeContent:
        platform = "Instagram"
        title = "Judul Post"
        entries = [{"url": "https://x/1.jpg"}, {"url": "https://x/2.jpg"}]

    results = instagram_fallback.download_photos(
        FakeContent(),
        selected_indices=None,
        target_ext="jpg",
        output_folder=tmp_path,
        naming_template="%(platform)s_%(title)s_%(year)s",
    )

    assert len(results) == 2


# ---------------------------------------------------------------------------
# update_checker
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "version,expected",
    [
        ("2026.8.19", (2026, 8, 19)),
        ("2025.1.1", (2025, 1, 1)),
        ("2026.8.19.1", (2026, 8, 19, 1)),
    ],
)
def test_version_tuple(version, expected):
    assert update_checker._version_tuple(version) == expected


def test_check_for_update_detects_newer_version(monkeypatch):
    monkeypatch.setattr(update_checker, "get_installed_version", lambda: "2026.1.1")
    monkeypatch.setattr(update_checker, "get_latest_version", lambda: "2026.8.19")

    has_update, installed, latest = update_checker.check_for_update()

    assert has_update is True
    assert installed == "2026.1.1"
    assert latest == "2026.8.19"


def test_check_for_update_no_update_when_already_latest(monkeypatch):
    monkeypatch.setattr(update_checker, "get_installed_version", lambda: "2026.8.19")
    monkeypatch.setattr(update_checker, "get_latest_version", lambda: "2026.8.19")

    has_update, installed, latest = update_checker.check_for_update()

    assert has_update is False


def test_check_for_update_fails_safely_when_no_internet(monkeypatch):
    monkeypatch.setattr(update_checker, "get_installed_version", lambda: "2026.1.1")
    monkeypatch.setattr(update_checker, "get_latest_version", lambda: None)

    has_update, installed, latest = update_checker.check_for_update()

    assert has_update is False
    assert latest is None


def test_get_latest_version_returns_none_on_network_error(monkeypatch):
    def fake_urlopen(*args, **kwargs):
        raise update_checker.URLError("no internet")

    monkeypatch.setattr(update_checker.urllib.request, "urlopen", fake_urlopen)

    assert update_checker.get_latest_version() is None


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


# ---------------------------------------------------------------------------
# detector.is_valid_url
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://youtube.com/watch?v=abc123", True),
        ("http://example.com/video", True),
        ("bukan url", False),
        ("ftp://example.com/file", False),
        ("", False),
    ],
)
def test_is_valid_url(url, expected):
    assert is_valid_url(url) == expected
