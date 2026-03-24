# Screenshot Auto-Namer & Sorter — Claude.md

## Project Overview
CLI tool that uses Claude Vision API to analyze screenshot content, generate descriptive filenames, and sort files into category folders.

## Architecture
- **main.py** — CLI entry point (argparse). Handles input/output paths, dry-run mode, single-file mode.
- **analyzer.py** — Core module. Sends images to Claude Vision API, parses response into structured {name, category, confidence} output.
- **renamer.py** — File operations. Handles renaming, moving to category folders, conflict resolution (appends `-1`, `-2` etc).

## Key Decisions
- **API**: Anthropic Claude (`claude-sonnet-4-20250514`) with vision. Sonnet is the best cost/quality tradeoff for image analysis.
- **Categories**: Auto-detected by Claude, not hardcoded. The prompt asks Claude to pick from a suggested set OR create a new slug if nothing fits.
- **Filename format**: `YYYY-MM-DD_descriptive-slug.ext` — date prefix for chronological sorting, slug for searchability.
- **Output dir**: `~/Screenshots/<category>/` — created on demand.
- **API key**: `ANTHROPIC_API_KEY` env var, with python-dotenv fallback to `.env` file.

## Conventions
- Python 3.10+
- Type hints on all functions
- No classes unless needed — keep it functional and simple
- Error handling: never delete/overwrite originals silently. Log everything.
- Dry-run mode must be the safe default for development.

## Dependencies
- `anthropic` — API client
- `python-dotenv` — .env support
- Standard lib: `pathlib`, `shutil`, `argparse`, `json`, `base64`, `datetime`

## Testing
- Use `--dry-run` for safe testing
- Test with diverse screenshots: code editors, browsers, chat apps, terminal, design tools
- Watch API costs — Sonnet vision is ~$3/1M input tokens, images ~1600 tokens each

## Phase 1 Scope (This Week)
Working MVP: batch-rename a folder of screenshots using vision API.
- Single file processing ✓
- Batch processing with glob
- Dry-run mode
- Basic error handling + logging
