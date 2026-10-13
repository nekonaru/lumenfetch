"""test_options.py - Test menu YouTube (video MP4 / audio MP3)."""

from unittest import mock

from core import options
from core.detector import DetectedContent
from tests.conftest import SAMPLE_VIDEO_FORMATS


def _video_content(**kwargs):
    base = dict(
        url="https://youtube.com/watch?v=abc",
        title="Judul Video",
        content_type="VIDEO",
        duration=300,
        entries=[],
        raw_info={"formats": SAMPLE_VIDEO_FORMATS},
    )
    base.update(kwargs)
    return DetectedContent(**base)


def test_show_content_panel_displays_video():
    content = _video_content()

    printed = []
    with mock.patch.object(options.console, "print", lambda *a, **k: printed.append(a[0])):
        options.show_content_panel(content)

    panel_text = str(printed[0].renderable)
    assert "Judul Video" in panel_text
    assert "VIDEO" in panel_text
    assert "5:00" in panel_text


def test_show_content_panel_playlist_count():
    content = _video_content(entries=[{"url": "v1"}, {"url": "v2"}])

    printed = []
    with mock.patch.object(options.console, "print", lambda *a, **k: printed.append(a[0])):
        options.show_content_panel(content)

    assert "2 video" in str(printed[0].renderable)


def test_ask_video_choice_returns_mp4():
    with mock.patch.object(options.Prompt, "ask", return_value="3"):
        choice = options.ask_video_choice()

    assert choice.output_kind == "video"
    assert choice.fmt == "mp4"
    assert choice.quality == "720p"


def test_ask_video_choice_shows_size_estimate_when_content_given():
    content = _video_content()

    with mock.patch.object(options.Prompt, "ask", side_effect=["1"]):
        with mock.patch.object(options.console, "print") as fake_print:
            options.ask_video_choice(content, avg_speed_bps=5_000_000)

    printed_text = " ".join(str(call.args[0]) for call in fake_print.call_args_list)
    assert "MB" in printed_text
    assert "detik" in printed_text or "menit" in printed_text


def test_ask_video_choice_without_content_still_works():
    with mock.patch.object(options.Prompt, "ask", return_value="1"):
        choice = options.ask_video_choice()

    assert choice.output_kind == "video"


def test_ask_video_choice_no_estimate_when_formats_missing():
    content = _video_content(duration=100, raw_info={})

    with mock.patch.object(options.Prompt, "ask", return_value="1"):
        choice = options.ask_video_choice(content, avg_speed_bps=5_000_000)

    assert choice.output_kind == "video"


def test_ask_audio_choice_returns_mp3_with_bitrate():
    with mock.patch.object(options.Prompt, "ask", side_effect=["2"]):
        choice = options.ask_audio_choice()

    assert choice.output_kind == "audio"
    assert choice.fmt == "mp3"
    assert choice.quality == "320kbps"


def test_ask_audio_choice_shows_size_estimate_when_content_given():
    formats = [{"acodec": "mp4a", "abr": 128, "filesize": 4_000_000}]
    content = DetectedContent(
        url="https://youtube.com/watch?v=abc",
        title="Judul Lagu",
        content_type="AUDIO",
        duration=240,
        entries=[],
        raw_info={"formats": formats},
    )

    with mock.patch.object(options.Prompt, "ask", return_value="1"):
        with mock.patch.object(options.console, "print") as fake_print:
            options.ask_audio_choice(content, avg_speed_bps=5_000_000)

    printed_text = " ".join(str(call.args[0]) for call in fake_print.call_args_list)
    assert "MB" in printed_text


def test_resolve_choice_video_asks_output_type(monkeypatch):
    content = _video_content(raw_info={})

    responses = iter(["1", "1"])  # [1] Video, quality Best
    monkeypatch.setattr(options.Prompt, "ask", lambda *a, **k: next(responses))

    choice = options.resolve_choice(content)

    assert choice.output_kind == "video"
    assert choice.fmt == "mp4"


def test_resolve_choice_video_to_audio(monkeypatch):
    content = _video_content(raw_info={})

    responses = iter(["2", "1"])  # [2] Audio, bitrate Best
    monkeypatch.setattr(options.Prompt, "ask", lambda *a, **k: next(responses))

    choice = options.resolve_choice(content)

    assert choice.output_kind == "audio"
    assert choice.fmt == "mp3"


def test_resolve_choice_audio_content_skips_output_menu(monkeypatch):
    content = DetectedContent(
        url="https://youtube.com/watch?v=abc",
        title="Lagu",
        content_type="AUDIO",
        duration=200,
        entries=[],
        raw_info={},
    )
    monkeypatch.setattr(options.Prompt, "ask", lambda *a, **k: "1")

    choice = options.resolve_choice(content)

    assert choice.output_kind == "audio"


def test_resolve_choice_threads_avg_speed_to_video_choice(monkeypatch):
    content = _video_content()

    captured = {}
    original = options.ask_video_choice

    def spy(content_arg, avg_speed_bps=None):
        captured["avg_speed_bps"] = avg_speed_bps
        return original(content_arg, avg_speed_bps)

    monkeypatch.setattr(options, "ask_video_choice", spy)
    monkeypatch.setattr(options.Prompt, "ask", lambda *a, **k: "1")

    options.resolve_choice(content, avg_speed_bps=7_000_000)

    assert captured["avg_speed_bps"] == 7_000_000


def test_ask_playlist_mode():
    with mock.patch.object(options.Prompt, "ask", return_value="1"):
        assert options.ask_playlist_mode(5) == "single"
    with mock.patch.object(options.Prompt, "ask", return_value="2"):
        assert options.ask_playlist_mode(5) == "all"


def test_ask_subtitle_options_default_off():
    with mock.patch.object(options.Prompt, "ask", return_value="1"):
        assert options.ask_subtitle_options() == (False, None, False)


def test_ask_again_or_url_accepts_pasted_url():
    with mock.patch.object(options.Prompt, "ask", return_value="https://youtube.com/watch?v=abc"):
        assert options.ask_again_or_url() == "https://youtube.com/watch?v=abc"
    with mock.patch.object(options.Prompt, "ask", return_value="y"):
        assert options.ask_again_or_url() is True
    with mock.patch.object(options.Prompt, "ask", return_value="n"):
        assert options.ask_again_or_url() is False


def test_show_history_table_empty(capsys):
    options.show_history_table([])
    out = capsys.readouterr().out
    assert "riwayat" in out.lower()


def test_ask_cookies_browser_values():
    with mock.patch.object(options.Prompt, "ask", return_value="1"):
        assert options.ask_cookies_browser() is None
    with mock.patch.object(options.Prompt, "ask", return_value="2"):
        assert options.ask_cookies_browser() == "chrome"
