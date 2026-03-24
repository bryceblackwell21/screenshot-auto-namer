#!/usr/bin/env python3
"""Screenshot Auto-Namer — macOS menu bar app.

Sits in the menu bar, watches for new screenshots, and auto-renames/sorts them
using Claude's Vision API.
"""

from __future__ import annotations

import logging
import os
import plistlib
import subprocess
import sys
from datetime import date
from pathlib import Path

import anthropic
import rumps
from dotenv import load_dotenv

import config
from analyzer import analyze_screenshot
from renamer import move_screenshot

load_dotenv(override=True)

SCREENSHOT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".heic", ".webp"}
POLL_INTERVAL = 3  # seconds
SETTLE_CHECKS = 2  # number of stable-size checks before processing
SETTLE_INTERVAL = 1  # seconds between size checks

LAUNCHAGENT_LABEL = "com.bryceblackwell.screenshot-namer"
LAUNCHAGENT_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHAGENT_LABEL}.plist"

log = logging.getLogger("screenshot-namer")


class ScreenshotNamerApp(rumps.App):

    def __init__(self) -> None:
        super().__init__(
            name="Screenshot Namer",
            title="\U0001f4f7",  # camera emoji as placeholder icon
            quit_button=None,  # we add our own at the bottom
        )

        self.cfg = config.load()
        self._today_count = 0
        self._today_date = date.today()
        self._last_name: str | None = None
        self._known_files: set[str] = set()
        self._pending: dict[str, int] = {}  # path -> stable size-check count
        self._pending_sizes: dict[str, int] = {}  # path -> last known size
        self._client: anthropic.Anthropic | None = None

        # Build menu
        self._watching_item = rumps.MenuItem(
            "Watching: ON" if self.cfg["watching_enabled"] else "Watching: OFF",
            callback=self._toggle_watching,
        )
        self._watching_item.state = self.cfg["watching_enabled"]

        self._last_item = rumps.MenuItem("Last: —")
        self._count_item = rumps.MenuItem("Today: 0 processed")

        self._login_item = rumps.MenuItem(
            "Start at Login",
            callback=self._toggle_login,
        )
        self._login_item.state = self.cfg["start_at_login"]

        self._notify_item = rumps.MenuItem(
            "Notifications",
            callback=self._toggle_notifications,
        )
        self._notify_item.state = self.cfg["notifications"]

        self.menu = [
            self._watching_item,
            None,
            self._last_item,
            self._count_item,
            None,
            rumps.MenuItem("Process All Now...", callback=self._process_all),
            rumps.MenuItem("Open Output Folder", callback=self._open_output),
            None,
            self._login_item,
            self._notify_item,
            None,
            rumps.MenuItem("Quit Screenshot Namer", callback=self._quit),
        ]

        # Snapshot existing files so we only process NEW ones
        self._snapshot_existing()

    # ── Lifecycle ──────────────────────────────────────────────

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def _snapshot_existing(self) -> None:
        """Record all current screenshot files so we skip them."""
        watch_dir = Path(self.cfg["watch_dir"])
        if watch_dir.is_dir():
            for f in watch_dir.iterdir():
                if f.is_file() and f.suffix.lower() in SCREENSHOT_EXTENSIONS:
                    self._known_files.add(str(f))

    # ── Polling Timer ──────────────────────────────────────────

    @rumps.timer(POLL_INTERVAL)
    def _poll(self, _timer) -> None:
        """Check for new screenshot files in the watch directory."""
        if not self.cfg["watching_enabled"]:
            return

        # Reset daily counter at midnight
        today = date.today()
        if today != self._today_date:
            self._today_date = today
            self._today_count = 0
            self._count_item.title = "Today: 0 processed"

        watch_dir = Path(self.cfg["watch_dir"])
        if not watch_dir.is_dir():
            return

        for f in watch_dir.iterdir():
            path_str = str(f)
            if (
                f.is_file()
                and f.suffix.lower() in SCREENSHOT_EXTENSIONS
                and path_str not in self._known_files
            ):
                # New file — check if it's stable (done writing)
                try:
                    current_size = f.stat().st_size
                except OSError:
                    continue

                if current_size == 0:
                    continue

                prev_size = self._pending_sizes.get(path_str)
                if prev_size is None or current_size != prev_size:
                    # Size changed or first seen — reset counter
                    self._pending[path_str] = 0
                    self._pending_sizes[path_str] = current_size
                    continue

                # Size is stable — increment counter
                self._pending[path_str] = self._pending.get(path_str, 0) + 1
                if self._pending[path_str] >= SETTLE_CHECKS:
                    # File is stable, process it
                    self._pending.pop(path_str, None)
                    self._pending_sizes.pop(path_str, None)
                    self._known_files.add(path_str)
                    self._process_file(f)

    # ── Processing ─────────────────────────────────────────────

    def _process_file(self, file_path: Path) -> None:
        """Analyze and move a single screenshot."""
        log.info(f"Processing: {file_path.name}")
        output_dir = Path(self.cfg["output_dir"])

        try:
            result = analyze_screenshot(file_path, client=self._get_client())
        except Exception as e:
            log.error(f"Analysis failed for {file_path.name}: {e}")
            if self.cfg["notifications"]:
                rumps.notification(
                    title="Screenshot Namer",
                    subtitle="Analysis failed",
                    message=f"{file_path.name}: {e}",
                )
            return

        dest = move_screenshot(file_path, result, output_dir)

        # Update state
        self._today_count += 1
        self._last_name = result.filename_slug
        self._last_item.title = f"Last: {result.filename_slug}"
        self._count_item.title = f"Today: {self._today_count} processed"

        log.info(f"  → {dest} ({result.category}, {result.confidence:.0%})")

        if self.cfg["notifications"]:
            rumps.notification(
                title="Screenshot Namer",
                subtitle=f"→ {result.category}/",
                message=result.filename_slug,
            )

    # ── Menu Callbacks ─────────────────────────────────────────

    def _toggle_watching(self, sender) -> None:
        sender.state = not sender.state
        self.cfg["watching_enabled"] = bool(sender.state)
        sender.title = "Watching: ON" if sender.state else "Watching: OFF"
        self.title = "\U0001f4f7" if sender.state else "\U0001f4f7\u20e0"  # camera + combining circle
        config.save(self.cfg)

    def _toggle_login(self, sender) -> None:
        sender.state = not sender.state
        self.cfg["start_at_login"] = bool(sender.state)
        config.save(self.cfg)

        if sender.state:
            self._install_launch_agent()
        else:
            self._remove_launch_agent()

    def _toggle_notifications(self, sender) -> None:
        sender.state = not sender.state
        self.cfg["notifications"] = bool(sender.state)
        config.save(self.cfg)

    def _process_all(self, _sender) -> None:
        """Batch-process all existing screenshots in the watch directory."""
        watch_dir = Path(self.cfg["watch_dir"])
        if not watch_dir.is_dir():
            rumps.notification("Screenshot Namer", "Error", f"Watch directory not found: {watch_dir}")
            return

        files = [
            f for f in watch_dir.iterdir()
            if f.is_file() and f.suffix.lower() in SCREENSHOT_EXTENSIONS
        ]

        if not files:
            rumps.notification("Screenshot Namer", "Nothing to do", "No screenshots found.")
            return

        rumps.notification("Screenshot Namer", "Batch processing", f"Processing {len(files)} screenshots...")

        for f in files:
            self._known_files.add(str(f))
            self._process_file(f)

        rumps.notification("Screenshot Namer", "Done", f"Processed {len(files)} screenshots.")

    def _open_output(self, _sender) -> None:
        output_dir = Path(self.cfg["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(output_dir)])

    def _quit(self, _sender) -> None:
        rumps.quit_application()

    # ── LaunchAgent Management ─────────────────────────────────

    def _get_app_executable(self) -> str:
        """Get the path to run this app."""
        # When running from source, use the venv python + app.py
        app_dir = Path(__file__).resolve().parent
        venv_python = app_dir / ".venv" / "bin" / "python"
        if venv_python.exists():
            return str(venv_python)
        return sys.executable

    def _install_launch_agent(self) -> None:
        app_dir = Path(__file__).resolve().parent
        python_path = self._get_app_executable()
        app_script = str(app_dir / "app.py")

        plist_data = {
            "Label": LAUNCHAGENT_LABEL,
            "ProgramArguments": [python_path, app_script],
            "RunAtLoad": True,
            "KeepAlive": True,
            "WorkingDirectory": str(app_dir),
            "EnvironmentVariables": {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin"),
            },
            "StandardOutPath": str(app_dir / "logs" / "stdout.log"),
            "StandardErrorPath": str(app_dir / "logs" / "stderr.log"),
        }

        # Create logs directory
        (app_dir / "logs").mkdir(exist_ok=True)

        LAUNCHAGENT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LAUNCHAGENT_PATH, "wb") as f:
            plistlib.dump(plist_data, f)

        log.info(f"LaunchAgent installed: {LAUNCHAGENT_PATH}")

    def _remove_launch_agent(self) -> None:
        if LAUNCHAGENT_PATH.exists():
            # Unload before removing
            subprocess.run(
                ["launchctl", "unload", str(LAUNCHAGENT_PATH)],
                capture_output=True,
            )
            LAUNCHAGENT_PATH.unlink()
            log.info("LaunchAgent removed.")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    # Verify API key is available before starting
    load_dotenv(override=True)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your-key-here":
        rumps.notification(
            "Screenshot Namer",
            "Setup required",
            "Set ANTHROPIC_API_KEY in .env file.",
        )
        log.error("ANTHROPIC_API_KEY not configured. Add it to .env file.")
        # Still start the app so user can see it and configure
        # It will show errors when trying to process

    app = ScreenshotNamerApp()
    app.run()


if __name__ == "__main__":
    main()
