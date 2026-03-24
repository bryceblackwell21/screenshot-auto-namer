# Screenshot Auto-Namer & Sorter — Product Spec

**Status:** Phase 2 — Menu Bar App
**Owner:** Bryce Blackwell
**Repo:** github.com/bryceblackwell21/screenshot-auto-namer

## Problem

macOS screenshots are saved as `Screenshot YYYY-MM-DD at HH.MM.SS.png` — impossible to search, browse, or organize. Paid tools (ScreenSnapAI, KeepItShot) exist but cost money and offer limited customization. There's no free, AI-powered option that works like a native macOS utility you can set and forget.

## Solution

A macOS menu bar app that silently watches for new screenshots, uses Claude's Vision API to analyze their content, generates descriptive filenames, and sorts files into topic-based folders — all automatically. Works like Magnet or KeepItShot: install it, toggle it on, forget about it.

## Product Vision

The app should feel like a native macOS utility:
- **Menu bar icon** with status indicator (active/paused)
- **Toggle on/off** with a click — no terminal needed
- **Start at Login** option — survives reboots
- **macOS notifications** when screenshots are processed
- **Zero configuration required** to start (sensible defaults, configure later if you want)

---

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────┐
│  macOS Menu Bar (rumps)                         │
│  ┌───────────┐  ┌──────────┐  ┌─────────────┐  │
│  │ Status    │  │ Toggle   │  │ Settings    │  │
│  │ Icon      │  │ On/Off   │  │ Menu Items  │  │
│  └───────────┘  └──────────┘  └─────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │ controls
┌──────────────────────▼──────────────────────────┐
│  Watcher (rumps.Timer polling, ~3s interval)    │
│  Monitors ~/Desktop for new screenshot files    │
└──────────────────────┬──────────────────────────┘
                       │ new file detected
┌──────────────────────▼──────────────────────────┐
│  analyzer.py — Claude Vision API                │
│  Image → {filename_slug, category, description} │
└──────────────────────┬──────────────────────────┘
                       │ structured result
┌──────────────────────▼──────────────────────────┐
│  renamer.py — File Operations                   │
│  Rename + move to ~/Screenshots/<category>/     │
└─────────────────────────────────────────────────┘
```

### Key Files

```
app.py           Menu bar app entry point (rumps). Owns the UI and watcher loop.
analyzer.py      Sends images to Claude Vision API → structured naming metadata.
renamer.py       File operations: rename, move to category folder, conflict resolution.
config.py        User preferences (watch dir, output dir, model, start-at-login, etc.)
main.py          CLI entry point (kept for batch processing / scripting use cases).
```

### Why rumps (not Swift, not Launch Agent alone)

| Option | Verdict |
|---|---|
| **Launch Agent only** | Invisible daemon — no way to toggle on/off, see status, or configure without a terminal. Not a good UX. |
| **Swift/SwiftUI menu bar + Python backend** | Best native feel, but requires two languages and IPC. Overkill for v1. Worth revisiting if we want App Store distribution. |
| **rumps (Python menu bar)** | Single-language, single-process. Menu bar icon, toggles, notifications, timers all built in. Good enough for a personal tool and demo. Upgrade path to Swift later. |

**Threading note:** Rather than using `watchdog` (which runs its own thread and requires careful queue-based IPC to update the UI safely), we use `rumps.Timer` to poll the watch directory every ~3 seconds. For a screenshots folder that gets a few files per hour, polling is simpler, eliminates threading bugs, and the latency is imperceptible.

### Auto-Start: LaunchAgent (installed by the app)

The menu bar app includes a "Start at Login" toggle. When enabled, it writes a LaunchAgent plist to `~/Library/LaunchAgents/` that points to the app. macOS then:
- Starts the app automatically on login
- Keeps it alive if it crashes (`KeepAlive: true`)
- Runs silently in the background

When disabled, the plist is removed. This is the same pattern used by apps like KeepingYouAwake and other indie menu bar tools.

---

## Core Behaviors

**API:** Anthropic Claude Sonnet (vision) — best cost/quality tradeoff for image analysis (~$3/1M input tokens, ~1600 tokens per image ≈ $0.005/screenshot).

**Filename format:** `descriptive-slug.ext` — no date prefix (filesystem created/modified dates handle chronology). Slug is app-first, 3-5 words, specific to content.

**Category detection:** Claude auto-detects from content. Suggested categories: code, email, chat, social-media, documentation, design, browser, spreadsheet, presentation, settings, error. Claude can create new slugs if nothing fits.

**Output structure:**

```
~/Screenshots/
├── code/
│   └── vscode-python-debug-breakpoint.png
├── email/
│   └── gmail-project-update-thread.png
├── design/
│   └── figma-landing-hero-section.png
└── chat/
    └── slack-standup-thread.png
```

---

## Menu Bar UX

```
  [ camera icon ]
  ─────────────────────
  Watching: ✓ ON          ← click to toggle
  ─────────────────────
  Last: vscode-debug...   ← most recent file processed
  Today: 4 processed      ← daily counter
  ─────────────────────
  Watch Folder: ~/Desktop     ► (submenu to change)
  Output Folder: ~/Screenshots ► (submenu to change)
  ─────────────────────
  Start at Login: ✓       ← toggle, manages LaunchAgent plist
  Notifications: ✓        ← toggle macOS notifications
  ─────────────────────
  Process All Now...       ← batch-process existing screenshots
  Open Output Folder       ← Finder.reveal
  ─────────────────────
  Quit Screenshot Namer
```

---

## CLI Interface (retained for power users / scripting)

```
python main.py [OPTIONS]

--input, -i    Source directory (default: ~/Desktop)
--output, -o   Output base directory (default: ~/Screenshots)
--file, -f     Process a single file
--dry-run, -n  Preview without moving files
--verbose, -v  Debug logging
```

---

## Configuration

Stored in `~/.config/screenshot-namer/config.json`:

```json
{
  "watch_dir": "~/Desktop",
  "output_dir": "~/Screenshots",
  "model": "claude-sonnet-4-20250514",
  "start_at_login": true,
  "notifications": true,
  "watching_enabled": true
}
```

- **API key:** `ANTHROPIC_API_KEY` in `.env` file (loaded via python-dotenv with override)
- **Dependencies:** `anthropic`, `python-dotenv`, `rumps` (Python 3.9+)

---

## Phasing

### Phase 1 — CLI MVP (COMPLETE)

- [x] Project scaffolding (README, claude.md, .gitignore)
- [x] Single screenshot → API call → renamed file (end-to-end)
- [x] Batch processing (all screenshots in a directory)
- [x] Dry-run mode
- [x] Conflict resolution (append -1, -2 for duplicate names)
- [x] Python 3.9 compatibility fix
- [x] GitHub repo created

### Phase 2 — Menu Bar App (CURRENT)

- [ ] `app.py` — rumps menu bar app with toggle on/off
- [ ] Timer-based polling for new screenshots (replaces watchdog watcher.py)
- [ ] macOS notifications on successful processing
- [ ] "Start at Login" toggle (LaunchAgent plist management)
- [ ] `config.py` — JSON-based preferences
- [ ] Daily processing counter in menu
- [ ] "Open Output Folder" action
- [ ] "Process All Now" batch action from menu

### Phase 3 — Polish & Distribution

- [ ] App icon (template image for light/dark mode)
- [ ] py2app packaging into a .app bundle (LSUIElement for menu-bar-only)
- [ ] Code signing + notarization for Gatekeeper
- [ ] install.sh one-liner for easy setup
- [ ] Cost tracking / budget limits
- [ ] Undo log (record of moves for easy reversal)
- [ ] Configurable category rules

### Phase 4 — Future / If Needed

- [ ] Swift/SwiftUI menu bar rewrite (native feel, smaller bundle, App Store ready)
- [ ] Preferences window (rumps doesn't support windows — would need Swift or PyObjC)
- [ ] Duplicate/near-duplicate detection (perceptual hashing)
- [ ] Haiku model option for cheaper processing of obvious screenshots
- [ ] Async/concurrent API calls for large batches

---

## Competitive Comparison

| Feature | This Tool | ScreenSnapAI | KeepItShot |
|---|---|---|---|
| Price | Free (API costs ~$0.005/img) | Paid subscription | Paid subscription |
| Customization | Full (open source) | Limited | Limited |
| Categories | AI auto-detect, unlimited | Fixed set | Fixed set |
| Batch processing | Yes | Yes | Yes |
| Auto-watch folder | Yes (menu bar app) | Yes | Yes |
| Menu bar control | Yes | Yes | Yes |
| Start at Login | Yes | Yes | Yes |
| Offline mode | No (needs API) | Yes (on-device) | Yes (on-device) |

## Risks & Mitigations

- **API costs at scale:** Sonnet vision is cheap (~$0.005/image), but high volume could add up. Mitigation: add daily budget limit in config, consider Haiku for simple screenshots.
- **Slow for large batches:** Each API call takes 1-3s. Mitigation: Phase 4 adds async/concurrent requests.
- **Misclassification:** Claude may miscategorize ambiguous content. Mitigation: confidence scores, notifications show what happened, undo log in Phase 3.
- **rumps limitations:** No preferences window, no complex UI. Mitigation: keep menu simple; upgrade to Swift shell in Phase 4 if needed.
- **PyObjC compatibility:** rumps depends on PyObjC which could break on future macOS versions. Mitigation: low-risk (stable API surface), Swift rewrite is the escape hatch.
