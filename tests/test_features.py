"""test_features.py - Test fitur CLI, batch, ffmpeg, cookies, logging."""

from pathlib import Path
from unittest import mock

import pytest

import main
from core import utils
from core.detector import DetectedContent
from core.options import DownloadChoice


def _content(**kwargs):
    base = dict(url="https://youtube.com/watch?v=abc", title="T", content_type="VIDEO", duration=60, entries=[], raw_info={})
    base.update(kwargs)
    return DetectedContent(**base)


def test_parse_args_defaults():
    args = main.parse_args([])
    assert args.url is None
    assert args.jobs == 1
    assert args.playlist is None
    assert args.subs is False


def test_parse_args_url_and_flags():
    args = main.parse_args(
        [
            "https://youtube.com/watch?v=abc",
            "-f",
            "mp4",
            "-q",
            "720p",
            "-t",
            "video",
            "--playlist",
            "all",
            "--subs",
            "--sub-langs",
            "en,id",
            "--embed-metadata",
            "-y",
        ]
    )
    assert args.url == "https://youtube.com/watch?v=abc"
    assert args.fmt == "mp4"
    assert args.quality == "720p"
    assert args.playlist == "all"
    assert args.subs is True


def test_build_choice_from_args_defaults():
    content = _content()
    args = main.parse_args(["https://x"])
    choice = main.build_choice_from_args(content, args)
    assert choice.output_kind == "video"
    assert choice.fmt == "mp4"
    assert choice.playlist_mode == "single"


def test_build_choice_from_args_audio_mp3():
    content = _content(content_type="AUDIO")
    args = main.parse_args(["https://x", "-t", "audio"])
    choice = main.build_choice_from_args(content, args)
    assert choice.output_kind == "audio"
    assert choice.fmt == "mp3"


def test_apply_cli_overrides_playlist_subs():
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    args = main.parse_args(["https://x", "--playlist", "all", "--subs", "--embed-subs", "--embed-metadata"])
    main.apply_cli_overrides(choice, args)
    assert choice.playlist_mode == "all"
    assert choice.write_subs is True
    assert choice.embed_subs is True
    assert choice.embed_metadata is True


def test_read_batch_file_skips_comments(tmp_path):
    f = tmp_path / "batch.txt"
    f.write_text("https://youtube.com/watch?v=1\n\n# komen\nhttps://youtu.be/2\n", encoding="utf-8")
    assert main.read_batch_file(f) == ["https://youtube.com/watch?v=1", "https://youtu.be/2"]


def test_process_batch_sequential_counts(monkeypatch):
    calls = []

    def fake_process(url, config, **kwargs):
        calls.append(url)
        return url.endswith("/good")

    def fake_detect(url, cookies_browser=None, cookies_file=None):
        return _content(url=url)

    monkeypatch.setattr(main, "process_url", fake_process)
    monkeypatch.setattr(main, "detect", fake_detect)
    args = main.parse_args(["--jobs", "1"])
    summary = main.process_batch(["https://x.test/good", "https://x.test/bad"], utils.get_default_config(), args)
    assert summary == {"total": 2, "success": 1, "failed": 1}


def test_user_data_dir_and_migration(tmp_path, monkeypatch):
    import sys

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setitem(__import__("os").environ, "XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    if sys.platform.startswith("win"):
        monkeypatch.setitem(__import__("os").environ, "APPDATA", str(tmp_path / "appdata"))

    d = utils._user_data_dir()
    assert "lumenfetch" in str(d)

    target = tmp_path / "custom.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", target)
    utils._migrate_legacy_config()
    assert not target.exists()


def test_log_setup_creates_logger(tmp_path, monkeypatch):
    from core import log

    monkeypatch.setattr(utils, "_user_data_dir", lambda: tmp_path)
    import core.log as logmod

    monkeypatch.setattr(logmod, "_configured", False)
    logger = log.setup(verbose=True)
    assert logger is not None
    log.get_logger().info("hello-test")
    assert (tmp_path / "lumenfetch.log").exists()


def test_ask_playlist_mode_default_single():
    with mock.patch.object(main.options.Prompt, "ask", return_value="1"):
        assert main.options.ask_playlist_mode(5) == "single"
    with mock.patch.object(main.options.Prompt, "ask", return_value="2"):
        assert main.options.ask_playlist_mode(5) == "all"


def test_process_url_noninteractive_uses_override(tmp_path, monkeypatch):
    content = _content(url="https://x", title="T", duration=10)
    monkeypatch.setattr(main, "detect", lambda url, cookies_browser=None, cookies_file=None: content)
    monkeypatch.setattr(main.options, "show_content_panel", lambda c: None)
    captured = {}

    class FakeResult:
        filepath = tmp_path / "f.mp4"
        size_bytes = 10
        elapsed_seconds = 1.0
        file_count = 1

    def fake_download(*a, **k):
        captured["called"] = True
        return FakeResult()

    monkeypatch.setattr(main, "download", fake_download)
    monkeypatch.setattr(main.utils, "add_history_entry", lambda c, e: None)
    monkeypatch.setattr(main, "_ensure_ffmpeg", lambda: True)

    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    ok = main.process_url("https://x", utils.get_default_config(), choice_override=choice, auto_confirm=True)
    assert ok is True
    assert captured.get("called") is True


def test_classify_tiktok_challenge_as_blocked():
    from core.errors import ERROR_KIND_BLOCKED, classify_error, friendly_message

    err = Exception(
        "[TikTok] 123: Unexpected response from webpage request; please report this issue. "
        "Confirm you are on the latest version using yt-dlp -U"
    )
    assert classify_error(err) == ERROR_KIND_BLOCKED
    assert "Cookies" in friendly_message(ERROR_KIND_BLOCKED)


def test_classify_cookie_copy_failure():
    from core.errors import ERROR_KIND_COOKIES, classify_error, friendly_message

    err = Exception("Could not copy Chrome cookie database. See https://github.com/yt-dlp/yt-dlp/issues/7271 for more info")
    assert classify_error(err) == ERROR_KIND_COOKIES
    assert "tutup browser" in friendly_message(ERROR_KIND_COOKIES).lower()


def test_classify_dpapi_failure_as_cookies():
    from core.errors import ERROR_KIND_COOKIES, classify_error

    assert classify_error(Exception("Failed to decrypt with DPAPI. See issues/10927")) == ERROR_KIND_COOKIES
    assert classify_error(Exception("failed to load cookies")) == ERROR_KIND_COOKIES


def test_resolve_cookie_file(tmp_path):
    assert utils.resolve_cookie_file(None) is None
    assert utils.resolve_cookie_file("") is None
    assert utils.resolve_cookie_file(str(tmp_path / "tidak-ada.txt")) is None
    f = tmp_path / "cookies.txt"
    f.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    assert utils.resolve_cookie_file(str(f)) == str(f)


def test_apply_cookie_opts_prefers_file(tmp_path):
    f = tmp_path / "cookies.txt"
    f.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    opts: dict = {}
    assert utils.apply_cookie_opts(opts, "edge", str(f)) is True
    assert opts == {"cookiefile": str(f)}
    opts2: dict = {}
    assert utils.apply_cookie_opts(opts2, "edge", None) is True
    assert opts2["cookiesfrombrowser"][0] == "edge"
    assert utils.apply_cookie_opts({}, None, None) is False


def test_detect_uses_cookiefile(tmp_path, monkeypatch):
    from core import detector

    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    seen = {}

    class FakeYDL:
        def __init__(self, opts):
            seen.update(opts)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=False):
            return {"extractor_key": "Youtube", "title": "T", "vcodec": "h264"}

    monkeypatch.setattr(detector.yt_dlp, "YoutubeDL", FakeYDL)
    detector.detect("https://youtube.com/watch?v=abc", cookies_file=str(cookie_file))
    assert seen.get("cookiefile") == str(cookie_file)
    assert "cookiesfrombrowser" not in seen


def test_detect_retries_without_cookies_when_cookie_copy_fails(monkeypatch):
    from core import detector

    seen_opts = []

    class FakeYDL:
        def __init__(self, opts):
            seen_opts.append(dict(opts))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=False):
            if "cookiesfrombrowser" in seen_opts[-1]:
                raise detector.yt_dlp.utils.DownloadError("Could not copy Chrome cookie database")
            return {"extractor_key": "Youtube", "title": "Judul", "_type": "video", "vcodec": "h264"}

    monkeypatch.setattr(detector.yt_dlp, "YoutubeDL", FakeYDL)

    content = detector.detect("https://youtube.com/watch?v=abc", cookies_browser="edge")

    assert content.title == "Judul"
    assert "cookiesfrombrowser" in seen_opts[0]
    assert "cookiesfrombrowser" not in seen_opts[-1]


def test_detect_cookie_fallback_prepends_cookies_note(monkeypatch):
    from core import detector
    from core.detector import DetectionError

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=False):
            if "cookiesfrombrowser" in self.opts:
                raise detector.yt_dlp.utils.DownloadError("Could not copy Chrome cookie database")
            raise detector.yt_dlp.utils.DownloadError("This video is private")

    monkeypatch.setattr(detector.yt_dlp, "YoutubeDL", FakeYDL)

    with pytest.raises(DetectionError) as exc_info:
        detector.detect("https://youtube.com/watch?v=abc", cookies_browser="edge")

    assert "tutup browser" in str(exc_info.value).lower()
    assert "private" in str(exc_info.value).lower()


def test_ffmpeg_prefers_system(monkeypatch):
    from core import ffmpeg

    monkeypatch.setattr(ffmpeg.shutil, "which", lambda name: "C:/ffmpeg/ffmpeg.exe" if name == "ffmpeg" else None)
    monkeypatch.setattr(ffmpeg, "_verify", lambda *a, **k: True)
    assert ffmpeg.is_available() is True
    assert ffmpeg.ensure() is True


def test_ydl_logger_swallows_stderr(capsys, tmp_path, monkeypatch):
    import logging

    from core import log

    monkeypatch.setattr(utils, "_user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(logging.getLogger("lumenfetch.ydl"), "_lumenfetch_configured", False, raising=False)
    # Hapus handler lama agar terkonfigurasi ulang ke tmp_path.
    logging.getLogger("lumenfetch.ydl").handlers.clear()

    ydl_log = log.get_ydl_logger()
    ydl_log.error("ERROR: Could not copy Chrome cookie database")

    captured = capsys.readouterr()
    assert "Could not copy" not in captured.out
    assert "Could not copy" not in captured.err
    assert "Could not copy" in (tmp_path / "lumenfetch.log").read_text(encoding="utf-8")
    logging.getLogger("lumenfetch.ydl").handlers.clear()
    if hasattr(logging.getLogger("lumenfetch.ydl"), "_lumenfetch_configured"):
        delattr(logging.getLogger("lumenfetch.ydl"), "_lumenfetch_configured")


def test_base_opts_include_quiet_logger(tmp_path):
    from core import detector, downloader
    from core.options import DownloadChoice

    choice_opts = detector._base_ydl_opts()
    assert choice_opts["quiet"] is True
    assert hasattr(choice_opts["logger"], "error")

    dl_opts = downloader._build_ydl_opts(DownloadChoice(output_kind="video", quality="Best", fmt="mp4"), tmp_path / "v.mp4")
    assert dl_opts["quiet"] is True
    assert hasattr(dl_opts["logger"], "error")


def test_cli_version_exits_zero(monkeypatch, capsys):
    import sys

    monkeypatch.setattr(sys, "argv", ["lumenfetch", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        main.cli()
    assert exc_info.value.code == 0
    assert "2.0.0" in capsys.readouterr().out


def test_safe_io_never_raises():
    main._safe_io()
