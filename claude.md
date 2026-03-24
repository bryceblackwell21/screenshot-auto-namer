# Screenshot Auto-Namer & Sorter — Claude.md

## Project Overview
macOS menu bar app that uses Claude Vision API to analyze screenshot content, generate descriptive filenames, and sort files into category folders. Runs as a set-and-forget background utility.

## Architecture
- **app.py** — Menu bar app entry point (rumps). Owns the UI, polling timer, and watcher loop.
- **analyzer.py** — Core module. Sends images to Claude Vision API, parses response into structured {name, category, confidence} output.
- **renamer.py** — File operations. Handles renaming, moving to category folders, conflict resolution (appends `-1`, `-2` etc).
- **config.py** — User preferences. JSON-based config in `~/.config/screenshot-namer/config.json`.
- **main.py** — CLI entry point (argparse). Retained for batch processing and scripting.

## Key Decisions
- **API**: Anthropic Claude (`claude-sonnet-4-20250514`) with vision. Sonnet is the best cost/quality tradeoff for image analysis.
- **Categories**: Auto-detected by Claude, not hardcoded. The prompt asks Claude to pick from a suggested set OR create a new slug if nothing fits.
- **Filename format**: `descriptive-slug.ext` — no date prefix (filesystem tracks created/modified dates). Slug is app-first, 3-5 words, specific to the content.
- **Naming rules**: Lead with app/context (e.g. "vscode-", "slack-"), focus on what's unique, no generic words, no dates unless content-critical.
- **Output dir**: `~/Screenshots/<category>/` — created on demand.
- **API key**: `ANTHROPIC_API_KEY` env var, with python-dotenv (override=True) fallback to `.env` file.
- **Menu bar**: rumps library — single-process Python app with polling timer instead of watchdog threads.
- **Auto-start**: LaunchAgent plist managed by "Start at Login" toggle in menu.

## Conventions
- Python 3.9+ (use `from __future__ import annotations` for type hint compatibility)
- Type hints on all functions
- No classes unless needed — keep it functional and simple
- Error handling: never delete/overwrite originals silently. Log everything.
- Dry-run mode must be the safe default for development.

## Dependencies
- `anthropic` — API client
- `python-dotenv` — .env support
- `rumps` — macOS menu bar app framework
- Standard lib: `pathlib`, `shutil`, `argparse`, `json`, `base64`, `plistlib`

## Testing
- Use `--dry-run` for safe testing via CLI
- Menu bar app snapshots existing files on startup and only processes new ones
- Test with diverse screenshots: code editors, browsers, chat apps, terminal, design tools
- Watch API costs — Sonnet vision is ~$3/1M input tokens, images ~1600 tokens each
