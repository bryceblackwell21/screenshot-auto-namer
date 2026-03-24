"""File renaming and sorting — handles naming, moving, and conflict resolution."""

import shutil
from datetime import datetime
from pathlib import Path

from analyzer import AnalysisResult


def build_new_filename(result: AnalysisResult, original_path: Path) -> str:
    """Build a new filename from analysis result.

    Format: YYYY-MM-DD_descriptive-slug.ext
    Uses the file's modification date for the date prefix.
    """
    # Use file modification time for the date prefix
    mod_time = original_path.stat().st_mtime
    date_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d")
    ext = original_path.suffix.lower()
    return f"{date_str}_{result.filename_slug}{ext}"


def resolve_conflict(dest_path: Path) -> Path:
    """If dest_path already exists, append -1, -2, etc. until we find an unused name."""
    if not dest_path.exists():
        return dest_path

    stem = dest_path.stem
    ext = dest_path.suffix
    parent = dest_path.parent
    counter = 1

    while True:
        candidate = parent / f"{stem}-{counter}{ext}"
        if not candidate.exists():
            return candidate
        counter += 1


def move_screenshot(
    original_path: Path,
    result: AnalysisResult,
    output_base: Path,
    dry_run: bool = False,
) -> Path:
    """Rename and move a screenshot to its category folder.

    Args:
        original_path: Current path of the screenshot.
        result: Analysis result with filename_slug and category.
        output_base: Base output directory (e.g. ~/Screenshots).
        dry_run: If True, don't actually move anything.

    Returns:
        The final destination path (even in dry-run mode).
    """
    new_filename = build_new_filename(result, original_path)
    category_dir = output_base / result.category
    dest_path = resolve_conflict(category_dir / new_filename)

    if dry_run:
        return dest_path

    # Create category folder if needed
    category_dir.mkdir(parents=True, exist_ok=True)

    # Move the file
    shutil.move(str(original_path), str(dest_path))
    return dest_path
