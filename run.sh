#!/bin/bash
# Convenience wrapper — runs the tool without needing to activate the venv manually.
# Usage:
#   bash run.sh                     # process Desktop screenshots
#   bash run.sh --dry-run           # preview without moving
#   bash run.sh --file ~/Desktop/screenshot.png

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "Run 'bash setup.sh' first."
    exit 1
fi

"$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/main.py" "$@"
