"""User preferences — JSON-based config stored in ~/.config/screenshot-namer/."""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "screenshot-namer"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "watch_dir": str(Path.home() / "Desktop"),
    "output_dir": str(Path.home() / "Screenshots"),
    "watching_enabled": True,
    "start_at_login": False,
    "notifications": True,
}


def load() -> dict:
    """Load config from disk, creating defaults if needed."""
    if not CONFIG_FILE.exists():
        save(DEFAULTS)
        return dict(DEFAULTS)

    with open(CONFIG_FILE) as f:
        stored = json.load(f)

    # Merge with defaults so new keys are always present
    merged = {**DEFAULTS, **stored}
    return merged


def save(cfg: dict) -> None:
    """Write config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get(key: str) -> object:
    """Get a single config value."""
    return load()[key]


def set_value(key: str, value: object) -> None:
    """Set a single config value and persist."""
    cfg = load()
    cfg[key] = value
    save(cfg)
