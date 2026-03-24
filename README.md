# Screenshot Auto-Namer & Sorter

CLI tool that uses Claude's Vision API to analyze screenshot content, generate descriptive filenames, and sort files into topic-based folders.

## Setup (one command)

```bash
bash setup.sh
```

This creates a virtual environment, installs dependencies, and prompts for your API key.

## Usage

```bash
# Preview what would happen (recommended first run)
bash run.sh --dry-run

# Process all screenshots on Desktop → ~/Screenshots/<category>/
bash run.sh

# Process a single file
bash run.sh --file ~/Desktop/screenshot.png

# Custom input/output directories
bash run.sh --input ~/Desktop --output ~/Screenshots
```

## Output

```
~/Screenshots/
├── code/
│   └── 2026-03-24_vscode-python-debug-config.png
├── chat/
│   └── 2026-03-24_slack-team-standup-thread.png
├── design/
│   └── 2026-03-24_figma-landing-page-mockup.png
└── browser/
    └── 2026-03-24_chrome-api-docs-anthropic.png
```
