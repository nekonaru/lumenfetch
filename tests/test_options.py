"""
test_lumenfetch.py
Unit test untuk fungsi-fungsi inti (sanitasi nama file, format ukuran,
naming template, resolve duplikat, config, validasi URL, dll).
"""

from unittest import mock

import pytest

from core import options
from tests.conftest import SAMPLE_VIDEO_FORMATS

# ---------------------------------------------------------------------------
# options.show_content_panel - carousel campuran
# ---------------------------------------------------------------------------

def test_show_content_panel_displays_mixed_carousel_breakdown():
    from core.detector import DetectedContent

    content = DetectedContent(
        url="https://instagram.com/p/abc",
        platform="Instagram",
        title="Liburan seru",
        content_type="IMAGE",
        duration=None,
        entries=[{"is_video": False}, {"is_video": True}, {"is_video": False}],
        raw_info={"source": "instaloader", "photo_count": 2, "video_count": 1},
    )

    printed = []
    with mock.patch.object(options.console, "print", lambda *a, **k: printed.append(a[0])):
        options.show_content_panel(content)

    panel_text = str(printed[0].renderable)
    assert "2 gambar" in panel_text
    assert "1 video" in panel_text


def test_show_content_panel_pure_image_gallery_unaffected():
    """Galeri gambar biasa (non-instaloader, atau instaloader tanpa video) tampilannya tidak boleh berubah."""
    from core.detector import DetectedContent

    content = DetectedContent(
        url="https://pinterest.com/board/abc",
        platform="Pinterest",
        title="Board Foto",
        content_type="IMAGE",
        duration=None,
        entries=[{"url": "a"}, {"url": "b"}, {"url": "c"}],
        raw_info={},
    )

    printed = []
    with mock.patch.object(options.console, "print", lambda *a, **k: printed.append(a[0])):
        options.show_content_panel(content)

    panel_text = str(printed[0].renderable)
    assert "3 gambar" in panel_text
    assert "video" not in panel_text


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


# ---------------------------------------------------------------------------
# ask_audio_choice - skip menu bitrate untuk format lossless (WAV/FLAC)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fmt_index,expected_fmt", [("3", "wav"), ("4", "flac")])
def test_ask_audio_choice_skips_bitrate_menu_for_lossless(fmt_index, expected_fmt):
    """
    Regresi UX: WAV (PCM mentah) dan FLAC (lossless compression) tidak
    punya konsep "target bitrate" kayak MP3/M4A - preferredquality yang
    dikirim ke ffmpeg diabaikan untuk codec ini. Nawarin pilihan
    320/192/128kbps ke user cuma membingungkan, karena pilihannya gak
    beneran ngefek ke hasil akhir.
    """
    with mock.patch.object(options.Prompt, "ask", return_value=fmt_index) as fake_ask:
        choice = options.ask_audio_choice()

    assert choice.fmt == expected_fmt
    assert choice.quality == "Best"
    # Prompt.ask cuma dipanggil SEKALI (buat format), bukan dua kali (format + quality)
    assert fake_ask.call_count == 1


@pytest.mark.parametrize("fmt_index,expected_fmt", [("1", "mp3"), ("2", "m4a")])
def test_ask_audio_choice_still_asks_bitrate_for_lossy_formats(fmt_index, expected_fmt):
    """MP3/M4A (lossy) tidak boleh kena regresi - tetap harus nanya bitrate seperti biasa."""
    with mock.patch.object(options.Prompt, "ask", side_effect=[fmt_index, "2"]) as fake_ask:
        choice = options.ask_audio_choice()

    assert choice.fmt == expected_fmt
    assert choice.quality == "320kbps"
    assert fake_ask.call_count == 2


def test_ask_audio_choice_lossless_ignores_content_and_avg_speed():
    """Estimasi ukuran/waktu juga gak relevan buat lossless (gak ada pilihan quality buat diestimasi)."""
    from core.detector import DetectedContent

    content = DetectedContent(
        url="https://youtube.com/watch?v=abc",
        platform="YouTube",
        title="Judul Lagu",
        content_type="AUDIO",
        duration=240,
        entries=[],
        raw_info={"formats": [{"acodec": "mp4a", "abr": 128, "filesize": 4_000_000}]},
    )

    with mock.patch.object(options.Prompt, "ask", return_value="4"):  # FLAC
        choice = options.ask_audio_choice(content, avg_speed_bps=5_000_000)

    assert choice.fmt == "flac"
    assert choice.quality == "Best"


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


