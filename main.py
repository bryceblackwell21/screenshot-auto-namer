#!/usr/bin/env python3
"""Screenshot Auto-Namer & Sorter — CLI entry point.

Analyzes screenshots using Claude's Vision API, generates descriptive filenames,
and sorts them into topic-based folders.

Usage:
    python main.py                          # Process all screenshots on Desktop
    python main.py --input ~/Desktop        # Specify input directory
    python main.py --output ~/Screenshots   # Specify output directory
    python main.py --file screenshot.png    # Process a single file
    python main.py --dry-run                # Preview changes without moving files
"""

import argparse
import logging
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from analyzer import analyze_screenshot
from renamer import move_screenshot

# Load .env file if present (for ANTHROPIC_API_KEY)
load_dotenv()

# Supported image extensions (macOS screenshot formats)
SCREENSHOT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".heic", ".webp"}

# Defaults
DEFAULT_INPUT = Path.home() / "Desktop"
DEFAULT_OUTPUT = Path.home() / "Screenshots"


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler()],
    )


def find_screenshots(input_dir: Path) -> list[Path]:
    """Find all screenshot files in a directory (non-recursive)."""
    files = []
    for f in sorted(input_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in SCREENSHOT_EXTENSIONS:
            # Only grab files that look like macOS screenshots or generic images
            files.append(f)
    return files


def process_single(
    file_path: Path,
    output_dir: Path,
    client: anthropic.Anthropic,
    dry_run: bool = False,
) -> bool:
    """Process a single screenshot. Returns True on success."""
    log = logging.getLogger(__name__)

    log.info(f"  Analyzing: {file_path.name}")

    try:
        result = analyze_screenshot(file_path, client=client)
    except Exception as e:
        log.error(f"  ✗ Analysis failed: {e}")
        return False

    dest = move_screenshot(file_path, result, output_dir, dry_run=dry_run)
    prefix = "[DRY RUN] " if dry_run else ""
    log.info(f"  {prefix}→ {dest.relative_to(output_dir.parent) if not dry_run else dest}")
    log.info(f"    Category: {result.category} | Confidence: {result.confidence:.0%}")
    log.info(f"    Description: {result.description}")
    log.info("")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze screenshots with Claude Vision, rename and sort them.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Directory to scan for screenshots (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Base directory for sorted output (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--file", "-f",
        type=Path,
        default=None,
        help="Process a single file instead of a directory",
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
    setup_logging(args.verbose)
    log = logging.getLogger(__name__)

    # Validate API key is available
    try:
        client = anthropic.Anthropic()
    except (anthropic.AuthenticationError, anthropic.APIError, Exception) as e:
        if "api_key" in str(e).lower() or "auth" in str(e).lower():
            log.error("Error: ANTHROPIC_API_KEY not set.")
            log.error("Set it via: export ANTHROPIC_API_KEY='your-key-here'")
            log.error("Or create a .env file with: ANTHROPIC_API_KEY=your-key-here")
            return 1
        raise

    if args.dry_run:
        log.info("🔍 DRY RUN — no files will be moved\n")

    # Single file mode
    if args.file:
        if not args.file.exists():
            log.error(f"File not found: {args.file}")
            return 1
        log.info(f"Processing single file:")
        success = process_single(args.file, args.output, client, dry_run=args.dry_run)
        return 0 if success else 1

    # Batch mode
    if not args.input.is_dir():
        log.error(f"Input directory not found: {args.input}")
        return 1

    screenshots = find_screenshots(args.input)
    if not screenshots:
        log.info(f"No screenshots found in {args.input}")
        return 0

    log.info(f"Found {len(screenshots)} screenshot(s) in {args.input}\n")

    success_count = 0
    fail_count = 0

    for screenshot in screenshots:
        if process_single(screenshot, args.output, client, dry_run=args.dry_run):
            success_count += 1
        else:
            fail_count += 1

    log.info(f"Done: {success_count} processed, {fail_count} failed")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
