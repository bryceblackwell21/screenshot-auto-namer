# Screenshot Auto-Namer & Sorter — Product Spec

**Status:** Phase 1 MVP (Tier 2, ICE Score 100)
**Owner:** Bryce Blackwell
**Repo:** `projects/screenshot-auto-namer/`

## Problem

macOS screenshots are saved as `Screenshot YYYY-MM-DD at HH.MM.SS.png` — impossible to search, browse, or organize. Paid tools (ScreenSnapAI) exist but cost money and offer limited customization.

## Solution

A CLI tool that uses Claude's Vision API to analyze screenshot content, generate descriptive filenames, and sort files into topic-based folders automatically.

## Architecture

```
main.py          CLI entry point (argparse). Input/output paths, dry-run, single-file mode.
analyzer.py      Sends images to Claude Vision API → returns {filename_slug, category, description, confidence}
renamer.py       File operations: rename, move to category folder, conflict resolution.
```

**API:** Anthropic Claude Sonnet (vision) — best cost/quality tradeoff for image analysis (~$3/1M input tokens, ~1600 tokens per image ≈ $0.005/screenshot).

**Filename format:** `YYYY-MM-DD_descriptive-slug.ext` (date from file mod time)

**Category detection:** Claude auto-detects from content. Suggested categories: code, email, chat, social-media, documentation, design, browser, spreadsheet, presentation, settings, error. Claude can create new slugs if nothing fits.

## CLI Interface

```
python main.py [OPTIONS]

--input, -i    Source directory (default: ~/Desktop)
--output, -o   Output base directory (default: ~/Screenshots)
--file, -f     Process a single file
--dry-run, -n  Preview without moving files
--verbose, -v  Debug logging
```

## Output Structure

```
~/Screenshots/
├── code/
│   └── 2026-03-24_vscode-python-debug-config.png
├── email/
│   └── 2026-03-24_gmail-project-update-thread.png
├── design/
│   └── 2026-03-24_figma-landing-page-mockup.png
└── uncategorized/
    └── 2026-03-24_misc-capture.png
```

## Configuration

- **API key:** `ANTHROPIC_API_KEY` environment variable, python-dotenv fallback to `.env` file
- **Dependencies:** `anthropic`, `python-dotenv` (Python 3.10+)

## Phase 1 Scope (This Week — Working MVP)

- [x] Project scaffolding (README, claude.md, .gitignore)
- [x] Single screenshot → API call → renamed file (end-to-end)
- [x] Batch processing (all screenshots in a directory)
- [x] Dry-run mode
- [x] Conflict resolution (append -1, -2 for duplicate names)
- [ ] Test with 10+ real screenshots on Desktop

## Phase 2 (Future)

- macOS folder watcher (auto-process new screenshots via `fswatch` or `watchdog`)
- Progress bar for batch processing (`tqdm`)
- Cost tracking / budget limits per run
- Configurable category rules (YAML config file)
- Duplicate/near-duplicate detection (perceptual hashing)
- Undo: log of moves for easy reversal
- Optional: Haiku model for cheaper processing of obvious screenshots

## Competitive Comparison

| Feature | This Tool | ScreenSnapAI |
|---|---|---|
| Price | Free (API costs ~$0.005/img) | Paid subscription |
| Customization | Full (open source) | Limited |
| Categories | AI auto-detect, unlimited | Fixed set |
| Batch processing | Yes | Yes |
| Auto-watch folder | Phase 2 | Yes |
| Offline mode | No (needs API) | Yes (on-device) |

## Risks & Mitigations

- **API costs at scale:** Sonnet vision is cheap (~$0.005/image), but high volume could add up. Mitigation: add `--limit N` flag, consider Haiku for simple screenshots.
- **Slow for large batches:** Each API call takes 1-3s. Mitigation: Phase 2 adds async/concurrent requests.
- **Misclassification:** Claude may miscategorize ambiguous content. Mitigation: confidence scores + `--dry-run` for review.
