# Contributing to Lumenfetch

Thanks for helping develop Lumenfetch. This guide keeps contributions easy to review.

**Bahasa Indonesia** | [English](CONTRIBUTING.md)

> Indonesian version: [`CONTRIBUTING.id.md`](CONTRIBUTING.id.md)

## 🛠 Development Setup

1. Fork & clone this repo
2. Install dependencies (including testing & lint tools):
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Make sure `ffmpeg` is installed on your system (see Requirements in the README)

## 🗂 Module Structure & Principles

Lumenfetch is split by responsibility - please keep it consistent when adding/changing code:

| File | Responsibility | Must not |
|------|----------------|----------|
| `core/constants.py` | Shared values (version, formats, limits) | Business logic |
| `core/errors.py` | Central error classification + friendly messages | Download/detect logic |
| `core/i18n.py` | UI string catalog (EN default, ID optional) | Business logic |
| `core/cli.py` | Argument parsing + non-interactive choice building | Business logic |
| `core/doctor.py` | Setup diagnosis (ffmpeg, deps, cookies, network) | Download/detect |
| `core/ffmpeg.py` | System ffmpeg first, bundled fallback | Download/detect |
| `core/log.py` | Central file logging | Rich display/menus |
| `core/detector.py` | YouTube video info detection via yt-dlp | Download anything |
| `core/downloader.py` | Download process, progress hook, retry | Show menus/prompts |
| `core/options.py` | All interaction & menus (rich) | Download logic |
| `core/utils.py` | Pure helpers: sanitizing, formatting, user config | Depend on CLI or network |
| `main.py` | Ties everything together via CLI + main loop | New business logic |

When adding a feature, put it in the most fitting module first before creating a new file.

## ✅ Before Opening a Pull Request

Run this in the project root:

```bash
pytest tests/ -v
ruff check .
```

Make sure all tests pass and there are no new lint warnings. GitHub Actions also runs these automatically on every PR.

## 📝 Commit Messages

Use short prefixes so history stays readable:

- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation changes (README, CONTRIBUTING, etc.)
- `refactor:` — code structure changes without behavior change
- `test:` — add/change tests

Example: `fix: handle single-video YouTube playlist`

## 🐛 Bug Reports / Feature Requests

Open a new [Issue](../../issues) and include:
- The problematic link (if any, remove personal info)
- The error message shown in the terminal
- Steps to reproduce the problem

## 🤝 Pull Requests

1. Create a new branch from `main` with a clear name (e.g. `fix/playlist-single-video`)
2. Make sure `pytest` and `ruff check .` pass
3. Explain in the PR description what changed and why
4. Wait for review - there may be small change requests before merging
