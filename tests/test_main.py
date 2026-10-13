"""
test_lumenfetch.py
Unit test untuk fungsi-fungsi inti (sanitasi nama file, format ukuran,
naming template, resolve duplikat, config, validasi URL, dll).
"""

from pathlib import Path

import main
from core import utils
from core.options import DownloadChoice

# ---------------------------------------------------------------------------
# main.main() - startup tidak boleh crash kalau static_ffmpeg gagal
# ---------------------------------------------------------------------------

def test_main_does_not_crash_when_static_ffmpeg_fails(monkeypatch):
    """
    Regresi bug KRITIS: static_ffmpeg.add_paths() butuh internet buat
    download binary ffmpeg di percobaan PERTAMA di komputer itu. Kalau
    gagal (offline, GitHub diblokir firewall kantor/kampus, dll) dan
    pemanggilannya tidak dibungkus try/except, exception itu nembus sampai
    ke __main__ (yang cuma nangkep KeyboardInterrupt) - user lihat
    traceback Python mentah dan APLIKASI SAMA SEKALI TIDAK BISA DIBUKA,
    padahal banyak fitur (deteksi konten, download gambar tunggal, dll)
    sama sekali tidak butuh ffmpeg.
    """
    monkeypatch.setattr(
        main.static_ffmpeg, "add_paths", lambda: (_ for _ in ()).throw(RuntimeError("gagal download ffmpeg"))
    )
    monkeypatch.setattr(main.update_checker, "check_for_update", lambda: (False, "2026.1.1", None))
    monkeypatch.setattr(main.update_checker, "check_self_update", lambda: (False, "2.0.0", None))
    monkeypatch.setattr(main.utils, "load_config", lambda: utils.get_default_config())
    monkeypatch.setattr(main.options, "show_header", lambda version: None)
    # Langsung "q" biar main() keluar dari loop tanpa perlu interaksi lain
    monkeypatch.setattr(main, "try_clipboard_url", lambda config, last: (None, last))
    monkeypatch.setattr(main.Prompt, "ask", lambda *a, **k: "q")

    main.main()  # TIDAK BOLEH raise apa pun


# ---------------------------------------------------------------------------
# main.try_clipboard_url
# ---------------------------------------------------------------------------

def test_try_clipboard_url_disabled_by_auto_paste_off(monkeypatch):
    monkeypatch.setattr(main.pyperclip, "paste", lambda: "https://youtube.com/watch?v=abc")
    url, last = main.try_clipboard_url({"auto_paste": False}, last_prompted=None)
    assert url is None
    assert last is None


def test_try_clipboard_url_ignores_invalid_clipboard_content(monkeypatch):
    monkeypatch.setattr(main.pyperclip, "paste", lambda: "bukan url sama sekali")
    url, last = main.try_clipboard_url({"auto_paste": True}, last_prompted=None)
    assert url is None
    assert last is None


def test_try_clipboard_url_returns_url_when_accepted(monkeypatch):
    monkeypatch.setattr(main.pyperclip, "paste", lambda: "https://youtube.com/watch?v=abc")
    monkeypatch.setattr(main.Prompt, "ask", lambda *a, **k: "y")

    url, last = main.try_clipboard_url({"auto_paste": True}, last_prompted=None)

    assert url == "https://youtube.com/watch?v=abc"
    assert last == "https://youtube.com/watch?v=abc"


def test_try_clipboard_url_tracks_declined_content(monkeypatch):
    monkeypatch.setattr(main.pyperclip, "paste", lambda: "https://youtube.com/watch?v=abc")
    monkeypatch.setattr(main.Prompt, "ask", lambda *a, **k: "n")

    url, last = main.try_clipboard_url({"auto_paste": True}, last_prompted=None)

    assert url is None
    assert last == "https://youtube.com/watch?v=abc"  # tetap dicatat meski ditolak


def test_try_clipboard_url_does_not_reask_same_content(monkeypatch):
    """
    Regresi UX: dulu clipboard yang isinya belum berubah ditawarkan LAGI
    setiap loop, jadi user harus jawab 'n' berulang kali padahal isinya
    sama persis dengan yang baru saja ditolak/sudah dipakai.
    """
    prompt_call_count = [0]

    def fake_prompt_ask(*args, **kwargs):
        prompt_call_count[0] += 1
        return "n"

    monkeypatch.setattr(main.pyperclip, "paste", lambda: "https://youtube.com/watch?v=abc")
    monkeypatch.setattr(main.Prompt, "ask", fake_prompt_ask)

    config = {"auto_paste": True}
    url1, last1 = main.try_clipboard_url(config, last_prompted=None)
    url2, last2 = main.try_clipboard_url(config, last_prompted=last1)

    assert prompt_call_count[0] == 1  # cuma ditanya SEKALI, bukan dua kali
    assert url1 is None and url2 is None
    assert last1 == last2 == "https://youtube.com/watch?v=abc"


def test_try_clipboard_url_reasks_when_content_changes(monkeypatch):
    monkeypatch.setattr(main.pyperclip, "paste", lambda: "https://youtube.com/watch?v=xyz")
    monkeypatch.setattr(main.Prompt, "ask", lambda *a, **k: "y")

    # last_prompted dari URL SEBELUMNYA yang beda -> harus tetap ditanya lagi
    url, last = main.try_clipboard_url({"auto_paste": True}, last_prompted="https://youtube.com/watch?v=abc")

    assert url == "https://youtube.com/watch?v=xyz"


# ---------------------------------------------------------------------------
# main.handle_settings - ganti folder download
# ---------------------------------------------------------------------------

def test_handle_settings_expands_tilde_in_folder_path(monkeypatch, tmp_path):
    """
    User ketik path pakai "~" (mis. "~/Documents/MyDownloads") berharap itu
    ke-resolve ke home folder-nya, bukan diperlakukan sebagai nama folder
    relatif literal bernama "~" di dalam folder project.
    """
    menu_choices = iter(["1", "7"])
    monkeypatch.setattr(main.options, "show_settings_menu", lambda config: next(menu_choices))
    monkeypatch.setattr(main.Prompt, "ask", lambda *a, **k: "~/Documents/MyDownloads")
    monkeypatch.setattr(main.utils, "save_config", lambda config: None)

    config = utils.get_default_config()
    result = main.handle_settings(config)

    assert result["download_folder"] == str(Path.home() / "Documents" / "MyDownloads")
    assert "~" not in result["download_folder"]


def test_handle_settings_accepts_absolute_path_unchanged(monkeypatch, tmp_path):
    menu_choices = iter(["1", "7"])
    monkeypatch.setattr(main.options, "show_settings_menu", lambda config: next(menu_choices))
    monkeypatch.setattr(main.Prompt, "ask", lambda *a, **k: str(tmp_path / "CustomFolder"))
    monkeypatch.setattr(main.utils, "save_config", lambda config: None)

    config = utils.get_default_config()
    result = main.handle_settings(config)

    assert result["download_folder"] == str(tmp_path / "CustomFolder")


# ---------------------------------------------------------------------------
# main.process_url - warning transparan buat URL playlist murni
# ---------------------------------------------------------------------------

def test_process_url_warns_user_about_pure_playlist(tmp_path, monkeypatch):
    """
    User berhak tahu kalau URL yang mereka paste ternyata playlist murni dan
    cuma video pertama yang bakal didownload - daripada diam-diam cuma
    ngasih 1 dari sekian video yang mereka kira bakal didownload semua.
    """
    from core.detector import DetectedContent

    playlist_content = DetectedContent(
        url="https://www.youtube.com/playlist?list=PLxxxxxx",
        title="Judul Playlist",
        content_type="VIDEO",
        duration=None,
        entries=[{"url": "v1"}, {"url": "v2"}, {"url": "v3"}],
        raw_info={},
    )

    monkeypatch.setattr(main, "detect", lambda url, cookies_browser=None, **kwargs: playlist_content)
    monkeypatch.setattr(main.options, "show_content_panel", lambda content: None)
    monkeypatch.setattr(
        main.options, "resolve_choice", lambda content, avg_speed_bps=None: DownloadChoice(output_kind="video", fmt="mp4")
    )
    monkeypatch.setattr(main.options, "confirm_filename", lambda filename: False)  # keluar lebih awal, cukup cek warning

    printed = []
    monkeypatch.setattr(main.console, "print", lambda *a, **k: printed.append(str(a[0]) if a else ""))

    main.process_url("https://www.youtube.com/playlist?list=PLxxxxxx", utils.get_default_config())

    warning_shown = any("playlist" in line.lower() and "3 video" in line for line in printed)
    assert warning_shown, f"Warning playlist tidak muncul. Yang ke-print: {printed}"


def test_process_url_no_warning_for_single_video(tmp_path, monkeypatch):
    from core.detector import DetectedContent

    single_content = DetectedContent(
        url="https://www.youtube.com/watch?v=abc",
        title="Judul Video",
        content_type="VIDEO",
        duration=120,
        entries=[],
        raw_info={},
    )

    monkeypatch.setattr(main, "detect", lambda url, cookies_browser=None, **kwargs: single_content)
    monkeypatch.setattr(main.options, "show_content_panel", lambda content: None)
    monkeypatch.setattr(
        main.options, "resolve_choice", lambda content, avg_speed_bps=None: DownloadChoice(output_kind="video", fmt="mp4")
    )
    monkeypatch.setattr(main.options, "confirm_filename", lambda filename: False)

    printed = []
    monkeypatch.setattr(main.console, "print", lambda *a, **k: printed.append(str(a[0]) if a else ""))

    main.process_url("https://www.youtube.com/watch?v=abc", utils.get_default_config())

    warning_shown = any("playlist berisi" in line.lower() for line in printed)
    assert not warning_shown


