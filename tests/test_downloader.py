"""test_downloader.py - Test download MP4/MP3 (selector, opts, retry, resolve)."""

import pytest

from core import downloader
from core.downloader import DownloadChoice


def test_format_selector_prefers_compatible_codecs_for_mp4():
    selector = downloader._quality_to_format_selector("Best", "mp4")
    assert "ext=mp4" in selector
    assert "ext=m4a" in selector


def test_format_selector_applies_height_filter():
    selector = downloader._quality_to_format_selector("720p", "mp4")
    assert "height<=720" in selector


def test_format_selector_worst_quality():
    selector = downloader._quality_to_format_selector("Worst", "mp4")
    assert "worstvideo" in selector and "worstaudio" in selector


def test_audio_quality_to_kbps():
    assert downloader._audio_quality_to_kbps("320kbps") == "320"
    assert downloader._audio_quality_to_kbps("Best") == "0"


def test_backoff_delay_grows_and_caps():
    d1 = downloader.backoff_delay(1)
    d2 = downloader.backoff_delay(2)
    d3 = downloader.backoff_delay(3)
    assert 2.0 <= d1 <= 3.0
    assert d2 > d1
    assert d3 > d2
    assert downloader.backoff_delay(99) <= 31.0


def test_video_opts_mp4_embeds_thumbnail(tmp_path):
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    opts = downloader._build_ydl_opts(choice, tmp_path / "video.mp4")
    assert "ext=mp4" in opts["format"]
    assert opts["merge_output_format"] == "mp4"
    assert {"key": "EmbedThumbnail"} in opts["postprocessors"]
    assert opts["writethumbnail"] is True


def test_audio_opts_mp3_extract(tmp_path):
    choice = DownloadChoice(output_kind="audio", quality="320kbps", fmt="mp3")
    opts = downloader._build_ydl_opts(choice, tmp_path / "lagu.mp3")
    assert opts["format"] == "bestaudio/best"
    pp = [p for p in opts["postprocessors"] if p["key"] == "FFmpegExtractAudio"]
    assert len(pp) == 1
    assert pp[0]["preferredcodec"] == "mp3"
    assert pp[0]["preferredquality"] == "320"


def test_build_opts_resume_enabled(tmp_path):
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    opts = downloader._build_ydl_opts(choice, tmp_path / "v.mp4")
    assert opts["continuedl"] is True
    assert opts["fragment_retries"] == 3


def test_build_opts_subs_and_metadata(tmp_path):
    choice = DownloadChoice(
        output_kind="video", quality="Best", fmt="mp4", write_subs=True, sub_langs=["en"], embed_metadata=True
    )
    opts = downloader._build_ydl_opts(choice, tmp_path / "v.mp4")
    assert opts["writesubtitles"] is True
    assert opts["subtitleslangs"] == ["en"]
    assert {"key": "FFmpegMetadata", "add_metadata": True} in opts["postprocessors"]


def test_build_opts_no_subs_by_default(tmp_path):
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    opts = downloader._build_ydl_opts(choice, tmp_path / "v.mp4")
    assert "writesubtitles" not in opts


def test_build_opts_uses_cookiefile(tmp_path):
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    opts = downloader._build_ydl_opts(choice, tmp_path / "v.mp4", None, str(cookie_file))
    assert opts["cookiefile"] == str(cookie_file)
    assert "cookiesfrombrowser" not in opts


def test_noplaylist_true_by_default(tmp_path):
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    opts = downloader._build_ydl_opts(choice, tmp_path / "video.mp4")
    assert opts["noplaylist"] is True


def test_force_single_item_sets_playlist_items_to_one(tmp_path):
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    opts = downloader._build_ydl_opts(choice, tmp_path / "video.mp4", force_single_item=True)
    assert opts["playlist_items"] == "1"


def test_force_single_item_not_set_by_default(tmp_path):
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    opts = downloader._build_ydl_opts(choice, tmp_path / "video.mp4")
    assert "playlist_items" not in opts


def test_playlist_all_opens_noplaylist_with_index(tmp_path):
    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4", playlist_mode="all")
    opts = downloader._build_ydl_opts(choice, tmp_path / "v.mp4", force_single_item=False, playlist_all=True)
    assert opts["noplaylist"] is False
    assert "playlist_index" in opts["outtmpl"]
    assert "playlist_items" not in opts


def test_download_single_video_success(tmp_path, monkeypatch):
    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            base = self.opts["outtmpl"].rsplit(".", 1)[0]
            from pathlib import Path as _P

            _P(f"{base}.mp4").write_bytes(b"fake-video")

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYDL)

    class FakeContent:
        url = "https://www.youtube.com/watch?v=abc"
        platform = "YouTube"
        title = "Judul Video"
        entries = []

    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    result = downloader.download(FakeContent(), choice, tmp_path, "%(platform)s_%(title)s_%(year)s")

    assert result.filepath.suffix == ".mp4"
    assert result.size_bytes == len(b"fake-video")
    assert result.file_count == 1


def test_download_forces_single_item_for_pure_playlist_video(tmp_path, monkeypatch):
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


def test_download_playlist_all_finds_indexed_files(tmp_path, monkeypatch):
    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            base = self.opts["outtmpl"].rsplit(".", 1)[0].replace("%(playlist_index,autonumber)d", "1")
            from pathlib import Path as _P

            _P(f"{base}.mp4").write_bytes(b"satu")
            _P(base.replace("-1", "-2") + ".mp4").write_bytes(b"dua-dua")

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYDL)

    class FakePlaylistContent:
        url = "https://www.youtube.com/playlist?list=PLxxxxxx"
        platform = "YouTube"
        title = "Judul Playlist"
        entries = [{"url": "v1"}, {"url": "v2"}]

    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4", playlist_mode="all")
    result = downloader.download(FakePlaylistContent(), choice, tmp_path, "%(title)s")

    assert result.file_count == 2
    assert result.size_bytes == len(b"satu") + len(b"dua-dua")


def test_download_retries_connection_with_backoff(tmp_path, monkeypatch):
    attempts = []

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            attempts.append(1)
            if len(attempts) < 3:
                raise downloader.yt_dlp.utils.DownloadError("Connection timed out")
            base = self.opts["outtmpl"].rsplit(".", 1)[0]
            from pathlib import Path as _P

            _P(f"{base}.mp4").write_bytes(b"ok")

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYDL)

    class FakeContent:
        url = "https://www.youtube.com/watch?v=abc"
        platform = "YouTube"
        title = "Judul"
        entries = []

    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    result = downloader.download(FakeContent(), choice, tmp_path, "%(title)s", max_retry=3)

    assert len(attempts) == 3
    assert result.file_count == 1


def test_download_retries_without_cookies_when_cookie_copy_fails(tmp_path, monkeypatch):
    calls = []

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            calls.append("cookiesfrombrowser" in self.opts)
            if "cookiesfrombrowser" in self.opts:
                raise downloader.yt_dlp.utils.DownloadError("Could not copy Chrome cookie database")
            (tmp_path / "Judul_2026.mp4").write_bytes(b"x")

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYDL)

    class FakeContent:
        url = "https://www.youtube.com/watch?v=abc"
        platform = "YouTube"
        title = "Judul"
        entries = []

    choice = DownloadChoice(output_kind="video", quality="Best", fmt="mp4")
    downloader.download(FakeContent(), choice, tmp_path, "%(title)s", cookies_browser="edge")

    assert calls == [True, False]


@pytest.mark.parametrize(
    "error_msg,expected_kind",
    [
        ("HTTP Error 429: Too Many Requests", "rate_limit"),
        ("rate-limit reached, try again later", "rate_limit"),
        ("This video has been removed by the uploader", "removed"),
        ("Content deleted by owner", "removed"),
        ("no longer available in your country", "removed"),
        ("HTTP Error 404: Not Found", "removed"),
        ("Connection timed out", "connection"),
        ("Private video, sign in required", "private"),
        ("No space left on device", "disk"),
        ("Unexpected response from webpage request", "blocked"),
        ("Could not copy Chrome cookie database", "cookies"),
        ("Failed to decrypt with DPAPI", "cookies"),
        ("some completely unrecognized error message", "unknown"),
    ],
)
def test_classify_error_kinds(error_msg, expected_kind):
    assert downloader._classify_error(Exception(error_msg)) == expected_kind


def test_resolve_final_path_single_item_exact_match(tmp_path):
    dest = tmp_path / "video.mp4"
    dest.write_bytes(b"fake-video-content")

    path, size, count = downloader._resolve_final_path(dest)

    assert path == dest
    assert size == len(b"fake-video-content")
    assert count == 1


def test_resolve_final_path_single_item_changed_extension(tmp_path):
    dest = tmp_path / "video.mp4"
    actual = tmp_path / "video.mkv"
    actual.write_bytes(b"fake-video-content")

    path, size, count = downloader._resolve_final_path(dest)

    assert path == actual
    assert count == 1


def test_resolve_final_path_ignores_leftover_thumbnail(tmp_path):
    dest = tmp_path / "video.mp4"
    (tmp_path / "video.jpg").write_bytes(b"thumbnail-sisa")
    (tmp_path / "video.mkv").write_bytes(b"video-asli-lebih-besar")

    path, size, count = downloader._resolve_final_path(dest)

    assert path.suffix == ".mkv"
    assert count == 1


def test_resolve_final_path_no_file_found(tmp_path):
    path, size, count = downloader._resolve_final_path(tmp_path / "tidak-ada.mp4")
    assert size == 0
    assert count == 0


def test_resolve_final_path_multi_item_finds_all_files(tmp_path):
    dest = tmp_path / "Judul.mp4"
    (tmp_path / "Judul-1.mp4").write_bytes(b"satu")
    (tmp_path / "Judul-2.mp4").write_bytes(b"dua-lebih-panjang")

    path, size, count = downloader._resolve_final_path(dest, multi_item=True)

    assert count == 2
    assert path.exists()
    assert size == len(b"satu") + len(b"dua-lebih-panjang")
