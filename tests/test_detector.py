"""test_detector.py - Test deteksi YouTube (validasi URL, playlist strip, detect)."""

import pytest

from core import detector
from core.detector import DetectionError, detect, is_valid_url, is_youtube_url, strip_playlist_context


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.youtube.com/watch?v=abc123", True),
        ("https://youtube.com/watch?v=abc123", True),
        ("https://youtu.be/abc123", True),
        ("https://www.youtu.be/abc123", True),
        ("https://music.youtube.com/watch?v=abc123", True),
        ("https://m.youtube.com/watch?v=abc123", True),
        ("https://www.youtube.com/shorts/abc123", True),
        ("https://www.youtube.com/playlist?list=PLxxxxxx", True),
        ("https://www.tiktok.com/@u/video/123", False),
        ("https://www.instagram.com/p/ABC/", False),
        ("https://example.com/video", False),
        ("bukan url", False),
        ("ftp://youtube.com/watch?v=abc", False),
        ("", False),
    ],
)
def test_is_youtube_url(url, expected):
    assert is_youtube_url(url) == expected


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://youtube.com/watch?v=abc123", True),
        ("https://youtu.be/abc123", True),
        ("bukan url", False),
        ("https://tiktok.com/@user/video/123", False),
        ("ftp://youtube.com/watch?v=abc", False),
        ("", False),
    ],
)
def test_is_valid_url(url, expected):
    assert is_valid_url(url) == expected


def test_strip_playlist_context_removes_list_from_video_url():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxxxxx&index=5"
    result = strip_playlist_context(url)
    assert "list=" not in result
    assert "index=" not in result
    assert "v=dQw4w9WgXcQ" in result


def test_strip_playlist_context_keeps_pure_playlist_url_unchanged():
    url = "https://www.youtube.com/playlist?list=PLxxxxxx"
    assert strip_playlist_context(url) == url


def test_strip_playlist_context_untouched_when_no_list_param():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert strip_playlist_context(url) == url


def test_strip_playlist_context_handles_shorts_url():
    result = strip_playlist_context("https://www.youtube.com/shorts/abc123?list=PLxxx")
    assert "list=" not in result


def test_strip_playlist_context_handles_youtu_be_short_link():
    result = strip_playlist_context("https://youtu.be/dQw4w9WgXcQ?list=PLxxxxxx&index=5")
    assert "list=" not in result
    assert "index=" not in result
    assert "dQw4w9WgXcQ" in result


def test_strip_playlist_context_youtu_be_without_list_unchanged():
    url = "https://youtu.be/dQw4w9WgXcQ"
    assert strip_playlist_context(url) == url


def test_strip_playlist_context_youtu_be_root_without_video_id_unchanged():
    url = "https://youtu.be/?list=PLxxxxxx"
    assert strip_playlist_context(url) == url


def test_strip_playlist_context_does_not_match_lookalike_domain():
    url = "https://notyoutu.be/ID?list=PLxxxxxx"
    assert strip_playlist_context(url) == url


def test_detect_rejects_non_youtube_url():
    with pytest.raises(DetectionError):
        detect("https://www.tiktok.com/@u/video/123")


def test_detect_calls_extract_info_with_stripped_url(monkeypatch):
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
    assert content.platform == "YouTube"
    assert content.content_type == "VIDEO"
    assert "list=" not in content.url


def test_detect_audio_stream_classified_as_audio(monkeypatch):
    class FakeYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=False):
            return {"extractor_key": "Youtube", "title": "Lagu", "vcodec": "none", "acodec": "mp4a", "duration": 200}

    monkeypatch.setattr(detector.yt_dlp, "YoutubeDL", FakeYDL)

    content = detect("https://www.youtube.com/watch?v=abc")
    assert content.content_type == "AUDIO"


def test_detect_maps_private_error(monkeypatch):
    class FakeYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=False):
            raise detector.yt_dlp.utils.DownloadError("Private video, sign in required")

    monkeypatch.setattr(detector.yt_dlp, "YoutubeDL", FakeYDL)

    with pytest.raises(DetectionError) as exc_info:
        detect("https://www.youtube.com/watch?v=abc")
    assert "private" in str(exc_info.value).lower()


def test_detect_maps_tiktok_style_challenge_to_blocked(monkeypatch):
    class FakeYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=False):
            raise detector.yt_dlp.utils.DownloadError(
                "Unexpected response from webpage request; Confirm you are on the latest version"
            )

    monkeypatch.setattr(detector.yt_dlp, "YoutubeDL", FakeYDL)

    with pytest.raises(DetectionError) as exc_info:
        detect("https://www.youtube.com/watch?v=abc")
    assert "blocking" in str(exc_info.value).lower()


def test_detect_retries_without_cookies_when_cookie_copy_fails(monkeypatch):
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


def test_detect_uses_cookiefile_when_given(monkeypatch, tmp_path):
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
    detect("https://youtube.com/watch?v=abc", cookies_file=str(cookie_file))
    assert seen.get("cookiefile") == str(cookie_file)
    assert "cookiesfrombrowser" not in seen
