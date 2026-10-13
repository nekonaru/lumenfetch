"""doctor.py - Diagnose setup (ffmpeg, deps, cookies, network). No downloads."""

from __future__ import annotations

import sys
import urllib.request
from dataclasses import dataclass

from core.constants import VERSION
from core.i18n import t

YOUTUBE_PING_URL = "https://www.youtube.com/generate_204"
PING_TIMEOUT_SECONDS = 8


@dataclass
class DoctorCheck:
    name: str
    ok: bool
    detail: str = ""
    hint: str = ""


def run_all(config: dict | None = None) -> list[DoctorCheck]:
    """Run every check, fastest first. Never raises."""
    checks: list[DoctorCheck] = [
        _check_python(),
        _check_ffmpeg(),
        _check_curl_cffi(),
        _check_yt_dlp(),
        _check_self(),
        _check_network(),
    ]
    checks.append(_check_cookies_browser((config or {}).get("cookies_browser")))
    checks.append(_check_config_writable())
    return checks


def _check_python() -> DoctorCheck:
    ok = sys.version_info >= (3, 9)
    return DoctorCheck(
        name=t("doctor.python"),
        ok=ok,
        detail=".".join(map(str, sys.version_info[:3])),
        hint="" if ok else t("doctor.python_hint"),
    )


def _check_ffmpeg() -> DoctorCheck:
    from core import ffmpeg as _ffmpeg  # noqa: PLC0415

    found = _ffmpeg.find_system_ffmpeg()
    if found:
        return DoctorCheck(name=t("doctor.ffmpeg"), ok=True, detail=found)
    try:
        import static_ffmpeg  # noqa: PLC0415

        _ = static_ffmpeg
        return DoctorCheck(name=t("doctor.ffmpeg"), ok=True, detail=t("doctor.ffmpeg_bundled"))
    except ImportError:
        return DoctorCheck(name=t("doctor.ffmpeg"), ok=False, detail="-", hint=t("doctor.ffmpeg_hint"))


def _check_curl_cffi() -> DoctorCheck:
    import importlib.util

    ok = importlib.util.find_spec("curl_cffi") is not None
    return DoctorCheck(
        name=t("doctor.curl"),
        ok=ok,
        detail=t("doctor.installed") if ok else t("doctor.missing"),
        hint="" if ok else t("doctor.curl_hint"),
    )


def _check_yt_dlp() -> DoctorCheck:
    from core import update_checker  # noqa: PLC0415

    try:
        installed = update_checker.get_installed_version()
    except Exception:  # noqa: BLE001
        return DoctorCheck(name=t("doctor.ytdlp"), ok=False, detail="-", hint=t("doctor.ytdlp_hint"))
    try:
        has_update, _, latest = update_checker.check_for_update()
    except Exception:  # noqa: BLE001
        return DoctorCheck(name=t("doctor.ytdlp"), ok=True, detail=installed)
    if has_update and latest:
        return DoctorCheck(
            name=t("doctor.ytdlp"), ok=True, detail=installed, hint=t("doctor.ytdlp_update", latest=latest)
        )
    return DoctorCheck(name=t("doctor.ytdlp"), ok=True, detail=installed)


def _check_self() -> DoctorCheck:
    from core import update_checker  # noqa: PLC0415

    try:
        has_update, installed, latest = update_checker.check_self_update()
    except Exception:  # noqa: BLE001
        return DoctorCheck(name=t("doctor.self"), ok=True, detail=VERSION)
    if has_update and latest:
        return DoctorCheck(
            name=t("doctor.self"), ok=True, detail=installed, hint=t("doctor.self_update", latest=latest)
        )
    return DoctorCheck(name=t("doctor.self"), ok=True, detail=installed)


def _check_network() -> DoctorCheck:
    try:
        req = urllib.request.Request(YOUTUBE_PING_URL, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=PING_TIMEOUT_SECONDS) as resp:  # noqa: S310
            ok = resp.status in (200, 204)
            return DoctorCheck(
                name=t("doctor.network"),
                ok=ok,
                detail=f"HTTP {resp.status}" if ok else "-",
                hint="" if ok else t("doctor.network_hint"),
            )
    except Exception:  # noqa: BLE001
        return DoctorCheck(name=t("doctor.network"), ok=False, detail="-", hint=t("doctor.network_hint"))


def _check_cookies_browser(browser: str | None) -> DoctorCheck:
    from core.utils import build_cookies_from_browser  # noqa: PLC0415

    if not build_cookies_from_browser(browser):
        return DoctorCheck(name=t("doctor.cookies"), ok=True, detail=t("doctor.cookies_off"))
    try:
        from yt_dlp.cookies import extract_cookies_from_browser  # noqa: PLC0415

        jar = extract_cookies_from_browser(browser, logger=_SilentLogger())
        n = len(getattr(jar, "_cookies", {}))
        return DoctorCheck(name=t("doctor.cookies"), ok=True, detail=f"{browser} ({n} domains)")
    except Exception as e:  # noqa: BLE001
        return DoctorCheck(name=t("doctor.cookies"), ok=False, detail=str(e)[:80], hint=t("doctor.cookies_hint"))


class _SilentLogger:
    def debug(self, *a, **k):
        pass

    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass


def _check_config_writable() -> DoctorCheck:
    from core.utils import _resolve_config_path  # noqa: PLC0415

    try:
        path = _resolve_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        probe = path.parent / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return DoctorCheck(name=t("doctor.config"), ok=True, detail=str(path))
    except OSError as e:
        return DoctorCheck(name=t("doctor.config"), ok=False, detail=str(e)[:80], hint=t("doctor.config_hint"))


def show(checks: list[DoctorCheck]) -> bool:
    """Print a rich table. Return True if everything passed."""
    from rich.console import Console  # noqa: PLC0415
    from rich.table import Table  # noqa: PLC0415

    console = Console()
    table = Table(title=t("doctor.title"))
    table.add_column(t("doctor.col_check"))
    table.add_column(t("doctor.col_result"))
    table.add_column(t("doctor.col_detail"))
    table.add_column(t("doctor.col_hint"))

    all_ok = True
    for c in checks:
        if not c.ok:
            all_ok = False
        table.add_row(c.name, "✅ PASS" if c.ok else "❌ FAIL", c.detail, c.hint)
    console.print(table)
    return all_ok


__all__ = ["DoctorCheck", "run_all", "show"]
