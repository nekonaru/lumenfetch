"""
test_lumenfetch.py
Unit test untuk fungsi-fungsi inti (sanitasi nama file, format ukuran,
naming template, resolve duplikat, config, validasi URL, dll).
"""

from pathlib import Path

import pytest

import main
from core import downloader, instagram_fallback, options, update_checker, utils
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
# estimate_video_size_bytes / estimate_audio_size_bytes
# ---------------------------------------------------------------------------

SAMPLE_VIDEO_FORMATS = [
    {"vcodec": "avc1", "acodec": "none", "height": 1080, "ext": "mp4", "filesize": 150_000_000, "tbr": 4500},
    {"vcodec": "avc1", "acodec": "none", "height": 720, "ext": "mp4", "filesize": 80_000_000, "tbr": 2400},
    {"vcodec": "avc1", "acodec": "none", "height": 480, "ext": "mp4", "filesize": 40_000_000, "tbr": 1200},
    {"vcodec": "none", "acodec": "mp4a", "ext": "m4a", "filesize": 5_000_000, "abr": 128},
]


def test_estimate_video_size_best_picks_highest_resolution():
    size = utils.estimate_video_size_bytes(SAMPLE_VIDEO_FORMATS, "Best", duration=300)
    assert size == 150_000_000 + 5_000_000  # video 1080p + audio


def test_estimate_video_size_specific_tier():
    size = utils.estimate_video_size_bytes(SAMPLE_VIDEO_FORMATS, "720p", duration=300)
    assert size == 80_000_000 + 5_000_000


def test_estimate_video_size_worst_picks_lowest_resolution():
    size = utils.estimate_video_size_bytes(SAMPLE_VIDEO_FORMATS, "Worst", duration=300)
    assert size == 40_000_000 + 5_000_000  # 480p (paling rendah di sample) + audio


def test_estimate_video_size_returns_none_when_tier_unavailable():
    """
    Kalau tier yang diminta (mis. 360p) gak ada di daftar format konten ini,
    HARUS None - bukan fallback nebak pakai ukuran tier lain (itu bakal
    nampilin angka yang menyesatkan, mis. "360p" tapi ukurannya sama gede
    kayak "Best"/1080p).
    """
    size = utils.estimate_video_size_bytes(SAMPLE_VIDEO_FORMATS, "360p", duration=300)
    assert size is None


def test_estimate_video_size_returns_none_without_duration():
    size = utils.estimate_video_size_bytes(SAMPLE_VIDEO_FORMATS, "Best", duration=None)
    assert size is None


def test_estimate_video_size_returns_none_without_formats():
    size = utils.estimate_video_size_bytes([], "Best", duration=300)
    assert size is None


def test_estimate_video_size_falls_back_to_bitrate_when_no_filesize():
    formats = [
        {"vcodec": "avc1", "acodec": "none", "height": 720, "tbr": 2000, "filesize": None, "filesize_approx": None},
    ]
    size = utils.estimate_video_size_bytes(formats, "720p", duration=100)
    assert size == int(2000 * 1000 / 8 * 100)  # tbr(kbit/s) -> bytes


def test_estimate_audio_size_fixed_bitrate_uses_target_kbps():
    """Bitrate tetap (320/192/128) dihitung dari TARGET output, bukan sumbernya - lebih akurat setelah ffmpeg convert."""
    size = utils.estimate_audio_size_bytes([], "320kbps", duration=200)
    assert size == int(320 * 1000 / 8 * 200)


def test_estimate_audio_size_best_uses_source_format():
    formats = [{"acodec": "mp4a", "abr": 160, "filesize": 3_000_000}]
    size = utils.estimate_audio_size_bytes(formats, "Best", duration=150)
    assert size == 3_000_000


def test_estimate_audio_size_returns_none_without_duration():
    assert utils.estimate_audio_size_bytes(SAMPLE_VIDEO_FORMATS, "320kbps", duration=None) is None


# ---------------------------------------------------------------------------
# estimate_average_speed_bps / format_eta
# ---------------------------------------------------------------------------

def test_estimate_average_speed_computes_mean_from_history():
    history = [
        {"success": True, "size_bytes": 50_000_000, "elapsed_seconds": 10},  # 5 MB/s
        {"success": True, "size_bytes": 30_000_000, "elapsed_seconds": 6},  # 5 MB/s
    ]
    speed = utils.estimate_average_speed_bps(history)
    assert speed == 5_000_000


def test_estimate_average_speed_skips_failed_entries():
    history = [
        {"success": False, "size_bytes": 50_000_000, "elapsed_seconds": 10},
        {"success": True, "size_bytes": 20_000_000, "elapsed_seconds": 4},  # 5 MB/s
    ]
    speed = utils.estimate_average_speed_bps(history)
    assert speed == 5_000_000


def test_estimate_average_speed_skips_entries_missing_data():
    """Entri riwayat lama (sebelum fitur ini ada) gak punya size_bytes/elapsed_seconds - harus di-skip, bukan crash."""
    history = [
        {"success": True, "title": "video lama tanpa size_bytes"},
        {"success": True, "size_bytes": 10_000_000, "elapsed_seconds": 2},  # 5 MB/s
    ]
    speed = utils.estimate_average_speed_bps(history)
    assert speed == 5_000_000


def test_estimate_average_speed_returns_none_when_no_data():
    assert utils.estimate_average_speed_bps([]) is None
    assert utils.estimate_average_speed_bps([{"success": True}]) is None


def test_format_eta_under_a_minute():
    assert utils.format_eta(50_000_000, 5_000_000) == "~10 detik"


def test_format_eta_in_minutes():
    assert utils.format_eta(600_000_000, 5_000_000) == "~2 menit"


def test_format_eta_in_hours():
    assert utils.format_eta(50_000_000_000, 5_000_000) == "~2.8 jam"


def test_format_eta_none_when_missing_data():
    assert utils.format_eta(None, 5_000_000) is None
    assert utils.format_eta(50_000_000, None) is None
    assert utils.format_eta(50_000_000, 0) is None


# ---------------------------------------------------------------------------
# config.json (load/save/history) — pakai tmp_path biar tidak sentuh file asli
# ---------------------------------------------------------------------------

def test_load_config_creates_default_if_missing(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path)

    config = utils.load_config()

    assert config_path.exists()
    assert config["download_folder"] == utils.get_default_download_folder()
    assert config["max_retry"] == 3


def test_get_default_download_folder_is_os_downloads_folder():
    """
    Regresi: default lama "downloads/" itu folder relatif di dalam project
    (bukan folder Downloads asli sistem operasi), beda dari kebiasaan
    browser lain (Chrome/Firefox/Edge) yang defaultnya selalu ke folder
    Downloads user. Default sekarang harus folder Downloads asli, ABSOLUTE
    path, bukan folder relatif "downloads/" lagi.
    """
    result = utils.get_default_download_folder()
    assert result == str(Path.home() / "Downloads")
    assert Path(result).is_absolute()
    assert result != "downloads/"


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

    result = instagram_fallback.download_photos(
        FakeContent(),
        selected_indices=[0, 2],
        target_ext="jpg",
        output_folder=tmp_path,
        naming_template="%(platform)s_%(title)s_%(year)s",
    )

    assert result.success_count == 2
    assert result.failed_count == 0
    assert calls == ["https://x/1.jpg", "https://x/3.jpg"]


def test_download_photos_downloads_all_when_no_selection(tmp_path, monkeypatch):
    def fake_urlretrieve(url, dest):
        Path(dest).write_bytes(b"fake-image-bytes")

    monkeypatch.setattr(instagram_fallback.urllib.request, "urlretrieve", fake_urlretrieve)

    class FakeContent:
        platform = "Instagram"
        title = "Judul Post"
        entries = [{"url": "https://x/1.jpg"}, {"url": "https://x/2.jpg"}]

    result = instagram_fallback.download_photos(
        FakeContent(),
        selected_indices=None,
        target_ext="jpg",
        output_folder=tmp_path,
        naming_template="%(platform)s_%(title)s_%(year)s",
    )

    assert result.success_count == 2
    assert result.total_count == 2


def test_download_photos_partial_failure_continues_and_reports_accurately(tmp_path, monkeypatch):
    """
    Regresi bug: dulu satu foto gagal (mis. koneksi putus di tengah carousel)
    langsung raise dan membatalkan sisa foto lain yang belum dicoba, PLUS
    foto yang sudah sempat sukses sebelumnya jadi "yatim" (tersimpan di disk
    tapi tidak pernah dilaporkan balik ke caller karena fungsinya keburu
    crash). Sekarang tiap foto independen: yang gagal di-skip, yang lain
    tetap lanjut, dan hasilnya melaporkan angka sukses/gagal yang akurat.
    """

    def fake_urlretrieve(url, dest):
        if "2.jpg" in url:
            raise TimeoutError("koneksi putus")
        Path(dest).write_bytes(b"fake-image-bytes")

    monkeypatch.setattr(instagram_fallback.urllib.request, "urlretrieve", fake_urlretrieve)

    class FakeContent:
        platform = "Instagram"
        title = "Galeri"
        entries = [{"url": "https://x/1.jpg"}, {"url": "https://x/2.jpg"}, {"url": "https://x/3.jpg"}]

    result = instagram_fallback.download_photos(
        FakeContent(),
        selected_indices=None,
        target_ext="jpg",
        output_folder=tmp_path,
        naming_template="%(platform)s_%(title)s_%(year)s",
    )

    assert result.success_count == 2  # foto 1 dan 3 tetap berhasil
    assert result.failed_count == 1  # foto 2 gagal, tapi tidak membatalkan yang lain
    assert result.total_count == 3


def test_download_photos_all_fail(tmp_path, monkeypatch):
    def fake_urlretrieve(url, dest):
        raise TimeoutError("koneksi putus total")

    monkeypatch.setattr(instagram_fallback.urllib.request, "urlretrieve", fake_urlretrieve)

    class FakeContent:
        platform = "Instagram"
        title = "Galeri"
        entries = [{"url": "https://x/1.jpg"}, {"url": "https://x/2.jpg"}]

    result = instagram_fallback.download_photos(
        FakeContent(),
        selected_indices=None,
        target_ext="jpg",
        output_folder=tmp_path,
        naming_template="%(platform)s_%(title)s_%(year)s",
    )

    assert result.success_count == 0
    assert result.failed_count == 2


def test_download_photos_cleans_up_partial_file_on_failure(tmp_path, monkeypatch):
    """
    Regresi: urlretrieve() yang gagal DI TENGAH transfer (bukan gagal total
    dari awal) bisa saja sudah sempat menulis sebagian data ke `dest` sebelum
    error-nya muncul. Kalau file sisa ini tidak dibersihkan, dia nyangkut di
    folder output dengan nama yang KELIHATAN sah (padahal isinya 0-byte atau
    korup) - berpotensi membingungkan kalau user buka foldernya manual.
    """

    def fake_urlretrieve(url, dest):
        # Simulasikan urlretrieve yang sempat nulis sebagian data ke disk
        # SEBELUM raise (persis skenario koneksi putus di tengah transfer).
        Path(dest).write_bytes(b"data-parsial-yang-korup")
        raise TimeoutError("koneksi putus di tengah transfer")

    monkeypatch.setattr(instagram_fallback.urllib.request, "urlretrieve", fake_urlretrieve)

    class FakeContent:
        platform = "Instagram"
        title = "Galeri"
        entries = [{"url": "https://x/1.jpg"}]

    instagram_fallback.download_photos(
        FakeContent(),
        selected_indices=None,
        target_ext="jpg",
        output_folder=tmp_path,
        naming_template="%(platform)s_%(title)s_%(year)s",
    )

    leftover_files = list(tmp_path.glob("*"))
    assert leftover_files == [], f"file sisa masih ada, tidak dibersihkan: {leftover_files}"


# ---------------------------------------------------------------------------
# main.main() - startup tidak boleh crash kalau static_ffmpeg gagal
# ---------------------------------------------------------------------------

def test_main_does_not_crash_when_static_ffmpeg_fails(monkeypatch):
    """
    Regresi bug KRITIS: static_ffmpeg.add_paths() butuh internet buat
    download binary ffmpeg di percobaan PERTAMA di komputer itu. Kalau
    gagal (offline, GitHub diblokir firewall kantor/kampus, dll) dan
    pemanggilannya tidak dibungkus try/except, exception itu nembus sampai
    ke __main__ (yang cuma nangkep KeyboardInterrupt) - user lihat
    traceback Python mentah dan APLIKASI SAMA SEKALI TIDAK BISA DIBUKA,
    padahal banyak fitur (deteksi konten, download gambar tunggal, dll)
    sama sekali tidak butuh ffmpeg.
    """
    monkeypatch.setattr(
        main.static_ffmpeg, "add_paths", lambda: (_ for _ in ()).throw(RuntimeError("gagal download ffmpeg"))
    )
    monkeypatch.setattr(main.update_checker, "check_for_update", lambda: (False, "2026.1.1", None))
    monkeypatch.setattr(main.utils, "load_config", lambda: utils.get_default_config())
    monkeypatch.setattr(main.options, "show_header", lambda version: None)
    # Langsung "q" biar main() keluar dari loop tanpa perlu interaksi lain
    monkeypatch.setattr(main, "try_clipboard_url", lambda config, last: (None, last))
    monkeypatch.setattr(main.Prompt, "ask", lambda *a, **k: "q")

    main.main()  # TIDAK BOLEH raise apa pun


# ---------------------------------------------------------------------------
# utils.save_config - fail-safe kalau disk write gagal
# ---------------------------------------------------------------------------

def test_save_config_does_not_raise_on_oserror(tmp_path, monkeypatch):
    """
    Regresi: save_config() (dipanggil dari load_config, handle_settings,
    add_history_entry) dulu tidak dibungkus try/except - kalau folder
    tempat app dijalankan read-only, ini bisa crash dengan pola yang sama
    kayak bug static_ffmpeg di atas.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path)

    def fake_open(*args, **kwargs):
        raise OSError("Read-only file system")

    monkeypatch.setattr(Path, "open", fake_open)

    utils.save_config(utils.get_default_config())  # TIDAK BOLEH raise


def test_load_config_still_works_when_disk_write_fails(tmp_path, monkeypatch):
    """
    Test end-to-end: load_config() (yang manggil save_config() di baliknya
    saat config.json belum ada) harus tetap balikin config in-memory yang
    valid meski disk-nya gagal ditulis (mis. read-only) - fail-safe-nya
    save_config() harus otomatis melindungi load_config() juga, tanpa perlu
    load_config() punya try/except sendiri.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path)

    original_open = Path.open

    def fake_open(self, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode", "r")
        if self == config_path and "w" in mode:
            raise OSError("Read-only file system")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fake_open)

    config = utils.load_config()  # TIDAK BOLEH raise

    assert config["download_folder"] == utils.get_default_download_folder()
    assert not config_path.exists()  # gagal ke-tulis, tapi config in-memory tetap valid




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

    import unittest.mock as mock

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

    import unittest.mock as mock

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

    import unittest.mock as mock

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


# ---------------------------------------------------------------------------
# detector.strip_playlist_context
# ---------------------------------------------------------------------------

def test_strip_playlist_context_removes_list_from_video_url():
    """
    Regresi bug: link video biasa yang dicopy pas lagi nonton di dalam
    playlist YouTube otomatis kebawa "&list=...". detect() sengaja pakai
    noplaylist=False (biar galeri multi-gambar kedeteksi lengkap), jadi
    tanpa strip ini, video biasa yang kebawa "list=" salah narik metadata
    PLAYLIST-nya (bukan video itu sendiri) - judul hasil deteksi jadi
    salah, prosesnya lambat, dan rawan kena rate-limit.
    """
    from core.detector import strip_playlist_context

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxxxxx&index=5"
    result = strip_playlist_context(url)

    assert "list=" not in result
    assert "index=" not in result
    assert "v=dQw4w9WgXcQ" in result


def test_strip_playlist_context_keeps_pure_playlist_url_unchanged():
    """URL playlist murni (tanpa v=, memang user minta playlist-nya) dibiarkan apa adanya."""
    from core.detector import strip_playlist_context

    url = "https://www.youtube.com/playlist?list=PLxxxxxx"
    assert strip_playlist_context(url) == url


def test_strip_playlist_context_untouched_when_no_list_param():
    from core.detector import strip_playlist_context

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert strip_playlist_context(url) == url


def test_strip_playlist_context_handles_shorts_url():
    from core.detector import strip_playlist_context

    url = "https://www.youtube.com/shorts/abc123?list=PLxxx"
    result = strip_playlist_context(url)
    assert "list=" not in result


def test_strip_playlist_context_handles_youtu_be_short_link():
    """
    Regresi: format link youtu.be/<video-id> (paling sering muncul lewat
    tombol Share YouTube, termasuk dari dalam playlist/mobile app) punya
    video ID di PATH, bukan di query "v=" - kondisi has_specific_video yang
    cuma cek "v" in query dan path /shorts//embed/ jadi kelewat kasus ini,
    parameter "list" tetap kebawa dan bug lama (metadata playlist salah
    tertarik) masih kejadian persis kayak sebelum fix pertama.
    """
    from core.detector import strip_playlist_context

    url = "https://youtu.be/dQw4w9WgXcQ?list=PLxxxxxx&index=5"
    result = strip_playlist_context(url)

    assert "list=" not in result
    assert "index=" not in result
    assert "dQw4w9WgXcQ" in result


def test_strip_playlist_context_youtu_be_without_list_unchanged():
    from core.detector import strip_playlist_context

    url = "https://youtu.be/dQw4w9WgXcQ"
    assert strip_playlist_context(url) == url


def test_strip_playlist_context_youtu_be_root_without_video_id_unchanged():
    """youtu.be tanpa video ID di path (edge case langka) tidak boleh dianggap 'video spesifik'."""
    from core.detector import strip_playlist_context

    url = "https://youtu.be/?list=PLxxxxxx"
    assert strip_playlist_context(url) == url


def test_strip_playlist_context_does_not_match_lookalike_domain():
    """
    Regresi presisi: "netloc.endswith('youtu.be')" secara teknis juga match
    domain asing kayak "notyoutu.be" (cuma cek akhiran string, bukan domain
    persis). Harus exact match "youtu.be" atau subdomain sah "*.youtu.be".
    """
    from core.detector import strip_playlist_context

    url = "https://notyoutu.be/ID?list=PLxxxxxx"
    assert strip_playlist_context(url) == url  # domain asing, TIDAK boleh ke-strip


def test_strip_playlist_context_handles_youtu_be_subdomain():
    from core.detector import strip_playlist_context

    url = "https://www.youtu.be/dQw4w9WgXcQ?list=PLxxxxxx"
    result = strip_playlist_context(url)
    assert "list=" not in result


def test_strip_playlist_context_untouched_for_non_youtube_url():
    """Galeri Pinterest/Reddit/Twitter tidak pernah punya parameter 'list' - dijamin tidak kesentuh sama sekali."""
    from core.detector import strip_playlist_context

    url = "https://www.pinterest.com/pin/123456789/"
    assert strip_playlist_context(url) == url


def test_detect_calls_extract_info_with_stripped_url(monkeypatch):
    """Test integrasi: detect() harus benar-benar kirim URL yang sudah bersih ke yt-dlp, bukan cuma fungsi terisolasi."""
    from core import detector

    captured_urls = []

    class FakeYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=False):
            captured_urls.append(url)
            return {
                "extractor_key": "Youtube",
                "title": "Judul Video Asli",
                "_type": "video",
                "vcodec": "h264",
                "duration": 120,
            }

    monkeypatch.setattr(detector.yt_dlp, "YoutubeDL", FakeYDL)

    content = detector.detect("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxxxxx&index=5")

    assert "list=" not in captured_urls[0]
    assert content.title == "Judul Video Asli"
    assert "list=" not in content.url


# ---------------------------------------------------------------------------
# options.ask_video_choice / ask_audio_choice - label estimasi ukuran & waktu
# ---------------------------------------------------------------------------

def test_ask_video_choice_shows_size_estimate_when_content_given():
    from core.detector import DetectedContent

    content = DetectedContent(
        url="https://youtube.com/watch?v=abc",
        platform="YouTube",
        title="Judul Video",
        content_type="VIDEO",
        duration=300,
        entries=[],
        raw_info={"formats": SAMPLE_VIDEO_FORMATS},
    )

    import unittest.mock as mock

    with mock.patch.object(options.Prompt, "ask", side_effect=["1", "1"]):
        with mock.patch.object(options.console, "print") as fake_print:
            options.ask_video_choice(content, avg_speed_bps=5_000_000)

    printed_text = " ".join(str(call.args[0]) for call in fake_print.call_args_list)
    assert "MB" in printed_text
    assert "detik" in printed_text or "menit" in printed_text


def test_ask_video_choice_without_content_still_works():
    """Backward-compat: dipanggil tanpa content (mis. dari test lama) tidak boleh crash, cuma gak ada estimasi."""
    import unittest.mock as mock

    with mock.patch.object(options.Prompt, "ask", side_effect=["1", "1"]):
        choice = options.ask_video_choice()

    assert choice.output_kind == "video"


def test_ask_video_choice_no_estimate_when_formats_missing():
    """Konten tanpa data 'formats' (mis. platform yang gak expose) tetap jalan normal tanpa estimasi."""
    from core.detector import DetectedContent

    content = DetectedContent(
        url="https://example.com/video",
        platform="Unknown",
        title="Video",
        content_type="VIDEO",
        duration=100,
        entries=[],
        raw_info={},  # tidak ada key "formats" sama sekali
    )

    import unittest.mock as mock

    with mock.patch.object(options.Prompt, "ask", side_effect=["1", "1"]):
        choice = options.ask_video_choice(content, avg_speed_bps=5_000_000)

    assert choice.output_kind == "video"


def test_ask_audio_choice_shows_size_estimate_when_content_given():
    from core.detector import DetectedContent

    formats = [{"acodec": "mp4a", "abr": 128, "filesize": 4_000_000}]
    content = DetectedContent(
        url="https://youtube.com/watch?v=abc",
        platform="YouTube",
        title="Judul Lagu",
        content_type="AUDIO",
        duration=240,
        entries=[],
        raw_info={"formats": formats},
    )

    import unittest.mock as mock

    with mock.patch.object(options.Prompt, "ask", side_effect=["1", "1"]):
        with mock.patch.object(options.console, "print") as fake_print:
            options.ask_audio_choice(content, avg_speed_bps=5_000_000)

    printed_text = " ".join(str(call.args[0]) for call in fake_print.call_args_list)
    assert "MB" in printed_text


def test_resolve_choice_threads_avg_speed_to_video_choice(monkeypatch):
    """Test integrasi: resolve_choice() harus benar-benar meneruskan avg_speed_bps sampai ke ask_video_choice()."""
    from core.detector import DetectedContent

    content = DetectedContent(
        url="https://youtube.com/watch?v=abc",
        platform="YouTube",
        title="Judul Video",
        content_type="VIDEO",
        duration=300,
        entries=[],
        raw_info={"formats": SAMPLE_VIDEO_FORMATS},
    )

    captured = {}
    original = options.ask_video_choice

    def spy(content_arg, avg_speed_bps=None):
        captured["avg_speed_bps"] = avg_speed_bps
        return original(content_arg, avg_speed_bps)

    monkeypatch.setattr(options, "ask_video_choice", spy)
    monkeypatch.setattr(options.Prompt, "ask", lambda *a, **k: "1")

    options.resolve_choice(content, avg_speed_bps=7_000_000)

    assert captured["avg_speed_bps"] == 7_000_000


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


# ---------------------------------------------------------------------------
# main.try_clipboard_url
# ---------------------------------------------------------------------------

def test_try_clipboard_url_disabled_by_auto_paste_off(monkeypatch):
    monkeypatch.setattr(main.pyperclip, "paste", lambda: "https://youtube.com/watch?v=abc")
    url, last = main.try_clipboard_url({"auto_paste": False}, last_prompted=None)
    assert url is None
    assert last is None


def test_try_clipboard_url_ignores_invalid_clipboard_content(monkeypatch):
    monkeypatch.setattr(main.pyperclip, "paste", lambda: "bukan url sama sekali")
    url, last = main.try_clipboard_url({"auto_paste": True}, last_prompted=None)
    assert url is None
    assert last is None


def test_try_clipboard_url_returns_url_when_accepted(monkeypatch):
    monkeypatch.setattr(main.pyperclip, "paste", lambda: "https://youtube.com/watch?v=abc")
    monkeypatch.setattr(main.Prompt, "ask", lambda *a, **k: "y")

    url, last = main.try_clipboard_url({"auto_paste": True}, last_prompted=None)

    assert url == "https://youtube.com/watch?v=abc"
    assert last == "https://youtube.com/watch?v=abc"


def test_try_clipboard_url_tracks_declined_content(monkeypatch):
    monkeypatch.setattr(main.pyperclip, "paste", lambda: "https://youtube.com/watch?v=abc")
    monkeypatch.setattr(main.Prompt, "ask", lambda *a, **k: "n")

    url, last = main.try_clipboard_url({"auto_paste": True}, last_prompted=None)

    assert url is None
    assert last == "https://youtube.com/watch?v=abc"  # tetap dicatat meski ditolak


def test_try_clipboard_url_does_not_reask_same_content(monkeypatch):
    """
    Regresi UX: dulu clipboard yang isinya belum berubah ditawarkan LAGI
    setiap loop, jadi user harus jawab 'n' berulang kali padahal isinya
    sama persis dengan yang baru saja ditolak/sudah dipakai.
    """
    prompt_call_count = [0]

    def fake_prompt_ask(*args, **kwargs):
        prompt_call_count[0] += 1
        return "n"

    monkeypatch.setattr(main.pyperclip, "paste", lambda: "https://youtube.com/watch?v=abc")
    monkeypatch.setattr(main.Prompt, "ask", fake_prompt_ask)

    config = {"auto_paste": True}
    url1, last1 = main.try_clipboard_url(config, last_prompted=None)
    url2, last2 = main.try_clipboard_url(config, last_prompted=last1)

    assert prompt_call_count[0] == 1  # cuma ditanya SEKALI, bukan dua kali
    assert url1 is None and url2 is None
    assert last1 == last2 == "https://youtube.com/watch?v=abc"


def test_try_clipboard_url_reasks_when_content_changes(monkeypatch):
    monkeypatch.setattr(main.pyperclip, "paste", lambda: "https://youtube.com/watch?v=xyz")
    monkeypatch.setattr(main.Prompt, "ask", lambda *a, **k: "y")

    # last_prompted dari URL SEBELUMNYA yang beda -> harus tetap ditanya lagi
    url, last = main.try_clipboard_url({"auto_paste": True}, last_prompted="https://youtube.com/watch?v=abc")

    assert url == "https://youtube.com/watch?v=xyz"


# ---------------------------------------------------------------------------
# main.handle_settings - ganti folder download
# ---------------------------------------------------------------------------

def test_handle_settings_expands_tilde_in_folder_path(monkeypatch, tmp_path):
    """
    User ketik path pakai "~" (mis. "~/Documents/MyDownloads") berharap itu
    ke-resolve ke home folder-nya, bukan diperlakukan sebagai nama folder
    relatif literal bernama "~" di dalam folder project.
    """
    menu_choices = iter(["1", "7"])
    monkeypatch.setattr(main.options, "show_settings_menu", lambda config: next(menu_choices))
    monkeypatch.setattr(main.Prompt, "ask", lambda *a, **k: "~/Documents/MyDownloads")
    monkeypatch.setattr(main.utils, "save_config", lambda config: None)

    config = utils.get_default_config()
    result = main.handle_settings(config)

    assert result["download_folder"] == str(Path.home() / "Documents" / "MyDownloads")
    assert "~" not in result["download_folder"]


def test_handle_settings_accepts_absolute_path_unchanged(monkeypatch, tmp_path):
    menu_choices = iter(["1", "7"])
    monkeypatch.setattr(main.options, "show_settings_menu", lambda config: next(menu_choices))
    monkeypatch.setattr(main.Prompt, "ask", lambda *a, **k: str(tmp_path / "CustomFolder"))
    monkeypatch.setattr(main.utils, "save_config", lambda config: None)

    config = utils.get_default_config()
    result = main.handle_settings(config)

    assert result["download_folder"] == str(tmp_path / "CustomFolder")


# ---------------------------------------------------------------------------
# main.process_url - warning transparan buat URL playlist murni
# ---------------------------------------------------------------------------

def test_process_url_warns_user_about_pure_playlist(tmp_path, monkeypatch):
    """
    User berhak tahu kalau URL yang mereka paste ternyata playlist murni dan
    cuma video pertama yang bakal didownload - daripada diam-diam cuma
    ngasih 1 dari sekian video yang mereka kira bakal didownload semua.
    """
    from core.detector import DetectedContent

    playlist_content = DetectedContent(
        url="https://www.youtube.com/playlist?list=PLxxxxxx",
        platform="YouTube",
        title="Judul Playlist",
        content_type="VIDEO",
        duration=None,
        entries=[{"url": "v1"}, {"url": "v2"}, {"url": "v3"}],
        raw_info={},
    )

    monkeypatch.setattr(main, "detect", lambda url, cookies_browser=None: playlist_content)
    monkeypatch.setattr(main.options, "show_content_panel", lambda content: None)
    monkeypatch.setattr(
        main.options, "resolve_choice", lambda content, avg_speed_bps=None: DownloadChoice(output_kind="video", fmt="mp4")
    )
    monkeypatch.setattr(main.options, "confirm_filename", lambda filename: False)  # keluar lebih awal, cukup cek warning

    printed = []
    monkeypatch.setattr(main.console, "print", lambda *a, **k: printed.append(str(a[0]) if a else ""))

    main.process_url("https://www.youtube.com/playlist?list=PLxxxxxx", utils.get_default_config())

    warning_shown = any("playlist" in line.lower() and "3 video" in line for line in printed)
    assert warning_shown, f"Warning playlist tidak muncul. Yang ke-print: {printed}"


def test_process_url_no_warning_for_single_video(tmp_path, monkeypatch):
    from core.detector import DetectedContent

    single_content = DetectedContent(
        url="https://www.youtube.com/watch?v=abc",
        platform="YouTube",
        title="Judul Video",
        content_type="VIDEO",
        duration=120,
        entries=[],
        raw_info={},
    )

    monkeypatch.setattr(main, "detect", lambda url, cookies_browser=None: single_content)
    monkeypatch.setattr(main.options, "show_content_panel", lambda content: None)
    monkeypatch.setattr(
        main.options, "resolve_choice", lambda content, avg_speed_bps=None: DownloadChoice(output_kind="video", fmt="mp4")
    )
    monkeypatch.setattr(main.options, "confirm_filename", lambda filename: False)

    printed = []
    monkeypatch.setattr(main.console, "print", lambda *a, **k: printed.append(str(a[0]) if a else ""))

    main.process_url("https://www.youtube.com/watch?v=abc", utils.get_default_config())

    warning_shown = any("playlist berisi" in line.lower() for line in printed)
    assert not warning_shown


