#!/bin/bash
# Convenience wrapper — starts the file watcher.
# Usage:
#   bash watch.sh                    # watch Desktop, auto-process new screenshots
#   bash watch.sh --dry-run          # preview without moving
#   bash watch.sh --input ~/Desktop  # custom watch directory

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "Run 'bash setup.sh' first."
    exit 1
fi

"$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/watcher.py" "$@"
