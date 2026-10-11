"""
test_lumenfetch.py
Unit test untuk fungsi-fungsi inti (sanitasi nama file, format ukuran,
naming template, resolve duplikat, config, validasi URL, dll).
"""

from pathlib import Path
from unittest import mock

import pytest

from core import instagram_fallback, utils

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
# instagram_fallback._load_cookies_from_browser / detect_photo cookies_browser
# ---------------------------------------------------------------------------

def test_load_cookies_from_browser_filters_instagram_domain_only(monkeypatch):
    """
    Regresi bug: fitur "Cookies dari Browser" di menu settings DIAM-DIAM
    TIDAK BERLAKU buat jalur foto Instagram (satu-satunya alasan fallback
    instaloader ini ada) - README & menu settings sendiri bilang fitur ini
    "terutama buat Instagram", tapi post foto private tetap gagal walau
    cookies aktif. Sekarang cookies beneran dimuat ke session instaloader,
    dan cuma cookies domain instagram yang dipakai (bukan semua cookies
    browser, mis. dari Facebook/domain lain).
    """

    class FakeCookie:
        def __init__(self, domain, name, value):
            self.domain = domain
            self.name = name
            self.value = value

    fake_cookies = [
        FakeCookie(".instagram.com", "sessionid", "abc123"),
        FakeCookie(".instagram.com", "csrftoken", "xyz789"),
        FakeCookie(".facebook.com", "other_cookie", "harus-terfilter"),
    ]

    fake_loader = mock.MagicMock()
    fake_module = mock.MagicMock(chrome=lambda: fake_cookies)
    monkeypatch.setitem(__import__("sys").modules, "browser_cookie3", fake_module)

    instagram_fallback._load_cookies_from_browser(fake_loader, "chrome")

    cookies_passed = fake_loader.context.update_cookies.call_args[0][0]
    assert cookies_passed == {"sessionid": "abc123", "csrftoken": "xyz789"}


def test_load_cookies_from_browser_fails_safely_when_library_missing(monkeypatch):
    """browser_cookie3 belum terinstall -> gagal diam-diam, bukan crash (fitur cookies itu opsional)."""
    import builtins

    fake_loader = mock.MagicMock()
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "browser_cookie3":
            raise ImportError("no module named browser_cookie3")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    instagram_fallback._load_cookies_from_browser(fake_loader, "chrome")  # TIDAK BOLEH raise

    assert not fake_loader.context.update_cookies.called


def test_load_cookies_from_browser_fails_safely_when_browser_read_fails(monkeypatch):
    """Browser belum pernah login Instagram / gagal dibaca -> gagal diam-diam, bukan crash."""

    def failing_chrome():
        raise Exception("gagal baca cookies chrome")

    fake_loader = mock.MagicMock()
    fake_module = mock.MagicMock(chrome=failing_chrome)
    monkeypatch.setitem(__import__("sys").modules, "browser_cookie3", fake_module)

    instagram_fallback._load_cookies_from_browser(fake_loader, "chrome")  # TIDAK BOLEH raise

    assert not fake_loader.context.update_cookies.called


def test_load_cookies_from_browser_skips_unsupported_browser(monkeypatch):
    fake_loader = mock.MagicMock()
    fake_module = mock.MagicMock(spec=["chrome"])  # cuma punya atribut "chrome"
    monkeypatch.setitem(__import__("sys").modules, "browser_cookie3", fake_module)

    instagram_fallback._load_cookies_from_browser(fake_loader, "browser-aneh-tidak-didukung")

    assert not fake_loader.context.update_cookies.called


def test_load_cookies_from_browser_calls_test_login(monkeypatch):
    """
    Regresi: update_cookies() doang TIDAK CUKUP - instaloader.context.is_logged_in
    didefinisikan sebagai bool(self.username), yang cuma keisi lewat
    test_login(). Tanpa manggil ini, cookies valid tetap bikin is_logged_in
    False selamanya, dan instaloader punya pengecekan is_logged_in di jalur
    redirect handling yang bisa langsung raise LoginRequiredException kalau
    Instagram redirect ke halaman login - persis kondisi gagal yang fitur
    cookies ini coba selesaikan.
    """
    fake_loader = mock.MagicMock()
    fake_loader.context.test_login.return_value = "username_dari_cookies"

    fake_cookies = [type("C", (), {"domain": ".instagram.com", "name": "sessionid", "value": "abc"})()]
    fake_module = mock.MagicMock(chrome=lambda: fake_cookies)
    monkeypatch.setitem(__import__("sys").modules, "browser_cookie3", fake_module)

    instagram_fallback._load_cookies_from_browser(fake_loader, "chrome")

    fake_loader.context.test_login.assert_called_once()
    assert fake_loader.context.username == "username_dari_cookies"


def test_load_cookies_from_browser_sets_is_logged_in_true_with_real_instaloader():
    """
    Test end-to-end pakai objek instaloader.InstaloaderContext ASLI (bukan
    MagicMock) - biar bug regresinya kena tangkap beneran kalau kejadian
    lagi. MagicMock otomatis bikin semua atribut "ada" jadi truthy, jadi
    gak bakal ketauan kalau context.username lupa di-set - tes ini pakai
    context yang beneran punya property is_logged_in = bool(self.username).
    """
    import instaloader

    loader = instaloader.Instaloader(quiet=True)
    assert loader.context.is_logged_in is False  # kondisi awal sebelum cookies dimuat

    fake_cookies = [type("C", (), {"domain": ".instagram.com", "name": "sessionid", "value": "abc"})()]

    with mock.patch.dict("sys.modules", {"browser_cookie3": mock.MagicMock(chrome=lambda: fake_cookies)}):
        with mock.patch.object(loader.context, "test_login", return_value="username_asli"):
            instagram_fallback._load_cookies_from_browser(loader, "chrome")

    assert loader.context.username == "username_asli"
    assert loader.context.is_logged_in is True


def test_load_cookies_from_browser_test_login_failure_does_not_crash(monkeypatch):
    """test_login() gagal (mis. rate-limit/connection error sesaat) tidak boleh menggagalkan seluruh proses - cookies tetap dipakai apa adanya."""
    fake_loader = mock.MagicMock()
    fake_loader.context.test_login.side_effect = Exception("rate limited")

    fake_cookies = [type("C", (), {"domain": ".instagram.com", "name": "sessionid", "value": "abc"})()]
    fake_module = mock.MagicMock(chrome=lambda: fake_cookies)
    monkeypatch.setitem(__import__("sys").modules, "browser_cookie3", fake_module)

    instagram_fallback._load_cookies_from_browser(fake_loader, "chrome")  # TIDAK BOLEH raise

    fake_loader.context.update_cookies.assert_called_once()  # cookies tetap ke-suntik meski test_login gagal


def test_detect_photo_passes_cookies_browser_to_loader(monkeypatch):
    """Test integrasi: detect_photo() harus benar-benar memanggil _load_cookies_from_browser saat cookies_browser diset."""

    class FakePost:
        typename = "GraphImage"
        caption = "Judul"
        owner_username = "user"
        is_video = False
        url = "https://cdn/foto.jpg"

    monkeypatch.setattr(instagram_fallback.instaloader, "Instaloader", lambda **kwargs: mock.MagicMock())
    monkeypatch.setattr(instagram_fallback.instaloader.Post, "from_shortcode", lambda ctx, sc: FakePost())

    captured = {}

    def fake_load_cookies(loader, browser):
        captured["browser"] = browser

    monkeypatch.setattr(instagram_fallback, "_load_cookies_from_browser", fake_load_cookies)

    instagram_fallback.detect_photo("https://www.instagram.com/p/ABC123/", cookies_browser="chrome")

    assert captured.get("browser") == "chrome"


def test_detect_photo_skips_cookie_loading_when_none(monkeypatch):
    class FakePost:
        typename = "GraphImage"
        caption = "Judul"
        owner_username = "user"
        is_video = False
        url = "https://cdn/foto.jpg"

    monkeypatch.setattr(instagram_fallback.instaloader, "Instaloader", lambda **kwargs: mock.MagicMock())
    monkeypatch.setattr(instagram_fallback.instaloader.Post, "from_shortcode", lambda ctx, sc: FakePost())

    called = []
    monkeypatch.setattr(instagram_fallback, "_load_cookies_from_browser", lambda loader, browser: called.append(browser))

    instagram_fallback.detect_photo("https://www.instagram.com/p/ABC123/", cookies_browser=None)
    instagram_fallback.detect_photo("https://www.instagram.com/p/ABC123/", cookies_browser="none")

    assert called == []


def test_detector_passes_cookies_browser_to_instagram_fallback(monkeypatch):
    """
    Test integrasi end-to-end: detector.detect() harus benar-benar meneruskan
    cookies_browser sampai ke instagram_fallback.detect_photo(), bukan
    hilang di tengah jalan (bug asli yang dilaporkan).
    """
    from core import detector

    class FakeYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=False):
            raise detector.yt_dlp.utils.DownloadError("There is no video in this post")

    monkeypatch.setattr(detector.yt_dlp, "YoutubeDL", FakeYDL)

    captured = {}

    def fake_detect_photo(url, cookies_browser=None):
        captured["cookies_browser"] = cookies_browser
        return mock.MagicMock()

    monkeypatch.setattr(instagram_fallback, "detect_photo", fake_detect_photo)

    detector.detect("https://www.instagram.com/p/ABC123/", cookies_browser="firefox")

    assert captured.get("cookies_browser") == "firefox"


# ---------------------------------------------------------------------------
# instagram_fallback.detect_photo - carousel campuran (foto+video)
# ---------------------------------------------------------------------------

def test_detect_photo_includes_videos_in_mixed_carousel(monkeypatch):
    """
    Regresi bug: carousel Instagram yang isinya CAMPURAN foto+video dulu
    diam-diam nge-skip semua node video (`if not node.is_video`), user cuma
    dapet foto-fotonya doang tanpa pemberitahuan apa pun kalau ada video
    yang kelewat. Sekarang video-nya ikut disertakan (pakai video_url,
    bukan display_url yang cuma thumbnail).
    """

    class FakeSidecarNode:
        def __init__(self, is_video, url):
            self.is_video = is_video
            self.display_url = None if is_video else url
            self.video_url = url if is_video else None

    class FakePost:
        typename = "GraphSidecar"
        caption = "Liburan seru"
        owner_username = "testuser"

        def get_sidecar_nodes(self):
            return [
                FakeSidecarNode(False, "https://cdn/foto1.jpg"),
                FakeSidecarNode(True, "https://cdn/video1.mp4"),
                FakeSidecarNode(False, "https://cdn/foto2.jpg"),
            ]

    monkeypatch.setattr(instagram_fallback.instaloader, "Instaloader", lambda **kwargs: mock.MagicMock())
    monkeypatch.setattr(instagram_fallback.instaloader.Post, "from_shortcode", lambda ctx, sc: FakePost())

    content = instagram_fallback.detect_photo("https://www.instagram.com/p/ABC123/")

    assert len(content.entries) == 3
    assert content.raw_info["photo_count"] == 2
    assert content.raw_info["video_count"] == 1

    video_entries = [e for e in content.entries if e["is_video"]]
    assert len(video_entries) == 1
    assert video_entries[0]["url"] == "https://cdn/video1.mp4"  # video_url, bukan display_url


def test_detect_photo_pure_image_carousel_unaffected(monkeypatch):
    """Carousel foto-doang (tanpa video) tidak boleh berubah behavior-nya."""

    class FakeSidecarNode:
        def __init__(self, url):
            self.is_video = False
            self.display_url = url
            self.video_url = None

    class FakePost:
        typename = "GraphSidecar"
        caption = "Galeri foto"
        owner_username = "testuser"

        def get_sidecar_nodes(self):
            return [FakeSidecarNode("https://cdn/foto1.jpg"), FakeSidecarNode("https://cdn/foto2.jpg")]

    monkeypatch.setattr(instagram_fallback.instaloader, "Instaloader", lambda **kwargs: mock.MagicMock())
    monkeypatch.setattr(instagram_fallback.instaloader.Post, "from_shortcode", lambda ctx, sc: FakePost())

    content = instagram_fallback.detect_photo("https://www.instagram.com/p/XYZ789/")

    assert len(content.entries) == 2
    assert content.raw_info["photo_count"] == 2
    assert content.raw_info["video_count"] == 0
    assert all(not e["is_video"] for e in content.entries)


def test_download_photos_saves_video_entry_as_mp4_without_conversion(tmp_path, monkeypatch):
    """
    Regresi: entry video di carousel campuran harus disimpan APA ADANYA
    sebagai .mp4, TIDAK dipaksa lewat convert_image() (yang cuma buat
    gambar) - convert_image() memakai ffmpeg buat konversi antar-format
    gambar, bukan buat video.
    """
    convert_image_calls = []

    def fake_convert_image(src, target_ext):
        convert_image_calls.append(src.name)
        return src

    def fake_urlretrieve(url, dest):
        Path(dest).write_bytes(b"fake-content")

    monkeypatch.setattr(instagram_fallback, "convert_image", fake_convert_image)
    monkeypatch.setattr(instagram_fallback.urllib.request, "urlretrieve", fake_urlretrieve)

    class FakeContent:
        platform = "Instagram"
        title = "Liburan seru"
        entries = [
            {"url": "https://cdn/foto1.jpg", "is_video": False},
            {"url": "https://cdn/video1.mp4", "is_video": True},
        ]

    result = instagram_fallback.download_photos(
        FakeContent(), None, "png", tmp_path, "%(platform)s_%(title)s_%(year)s"
    )

    assert result.success_count == 2
    video_paths = [p for p in result.paths if p.suffix == ".mp4"]
    photo_paths = [p for p in result.paths if p.suffix != ".mp4"]
    assert len(video_paths) == 1
    assert len(photo_paths) == 1
    # convert_image() cuma boleh dipanggil buat entry FOTO, bukan video
    assert len(convert_image_calls) == 1


