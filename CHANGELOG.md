# Changelog

## v2.1.2

This release fixes repeated download failures (0 bytes, then an error) that happened even for public videos.

### New features

- **Doctor JavaScript check.** `lumenfetch --doctor` now also checks for a JavaScript runtime (Deno/Node), required for YouTube signature challenges.

### Improvements

- **Removed the forced `player_client` override.** It triggered YouTube's SABR-only experiment (5 formats served instead of about 46). yt-dlp's maintained defaults are used now.
- **Transient format errors retried.** Format errors now get backoff like connection errors.
- **Post-processing crashes no longer fail an otherwise good download.** A crash (for example thumbnail embed) keeps the video with a warning.
- **Parallel batch downloads of duplicate titles get unique filenames** instead of corrupting each other.

### Bug fixes

- **0-byte results now fail loudly with cleanup.** Empty results are no longer reported as success or left in the folder.
- **Batch files with a BOM prefix are no longer skipped silently**, and per-URL batch failures are now reported.

## v2.1.1

This release makes English the default display language and refreshes the PyPI page.

### New features

- **`lumenfetch doctor`.** Diagnoses your setup in seconds, each check with a specific fix hint.
- **Self-update notice.** Tells you when a newer lumenfetch is on PyPI.
- **`--ui-lang en|id`.** Display language via flag, `LUMENFETCH_LANG`, or the remembered `ui_lang` setting.

### Breaking changes

- **Default display language is now English.** Run `lumenfetch --ui-lang id` once to keep Bahasa Indonesia; the choice is remembered afterwards.

## v2.1.0

This release adds a setup doctor, a self-update notice, and SponsorBlock support.

### New features

- **`lumenfetch doctor`.** Diagnoses your setup in seconds: Python, ffmpeg, `curl_cffi`, yt-dlp version, lumenfetch version, YouTube reachability, browser-cookie readability, and config writability, each with a specific fix hint.
- **Self-update notice.** Tells you when a newer lumenfetch is on PyPI (`pip install --upgrade lumenfetch`), next to the existing yt-dlp notice.
- **`--sponsorblock`.** Skip SponsorBlock segments, e.g. `--sponsorblock sponsor intro outro`.
- **`--write-info-json`.** Save video metadata as `.info.json` next to the file.
- **Auto `.m3u`.** Audio playlists (`--playlist all`) now also write an `.m3u` file.

### Improvements

- **Parallel-safe downloads.** Two batch workers for the same title no longer overwrite each other's file (atomic name reservation, verified live 2/2).
- **Loud batch failures.** Batch mode now prints which URL failed and why instead of failing silently (also handles BOM-prefixed files from PowerShell).
- **Quiet terminal.** Raw yt-dlp `ERROR:` noise is redirected to `lumenfetch.log`; the terminal only shows friendly messages.
- **New `core/cli.py` and `core/doctor.py` modules.** Argument parsing and diagnostics were split out of `main.py`; `main.py` is slimmed down.
- **Coverage gate and trusted publishing.** CI enforces an 80% coverage gate and publishes to PyPI without a token.
- **Windows exe.** `lumenfetch.exe` is attached to the release, no Python needed.

### Bug fixes

- **Batch URLs with a BOM prefix are no longer silently skipped.**
- **Batch mode no longer swallows per-URL errors** (they are printed with the failing URL).
- **Parallel downloads of duplicate titles no longer corrupt each other's output.**

## v2.0.0

Lumenfetch is now a focused YouTube downloader: MP4 video and MP3 audio, nothing else.

### New features

- **MP4 video.** Quality Best/1080p/720p/480p/360p/Worst with auto-embedded thumbnail.
- **MP3 audio.** Bitrate Best/320kbps/192kbps/128kbps.
- **English and Indonesian CLI.** `--ui-lang en|id`; menus, prompts, tables, error messages, and `--help` are fully translatable. English is the default, remembered afterwards. Also via `LUMENFETCH_LANG` or the `ui_lang` config value.
- **Bilingual documentation.** `README.md` and `CONTRIBUTING.md` in English, with Indonesian versions in `README.id.md` and `CONTRIBUTING.id.md`.

### Breaking changes

- **YouTube-only.** Only `youtube.com`, `youtu.be`, and `music.youtube.com` links are accepted. Other platforms are rejected with a clear message instead of a misleading error.
- **Removed dependencies.** `instaloader` and `browser-cookie3` are gone; install is lighter. Browser/file cookies for YouTube still work.
- **Output filename template.** Filenames follow `%(platform)s_%(title)s_%(year)s`, e.g. `YouTube_Lofi-Hip-Hop-Radio_2026.mp4`.

### Improvements

- **New `core/i18n.py` module.** A pure dictionary of display text (en/id); all user-facing text goes through `t("key")`.
- **New `core/errors.py` taxonomy.** Every yt-dlp failure maps to a specific kind (bot-check, cookies, rate-limit, removed, etc.) with an actionable message, including automatic retry without cookies when the cookie database is locked.
- **`curl_cffi` is now a required dependency** so YouTube bot-checks pass.
- **User config moved** to the OS config dir (`%APPDATA%` on Windows, `~/.config` on Linux, `~/Library/Application Support` on macOS), with one-time migration from the old location.
