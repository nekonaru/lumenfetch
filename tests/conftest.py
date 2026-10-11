"""conftest.py - Fixture global test.

Semua sleep (retry backoff) di-nonaktifkan saat test agar suite cepat.
Logika backoff sendiri diuji murni via backoff_delay() tanpa tidur.
"""

from __future__ import annotations

import time as _time

import pytest

SAMPLE_VIDEO_FORMATS = [
    {"vcodec": "avc1", "acodec": "none", "height": 1080, "ext": "mp4", "filesize": 150_000_000, "tbr": 4500},
    {"vcodec": "avc1", "acodec": "none", "height": 720, "ext": "mp4", "filesize": 80_000_000, "tbr": 2400},
    {"vcodec": "avc1", "acodec": "none", "height": 480, "ext": "mp4", "filesize": 40_000_000, "tbr": 1200},
    {"vcodec": "none", "acodec": "mp4a", "ext": "m4a", "filesize": 5_000_000, "abr": 128},
]


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(_time, "sleep", lambda s: None)
    yield
