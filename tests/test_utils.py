"""
test_lumenfetch.py
Unit tests for core functions (filename sanitizing, size formatting,
naming templates, duplicate resolution, config, URL validation, etc.).
"""

from pathlib import Path

import pytest

from core import update_checker, utils

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
    Bug regression: users could set any naming_template via settings
    without validation. A misspelled placeholder (e.g. %(titel)s instead of
    %(title)s) used to make build_filename() raise a raw KeyError - and
    because its call site in main.py is OUTSIDE try/except, this crashed
    the whole app. build_filename() must now fail safe: fall back to the
    default template instead of raising.
    """
    result = utils.build_filename("YouTube", "Judul Video", "mp4", "%(platform)s_%(titel)s_%(year)s")
    assert result  # does not raise, and the result is still a valid filename
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
    Regression: multi-item outtmpl (gallery/carousel) produces files with
    an index suffix ("Judul-1.jpg", "Judul-2.jpg", etc.) - the exact plain
    "Judul.jpg" file is NEVER actually created. Without knowing this,
    resolve_duplicate() wrongly concludes "not downloaded yet" even
    though its multi-item group already exists, so a second download
    silently overwrote the first one instead of getting a (1) suffix.
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
    """multi_item defaults to False - the old single-item behavior must not change."""
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
    Regression: plain string sorted() puts "Galeri-10.jpg" BEFORE
    "Galeri-2.jpg" (character comparison 1 < 2), but the true order is
    2 before 10. Must be sorted numerically by the index number,
    not alphabetically by filename.
    """
    # deliberately unordered so a wrong logic would not accidentally pass
    (tmp_path / "Galeri-10.jpg").touch()
    (tmp_path / "Galeri-2.jpg").touch()
    (tmp_path / "Galeri-1.jpg").touch()

    result = utils.find_indexed_files(tmp_path / "Galeri.jpg")

    assert [p.name for p in result] == ["Galeri-1.jpg", "Galeri-2.jpg", "Galeri-10.jpg"]


def test_find_indexed_files_does_not_false_positive_on_prefix_overlap(tmp_path):
    """
    Edge-case regression: a plain "{stem}-*.*" glob false-positives when
    OTHER content happens to share the title as a prefix. Stem "Sunset"
    must NOT match "Sunset-Beach-1.jpg" (that file belongs to different
    content titled "Sunset-Beach"), because the characters after
    "Sunset-" are "B", not a digit - the trailing regex is what
    disambiguates.
    """
    (tmp_path / "Sunset-Beach-1.jpg").touch()
    (tmp_path / "Sunset-Beach-2.jpg").touch()

    result = utils.find_indexed_files(tmp_path / "Sunset.jpg")

    assert result == []  # not owned by "Sunset", so must be empty


def test_find_indexed_files_still_matches_its_own_prefix_stem(tmp_path):
    """Stem "Sunset-Beach" itself must still match its own files."""
    (tmp_path / "Sunset-Beach-1.jpg").touch()
    (tmp_path / "Sunset-Beach-2.jpg").touch()

    result = utils.find_indexed_files(tmp_path / "Sunset-Beach.jpg")

    assert len(result) == 2


def test_resolve_duplicate_multi_item_no_false_positive_from_other_content(tmp_path):
    """
    Regresi end-to-end: download galeri "Sunset-Beach" duluan, lalu download
    NEW gallery "Sunset" (never seen before) - it must get the plain name
    without a (1) suffix, because it really was never downloaded before.
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
    assert size == 40_000_000 + 5_000_000  # 480p (lowest in sample) + audio


def test_estimate_video_size_returns_none_when_tier_unavailable():
    """
    If the requested tier (e.g. 360p) is not present in this content's
    format list, it MUST return None - not a guessed fallback using another
    tier's size (that would show a misleading number, e.g. 360p with the
    same size as Best/1080p).
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
    """Fixed bitrates (320/192/128) are computed from the target OUTPUT bitrate, not the source - more accurate after the ffmpeg convert."""
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
    """Legacy history entries (from before this feature existed) have no size_bytes/elapsed_seconds - must be skipped, not crash."""
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
    assert utils.format_eta(50_000_000, 5_000_000) == "~10 seconds"
    assert utils.format_eta(50_000_000, 5_000_000, lang="id") == "~10 detik"


def test_format_eta_in_minutes():
    assert utils.format_eta(600_000_000, 5_000_000) == "~2 minutes"
    assert utils.format_eta(600_000_000, 5_000_000, lang="id") == "~2 menit"


def test_format_eta_in_hours():
    assert utils.format_eta(50_000_000_000, 5_000_000) == "~2.8 hours"
    assert utils.format_eta(50_000_000_000, 5_000_000, lang="id") == "~2.8 jam"


def test_format_eta_none_when_missing_data():
    assert utils.format_eta(None, 5_000_000) is None
    assert utils.format_eta(50_000_000, None) is None
    assert utils.format_eta(50_000_000, 0) is None


# ---------------------------------------------------------------------------
# config.json (load/save/history) - use tmp_path so the real file is never touched
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
    Regression: the old default "downloads/" was a relative folder inside
    the project (not the real OS Downloads folder), unlike other browsers
    (Chrome/Firefox/Edge) whose default is always the user's Downloads
    folder. The default now has to be the real Downloads folder, an
    ABSOLUTE path, not a relative "downloads/" folder anymore.
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
    assert config["max_retry"] == 3  # missing field still filled with the default


def test_load_config_resets_on_corrupt_json(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text("bukan json valid {{{", encoding="utf-8")
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path)

    config = utils.load_config()

    assert config == utils.DEFAULT_CONFIG


def test_get_default_config_returns_independent_copy():
    """get_default_config() must deep-copy - mutating the result must not
    affect the module-level DEFAULT_CONFIG or any other copy."""
    a = utils.get_default_config()
    b = utils.get_default_config()

    a["history"].append({"title": "x"})

    assert b["history"] == []
    assert utils.DEFAULT_CONFIG["history"] == []


def test_load_config_does_not_leak_history_across_instances(tmp_path, monkeypatch):
    """
    Regression for the shared-mutable-default bug: DEFAULT_CONFIG.copy()
    was a shallow copy, so the "history" list in configs from load_config()
    used to point at the SAME object as DEFAULT_CONFIG["history"]. Once
    add_history_entry() mutated that list, DEFAULT_CONFIG became
    "contaminated" and leaked into EVERY new config afterwards - including
    after the user chose Settings > Reset to defaults, which should be a
    clean slate but was still carrying the old history.
    """
    config_path_a = tmp_path / "a" / "config.json"
    config_path_a.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path_a)
    config_a = utils.load_config()
    utils.add_history_entry(config_a, {"title": "video-a"})

    # the module-level DEFAULT_CONFIG must not get dirtied
    assert utils.DEFAULT_CONFIG["history"] == []

    # A new config (e.g. simulating "reset to defaults") must be truly clean
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
    assert config["history"][0]["title"] == "video-24"  # newest entry lands first


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
# utils.save_config - fail-safe when disk writes fail
# ---------------------------------------------------------------------------

def test_save_config_does_not_raise_on_oserror(tmp_path, monkeypatch):
    """
    Regression: save_config() (called from load_config, handle_settings,
    add_history_entry) used to be unguarded - when the folder the app runs
    in is read-only, it could crash the same way as the static_ffmpeg bug
    above.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path)

    def fake_open(*args, **kwargs):
        raise OSError("Read-only file system")

    monkeypatch.setattr(Path, "open", fake_open)

    utils.save_config(utils.get_default_config())  # must NOT raise


def test_load_config_still_works_when_disk_write_fails(tmp_path, monkeypatch):
    """
    End-to-end test: load_config() (which calls save_config() internally
    when config.json does not exist yet) must still return a valid
    in-memory config even when the disk write fails (e.g. read-only) - the
    save_config() fail-safe automatically protects load_config() too,
    without load_config() needing its own try/except.
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

    config = utils.load_config()  # must NOT raise

    assert config["download_folder"] == utils.get_default_download_folder()
    assert not config_path.exists()  # write failed, but the in-memory config is still valid




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


