<div align="center">

# 📥 Lumenfetch: YouTube Downloader

**Save any YouTube video as `.mp4` or `.mp3`, with quality picker, subtitles, and playlists, right from your terminal.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/lumenfetch?style=flat-square&color=blue)](https://pypi.org/project/lumenfetch/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square)](https://github.com/nekonaru/lumenfetch/releases)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)](https://github.com/nekonaru/lumenfetch)
[![Tests](https://github.com/nekonaru/lumenfetch/actions/workflows/tests.yml/badge.svg)](https://github.com/nekonaru/lumenfetch/actions)

</div>

**English** | [Bahasa Indonesia](README.id.md)

## ✨ About

**Lumenfetch** is a lightweight Python CLI that downloads YouTube videos as **MP4** or extracts their audio as **MP3**. Just paste a link and it auto-detects the title, duration, and estimated file size, then offers the relevant quality options. Powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) under the hood, plus `curl_cffi` to pass YouTube's bot checks.

> _"One command, straight to MP4/MP3."_

## 🎯 Features

| Feature | Description |
|-------|-------------|
| 🔍 **Auto-detect** | Title, duration, and size estimates detected automatically |
| 🎛 **Dynamic options** | Quality menu adapts itself (video vs audio) |
| 🎞 **MP4 video** | Quality Best/1080p/720p/480p/360p/Worst, thumbnail auto-embedded |
| 🎵 **MP3 audio** | Bitrate Best/320kbps/192kbps/128kbps |
| 📜 **Playlists** | First video only by default; `--playlist all` for the whole list |
| 💬 **Subtitles & metadata** | Download subtitles + embed into MP4, optional via flags |
| 🌍 **English/Indonesian UI** | Display language via `--ui-lang id`, `LUMENFETCH_LANG`, or remembered setting |
| 📋 **Clipboard auto-paste** | A valid link in your clipboard is offered right away, never asked twice for the same content |
| 📊 **Real-time progress** | Speed, size, and ETA via `rich` |
| 📐 **Size & time estimates** | Shown next to every quality option, computed from yt-dlp data + your own past download speeds |
| 🔄 **Auto-retry & resume** | Connection errors retried with exponential backoff (default 3x); partial `.part` files resumed, not restarted |
| 🗂 **Download history** | Last 20 entries, viewable anytime with the `history` command |
| ⚙️ **Persistent settings** | Download folder, max retry, auto-paste, and naming template remembered |
| 🍪 **Browser/file cookies** | Optional, for age-restricted or private videos - from Chrome/Firefox/Edge/etc. or a `cookies.txt` file |
| 🧼 **Safe filenames** | Illegal characters sanitized, duplicates get `(1)`, `(2)` suffixes |
| 🔔 **yt-dlp update check** | Checks PyPI for a newer yt-dlp on every start, silently ignored when offline |

## 📦 Requirements

- **Python** 3.9 or newer
- **Internet connection**
- Libraries: `yt-dlp`, `rich`, `curl_cffi`, auto-installed with `lumenfetch`, no manual install needed

> ffmpeg **does not need manual install** - Lumenfetch uses your system ffmpeg if present, otherwise it automatically downloads its own bundled copy (via `static-ffmpeg`) on first use, just like `ffmpeg-static` in Node.js projects.

### Never used a terminal? Start here

<details>
<summary><b>🪟 Opening a terminal on Windows</b></summary>

1. Press the **Windows** key, type `PowerShell`, then press **Enter**
2. A black/blue window opens. Type all `python ...` / `pip ...` commands from this guide there, then press **Enter**

</details>

<details>
<summary><b>🍎 Opening a terminal on macOS</b></summary>

1. Press **Cmd + Space**, type `Terminal`, then press **Enter**
2. Type the commands from this guide there, then press **Enter**

</details>

<details>
<summary><b>🐧 Opening a terminal on Linux</b></summary>

Press **Ctrl + Alt + T**, or find the "Terminal" app in your app menu.

</details>

### No Python yet?

1. Open [python.org/downloads](https://www.python.org/downloads/) and download the latest version
2. **Windows only**: on the first installer screen, tick **"Add Python to PATH"** before clicking Install. If you skip this, the `python` command won't be recognized later
3. After installing, open a terminal (see above) and check with:

```bash
python --version
# or
python3 --version
```

If a version number shows up (e.g. `Python 3.12.1`), you're ready.

## 🚀 Installation

### Option A: Install from PyPI (easiest)

```bash
pip install lumenfetch
```

> If `pip` is not recognized, try:
> ```bash
> python -m pip install lumenfetch
> ```

> If you get an `externally-managed-environment` error (usually on Linux):
> ```bash
> pip install lumenfetch --break-system-packages
> ```

Once installed, the `lumenfetch` command works from any terminal, continue to [Usage](#️-usage).

### Option B: Install from source (for development / reading the code)

**1. Get the code**

<details>
<summary><b>Have Git installed</b></summary>

```bash
git clone https://github.com/nekonaru/lumenfetch.git
cd lumenfetch
```

</details>

<details>
<summary><b>No Git</b></summary>

1. Open the repository page on GitHub
2. Click the green **`Code`** button → choose **`Download ZIP`**
3. Extract the downloaded ZIP to a folder of your choice
4. In a terminal, enter the extracted folder, e.g.:

```bash
cd Downloads/lumenfetch-main
```

</details>

**2. Install in "editable" mode**
```bash
pip install -e .
```

> Same as Option A, append `--break-system-packages` if you hit the `externally-managed-environment` error.

This also registers the `lumenfetch` command, but it uses the code straight from this folder, handy if you want to modify the code and see results without reinstalling.

## 🖥️ Usage

**Run:**
```bash
lumenfetch
```

> If you installed from source without `pip install -e .`, run via `python main.py` from inside the project folder instead, but the editable install above is recommended.

**Paste a YouTube URL when asked:**
```
Masukkan URL YouTube (q: keluar, history, settings, help): https://youtube.com/watch?v=...
```

If there is a valid link in your clipboard, Lumenfetch offers it first - just answer `y` to use it.

**Pick an output type:**
```
Pilih tipe output:
  [1] Video (MP4)
  [2] Audio (MP3)
```

**Pick a quality (size & ETA estimates included):**
```
Pilih Quality:
  [1] Best   (default)  (~147.8 MB, ~31 detik)
  [2] 1080p              (~147.8 MB, ~31 detik)
  [3] 720p               (~81.1 MB, ~17 detik)
  [4] 480p               (~42.9 MB, ~9 detik)
```

**Confirm the filename, then the download runs** with a real-time progress bar (speed, size, ETA). Press `Ctrl+C` anytime to cancel safely.

**Done! 🎉**
```
✅ Selesai!
   File  : C:\Users\user\Downloads\YouTube_Lofi-Hip-Hop-Radio_2026.mp4
   Ukuran: 81.1 MB
   Waktu : 17 detik
```

## ↻ Resume Otomatis

If a download stops halfway (connection drops, terminal closed), the partial `.part` file stays on disk.

Just run the same URL again and yt-dlp **resumes** from where it stopped instead of starting over. Connection errors are also retried automatically with exponential backoff (2s, 4s, 8s... max 30s).

## ⚙️ Preferensi Tersimpan

Your download folder, max retry, auto-paste, naming template, and cookies choice are saved automatically in your user config dir and reused as defaults next session:

| OS | Config location |
|----|-----------------|
| 🪟 Windows | `%APPDATA%\lumenfetch\config.json` |
| 🍎 macOS | `~/Library/Application Support/lumenfetch/config.json` |
| 🐧 Linux | `~/.config/lumenfetch/config.json` |

Detailed logs live in `lumenfetch.log` in the same folder (run with `-v/--verbose` for debug level).

## 🌍 Display Language

The CLI (menus, prompts, messages, and `--help` text) is available in **English** (default) and **Bahasa Indonesia**.

```bash
lumenfetch --ui-lang id              # Bahasa Indonesia, remembered for next sessions
lumenfetch --ui-lang en              # back to English
LUMENFETCH_LANG=id lumenfetch        # via environment variable (Windows: set LUMENFETCH_LANG=id)
```

Priority order: `--ui-lang` → `LUMENFETCH_LANG` env → `ui_lang` in user config → default `en`.

## 📜 Playlist

A playlist URL downloads **only the first video** by default (with a warning), so one URL never silently floods your folder. To grab the whole list as indexed files:

```bash
lumenfetch "https://youtube.com/playlist?list=PLxxxxxx" --playlist all -y
```

## 📦 Batch Download

Put one URL per line in a text file (`#` = comment), then:

```bash
lumenfetch --batch daftar.txt --jobs 2
```

## 🍪 Cookies (Optional)

Age-restricted or private videos need a login. If you hit such errors, enable one of these:

**A. Browser cookies:**
1. Open Lumenfetch, type `settings`
2. Pick `[5] Pakai cookies dari browser/file`
3. Pick the browser where you're logged into YouTube (Chrome/Firefox/Edge/Brave/Opera/Vivaldi/Safari)

> **Important:** the chosen browser must be **fully closed** while downloading (its cookie file is locked while open - the error looks like `Could not copy ... cookie database`). Check Task Manager and kill all its processes (Edge/Chrome often keep running in the background).

**B. Cookie file (most reliable, recommended if cookie errors persist):**
1. Install the **"Get cookies.txt LOCALLY"** extension (Chrome/Edge/Firefox)
2. Open youtube.com (make sure you're logged in), click the extension → **Export** → save e.g. `D:\cookies.txt`
3. In Lumenfetch: `settings` → `[5]` → `[1] Nonaktifkan` → enter the cookie file path
4. Or via CLI: `lumenfetch <URL> --cookies-file D:\cookies.txt`

## 🤖 Non-Interactive Mode (Scripting/Automation)

Besides the Q&A mode, Lumenfetch also runs via command line arguments, handy for scheduling (cron/Task Scheduler) or calling from other scripts.

```bash
lumenfetch "https://youtube.com/watch?v=..." -t video -f mp4 -q 720p -y
```

**Available arguments:**

| Argument | Description |
|---|---|
| `url` | YouTube video/playlist URL. Filling this enables non-interactive mode when combined with other flags. |
| `-t/--type {video,audio}` | Output type |
| `-f/--format {mp4,mp3}` | Output format |
| `-q/--quality` | Video quality (Best/1080p/720p/480p/360p/Worst) or MP3 bitrate (Best/320kbps/192kbps/128kbps) |
| `-o/--output` | Custom output folder |
| `--cookies` | Browser cookies (chrome/firefox/edge/brave/opera/vivaldi/safari/none) |
| `--cookies-file` | Netscape-format cookie file |
| `--max-retry` | Connection retry count |
| `--playlist {single,all}` | Playlist mode |
| `--subs` | Download subtitles when available |
| `--sub-langs` | Subtitle languages, comma-separated (default: en,id) |
| `--embed-subs` | Embed subtitles into the MP4 file |
| `--embed-metadata` | Embed metadata (title/artist) into the output file |
| `--batch` | Text file with URLs (one per line) |
| `--jobs N` | Batch parallelism 1-4 (default 1) |
| `--no-clipboard` | Don't offer clipboard content |
| `--ui-lang {en,id}` | Display language (default `en`, remembered after being set) |
| `-y/--yes` | Skip the filename confirmation |
| `-v/--verbose` | Detailed logging to file + console |
| `--history` | Show history and exit |
| `--version` | Show the version |

**More examples:**

```bash
# Audio only, best bitrate
lumenfetch "https://youtube.com/watch?v=..." -t audio -q 320kbps -y

# Whole playlist as MP4
lumenfetch "https://youtube.com/playlist?list=PLxxx" --playlist all -y

# With subtitles embedded
lumenfetch "https://youtube.com/watch?v=..." -t video --subs --embed-subs -y

# Batch of URLs, 2 at a time
lumenfetch --batch daftar.txt --jobs 2

# See all options
lumenfetch --help
```

## 📂 Output Structure

Filenames follow the template in settings (default: `%(platform)s_%(title)s_%(year)s`):

```
YouTube_Lofi-Hip-Hop-Radio_2026.mp4
YouTube_Lofi-Hip-Hop-Radio_2026.mp3
```

## 🗺️ Default Folder per OS

| OS | Default folder |
|----|----------------|
| 🪟 Windows | `C:\Users\<username>\Downloads` |
| 🍎 macOS | `/Users/<username>/Downloads` |
| 🐧 Linux | `/home/<username>/Downloads` |

Change it anytime via the `settings` command (`[1]`), absolute paths and `~` are both accepted.

## ⚠️ Troubleshooting

| Problem | Solution |
|---------|--------|
| `ModuleNotFoundError: No module named 'yt_dlp'` / `'rich'` / `'curl_cffi'` | Re-run `pip install lumenfetch` (or `pip install -r requirements.txt` from source) |
| `HTTP Error 403: Forbidden` | Update yt-dlp: `pip install --upgrade yt-dlp` |
| `Sign in to confirm you're not a bot` | Enable **Cookies** above (browser or file) |
| `❌ Private / unavailable content` | Private/age-restricted video - enable **Cookies** above |
| `❌ Format not available for this content` | Try another quality |
| `❌ Connection trouble` keeps showing | Check your connection, or raise `max_retry` via `settings` |
| Downloaded video has no sound | Rare since ffmpeg is bundled, but if it happens, restart the app (the bundle re-downloads automatically if corrupted) |
| Naming template rejected in `settings` | Only `%(platform)s`, `%(title)s`, `%(year)s` are allowed - rejected automatically on typos so filenames never break |
| `⚠️ Playlist with N videos` | Only the first video by default. Use `--playlist all` for all of them as indexed files |
| `ffmpeg not found` | Install system ffmpeg first (lighter), bundled fallback is automatic. Check with `ffmpeg -version` |

## 📝 Important Notes

- Only YouTube links are accepted (`youtube.com`, `youtu.be`, `music.youtube.com`) - other platforms are rejected with a clear message, not a crash
- A `Sign in to confirm you're not a bot` message means YouTube is challenging automated requests: install/update `curl_cffi` + `yt-dlp`, then enable cookies
- This tool is for downloading videos you have the right to save (your own uploads, Creative Commons, offline watching). Respect creators' copyright

## 🛠️ Built With

![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white)
![yt-dlp](https://img.shields.io/badge/-yt--dlp-FF6B6B?style=flat-square)
![Rich](https://img.shields.io/badge/-Rich-FAE742?style=flat-square)
![curl-cffi](https://img.shields.io/badge/-curl--cffi-2B579A?style=flat-square)

## 🗂️ Project Structure

```
lumenfetch/
├── main.py                    # Entry point, CLI args, batch, main loop
├── core/
│   ├── constants.py           # Single source of truth (version, formats, limits)
│   ├── errors.py              # Central error taxonomy (classification + friendly messages)
│   ├── i18n.py                # UI strings (English default, Indonesian via --ui-lang)
│   ├── ffmpeg.py              # System ffmpeg first, bundled fallback
│   ├── log.py                 # Central file logging
│   ├── downloader.py          # MP4 download / MP3 extract + resume + retry backoff
│   ├── detector.py            # YouTube video info detection
│   ├── options.py             # Interactive menus & prompts (rich)
│   ├── update_checker.py      # Auto-check for newer yt-dlp on PyPI
│   └── utils.py               # Filename sanitizing, size formatting, user config
├── tests/
│   ├── conftest.py            # Global fixtures (no-sleep) + SAMPLE_VIDEO_FORMATS
│   ├── test_utils.py
│   ├── test_detector.py
│   ├── test_downloader.py
│   ├── test_options.py
│   ├── test_main.py
│   └── test_features.py       # Features (CLI, backoff, batch, ffmpeg, cookies, log)
├── .github/
│   └── workflows/
│       └── tests.yml          # CI: automatic test & lint
├── requirements.txt           # Dependency list (for manual reference)
├── pyproject.toml             # Package metadata + entry point + ruff config
├── CONTRIBUTING.md            # Contribution guide
├── LICENSE
├── README.md                  # Main docs (English)
└── README.id.md               # Docs (Bahasa Indonesia)
```

**Module separation principles:**
- `constants.py`, shared values (version, formats, limits) so modules never drift
- `errors.py`, central error classification used by detector & downloader together
- `detector.py`, purely detects YouTube video info, never downloads anything
- `downloader.py`, purely MP4/MP3 processing & progress, never shows menus
- `options.py`, all user interaction & menus, no download logic
- `utils.py`, pure helpers (sanitizing, formatting, config read/write), knows nothing about CLI or network
- `main.py`, ties everything together via CLI + main loop

## 🧪 Testing

Unit tests per module (filename sanitizing, naming templates, duplicate resolving, size/duration formatting, config, YouTube URL validation, yt-dlp opts, CLI, etc.).

```bash
pip install -e .[dev]
pytest tests/ -v
ruff check .
```

CI (`.github/workflows/tests.yml`) runs these automatically on every push & pull request to `main`.

## 🤝 Contributing

Want to help develop Lumenfetch? Read [`CONTRIBUTING.md`](CONTRIBUTING.md) for the project structure and contribution flow.

## ❓ FAQ

<details>
<summary><b>Is this legal / safe to use?</b></summary>

This tool uses the same requests your browser makes when you watch YouTube, so it doesn't hack anything. But use it responsibly: download for personal/offline use, and respect creators' copyright. Don't re-upload or sell other people's content.

</details>

<details>
<summary><b>Do I need a YouTube account?</b></summary>

No, not for public videos. You only need to be logged in (via cookies) for age-restricted or private videos you have access to.

</details>

<details>
<summary><b>Private / deleted video, can it be downloaded?</b></summary>

No. Only content that your account can actually watch can be downloaded.

</details>

<details>
<summary><b>Why is the process slow?</b></summary>

Download speed follows your connection. Connection errors are retried automatically with backoff, and interrupted downloads resume instead of restarting.

</details>

<details>
<summary><b>Which quality should I pick?</b></summary>

- Want the best available → **Best**
- Want smaller files for phone storage → **720p** or **480p**
- Audio only for music/podcasts → **MP3 320kbps**

</details>

## 👤 Author

<div align="center">

| [![Nicolas Dwi Dharma](https://github.com/github.png?size=100)](https://github.com/nekonaru) |
|:---:|
| **Nicolas Dwi Dharma** |
| [github.com/nekonaru](https://github.com/nekonaru) |

</div>

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

<div align="center">

Made with 📥 by **Nicolas Dwi Dharma**

*Star ⭐ this repo if the project helps you!*

</div>
