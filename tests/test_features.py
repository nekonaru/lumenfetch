"""test_features.py - Test untuk upgrade batch ini."""

from pathlib import Path
from unittest import mock

import main
from core import downloader, utils
from core.options import DownloadChoice


def test_parse_args_defaults():
    args = main.parse_args([])
    assert args.url is None
    assert args.jobs == 1
    assert args.playlist is None
    assert args.subs is False


def test_parse_args_url_and_flags(tmp_path):
    args = main.parse_args(["https://youtube.com/watch?v=abc", "-f", "mp4", "-q", "720p", "-t", "video", "--playlist", "all", "--subs", "--sub-langs", "en,id", "--embed-metadata", "-y"])
    assert args.url == "https://youtube.com/watch?v=abc"
    assert args.fmt == "mp4"
    assert args.quality == "720p"
    assert args.playlist == "all"
    assert args.subs is True


def test_build_choice_from_args_defaults():
    from core.detector import DetectedContent

    content = DetectedContent(url="https://x", platform="YouTube", title="T", content_type="VIDEO", duration=60, entries=[], raw_info={})
    args = main.parse_args(["https://x"])
    choice = main.build_choice_from_args(content, args)
    assert choice.output_kind == "video"
    assert choice.fmt == "mp4"
    assert choice.playlist_mode == "single"


def test_apply_cli_overrides_playlist_subs():
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    args = main.parse_args(["https://x", "--playlist", "all", "--subs", "--embed-subs", "--embed-metadata"])
    main.apply_cli_overrides(choice, args)
    assert choice.playlist_mode == "all"
    assert choice.write_subs is True
    assert choice.embed_subs is True
    assert choice.embed_metadata is True


def test_backoff_delay_grows_and_caps():
    d1 = downloader.backoff_delay(1)
    d2 = downloader.backoff_delay(2)
    d3 = downloader.backoff_delay(3)
    assert 2.0 <= d1 <= 3.0
    assert d2 > d1
    assert d3 > d2
    assert downloader.backoff_delay(99) <= 31.0


def test_build_opts_resume_and_subs(tmp_path):
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4", write_subs=True, sub_langs=["en"], embed_metadata=True)
    opts = downloader._build_ydl_opts(choice, tmp_path / "v.mp4")
    assert opts["continuedl"] is True
    assert opts["writesubtitles"] is True
    assert opts["subtitleslangs"] == ["en"]
    assert {"key": "FFmpegMetadata", "add_metadata": True} in opts["postprocessors"]


def test_build_opts_playlist_all(tmp_path):
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4", playlist_mode="all")
    opts = downloader._build_ydl_opts(choice, tmp_path / "v.mp4", force_single_item=False, playlist_all=True)
    assert opts["noplaylist"] is False
    assert "playlist_index" in opts["outtmpl"]
    assert "playlist_items" not in opts


def test_ffmpeg_prefers_system(monkeypatch):
    from core import ffmpeg

    monkeypatch.setattr(ffmpeg.shutil, "which", lambda name: "C:/ffmpeg/ffmpeg.exe" if name == "ffmpeg" else None)
    monkeypatch.setattr(ffmpeg, "_verify", lambda *a, **k: True)
    assert ffmpeg.is_available() is True
    assert ffmpeg.ensure() is True


def test_read_batch_file_skips_comments(tmp_path):
    f = tmp_path / "batch.txt"
    f.write_text("https://a.com/1\n\n# komen\nhttps://b.com/2\n", encoding="utf-8")
    assert main.read_batch_file(f) == ["https://a.com/1", "https://b.com/2"]


def test_process_batch_sequential_counts(monkeypatch):
    from core.detector import DetectedContent

    calls = []

    def fake_process(url, config, **kwargs):
        calls.append(url)
        return url.endswith("/good")

    def fake_detect(url, cookies_browser=None):
        return DetectedContent(url=url, platform="X", title="T", content_type="VIDEO", duration=10, entries=[], raw_info={})

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

    # Migrasi dilewati saat CONFIG_PATH di-patch (lihat regresi sebelumnya).
    target = tmp_path / "custom.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", target)
    utils._migrate_legacy_config()
    assert not target.exists()


def test_log_setup_creates_logger(tmp_path, monkeypatch):
    from core import log

    monkeypatch.setattr(utils, "_user_data_dir", lambda: tmp_path)
    # reset flag setup antar test
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
    from core.detector import DetectedContent

    content = DetectedContent(url="https://x", platform="YouTube", title="T", content_type="VIDEO", duration=10, entries=[], raw_info={})
    monkeypatch.setattr(main, "detect", lambda url, cookies_browser=None: content)
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

    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    ok = main.process_url("https://x", utils.get_default_config(), choice_override=choice, auto_confirm=True)
    assert ok is True
    assert captured.get("called") is True
