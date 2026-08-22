"""
test_lumenfetch.py
Unit test untuk fungsi-fungsi inti (sanitasi nama file, format ukuran,
naming template, resolve duplikat, config, validasi URL, dll).
"""

import pytest

from core import utils
from core.detector import is_valid_url

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


def test_add_history_entry_keeps_max_20(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path)
    config = utils.DEFAULT_CONFIG.copy()
    config["history"] = []

    for i in range(25):
        utils.add_history_entry(config, {"title": f"video-{i}"})

    assert len(config["history"]) == 20
    assert config["history"][0]["title"] == "video-24"  # entri terbaru di posisi awal


def test_clear_history(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path)
    config = utils.DEFAULT_CONFIG.copy()
    config["history"] = [{"title": "a"}, {"title": "b"}]

    utils.clear_history(config)

    assert config["history"] == []


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
