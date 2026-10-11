"""
test_lumenfetch.py
Unit test untuk fungsi-fungsi inti (sanitasi nama file, format ukuran,
naming template, resolve duplikat, config, validasi URL, dll).
"""


import pytest

from core.detector import is_valid_url

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


