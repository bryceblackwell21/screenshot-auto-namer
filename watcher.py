#!/usr/bin/env python3
"""File watcher — monitors a directory for new screenshots and auto-processes them.

Usage:
    python watcher.py                          # Watch ~/Desktop, output to ~/Screenshots
    python watcher.py --input ~/Desktop        # Custom watch directory
    python watcher.py --output ~/Screenshots   # Custom output directory
    python watcher.py --dry-run                # Preview mode (no moves)
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from analyzer import analyze_screenshot
from renamer import move_screenshot

load_dotenv(override=True)

SCREENSHOT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".heic", ".webp"}

DEFAULT_INPUT = Path.home() / "Desktop"
DEFAULT_OUTPUT = Path.home() / "Screenshots"

# Seconds to wait after file creation before processing (macOS writes screenshots in chunks)
SETTLE_DELAY = 2.0

log = logging.getLogger(__name__)


class ScreenshotHandler(FileSystemEventHandler):
    """Watches for new screenshot files and processes them automatically."""

    def __init__(self, output_dir: Path, client: anthropic.Anthropic, dry_run: bool = False) -> None:
        super().__init__()
        self.output_dir = output_dir
        self.client = client
        self.dry_run = dry_run

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if file_path.suffix.lower() not in SCREENSHOT_EXTENSIONS:
            return

        log.info(f"New screenshot detected: {file_path.name}")

        # Wait for the file to finish writing
        self._wait_for_stable(file_path)

        if not file_path.exists():
            log.warning(f"  File disappeared before processing: {file_path.name}")
            return

        self._process(file_path)

    def _wait_for_stable(self, file_path: Path) -> None:
        """Wait until the file size stops changing (i.e., writing is complete)."""
        prev_size = -1
        for _ in range(10):
            time.sleep(SETTLE_DELAY)
            if not file_path.exists():
                return
            curr_size = file_path.stat().st_size
            if curr_size == prev_size and curr_size > 0:
                return
            prev_size = curr_size

    def _process(self, file_path: Path) -> None:
        """Analyze and move a single screenshot."""
        try:
            result = analyze_screenshot(file_path, client=self.client)
        except Exception as e:
            log.error(f"  Analysis failed: {e}")
            return

        dest = move_screenshot(file_path, result, self.output_dir, dry_run=self.dry_run)
        prefix = "[DRY RUN] " if self.dry_run else ""
        log.info(f"  {prefix}→ {dest}")
        log.info(f"    Category: {result.category} | Confidence: {result.confidence:.0%}")
        log.info(f"    Description: {result.description}")
        log.info("")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Watch for new screenshots and auto-rename/sort them.",
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Directory to watch (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Base directory for sorted output (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview changes without moving any files",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")

    try:
        client = anthropic.Anthropic()
    except Exception as e:
        if "api_key" in str(e).lower() or "auth" in str(e).lower():
            log.error("ANTHROPIC_API_KEY not set. Check your .env file.")
            return 1
        raise

    if not args.input.is_dir():
        log.error(f"Watch directory not found: {args.input}")
        return 1

    handler = ScreenshotHandler(args.output, client, dry_run=args.dry_run)
    observer = Observer()
    observer.schedule(handler, str(args.input), recursive=False)
    observer.start()

    mode = " (DRY RUN)" if args.dry_run else ""
    log.info(f"Watching {args.input} for new screenshots{mode}")
    log.info("Press Ctrl+C to stop.\n")

    def shutdown(signum, frame):
        log.info("\nStopping watcher...")
        observer.stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    observer.join()
    return 0


if __name__ == "__main__":
    sys.exit(main())
