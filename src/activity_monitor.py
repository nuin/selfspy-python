"""
Activity monitoring implementation
"""

import asyncio
import logging
import platform
from datetime import datetime
from typing import Any, Dict, Optional

import Quartz
import structlog
from pynput import mouse
from rich.layout import Layout
from rich.live import Live
from rich.table import Table

from .activity_store import ActivityStore
from .config import Settings
from .platform.input_tracker import InputTracker

logger = structlog.get_logger()


class ActivityMonitor:
    """Activity monitor implementation"""

    def __init__(self, settings: Settings, store: "ActivityStore", debug: bool = False):
        self.settings = settings
        self.store = store
        self.current_window: Optional[Dict[str, str]] = None
        self.buffer: list[Dict[str, Any]] = []
        self.last_activity = datetime.now()
        self.running = False

        # Initialize stats
        self.stats = {
            "keystrokes": 0,
            "clicks": 0,
            "windows": 0,
            "last_window": None,
            "start_time": datetime.now(),
        }
        self.live_display = None

        # Configure logging
        log_level = logging.DEBUG if debug else logging.INFO
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(log_level)
        )

        # Initialize platform-specific trackers
        try:
            if platform.system() == "Darwin":
                from .platform.darwin import MacOSWindowTracker, MacOSInputTracker

                self.window_tracker = MacOSWindowTracker()
                self.input_tracker = MacOSInputTracker(
                    on_key_press=self._on_key_press,
                    on_key_release=self._on_key_release,
                    on_mouse_move=self._on_mouse_move,
                    on_mouse_click=self._on_mouse_click,
                    on_scroll=self._on_scroll,
                )
            else:
                from .platform.fallback import FallbackWindowTracker

                self.window_tracker = FallbackWindowTracker()
                self.input_tracker = InputTracker(
                    on_key_press=self._on_key_press,
                    on_key_release=self._on_key_release,
                    on_mouse_move=self._on_mouse_move,
                    on_mouse_click=self._on_mouse_click,
                    on_scroll=self._on_scroll,
                )
                logger.warning(
                    f"Platform {platform.system()} has limited tracking support"
                )
        except Exception as e:
            logger.warning(f"Using fallback trackers: {str(e)}")
            from .platform.fallback import FallbackWindowTracker

            self.window_tracker = FallbackWindowTracker()
            self.input_tracker = InputTracker(
                on_key_press=self._on_key_press,
                on_key_release=self._on_key_release,
                on_mouse_move=self._on_mouse_move,
                on_mouse_click=self._on_mouse_click,
                on_scroll=self._on_scroll,
            )

    def _generate_display(self) -> Layout:
        """Generate live display layout"""
        layout = Layout()

        # Activity summary table
        summary = Table(title="Activity Summary")
        summary.add_column("Metric", style="cyan")
        summary.add_column("Value", style="green")

        duration = datetime.now() - self.stats["start_time"]

        summary.add_row(
            "Session Duration",
            f"{duration.seconds // 3600}h {(duration.seconds % 3600) // 60}m",
        )
        summary.add_row("Keystrokes", str(self.stats["keystrokes"]))
        summary.add_row("Clicks", str(self.stats["clicks"]))
        summary.add_row("Windows", str(self.stats["windows"]))
        if self.stats["last_window"]:
            summary.add_row(
                "Current Window",
                f"{self.stats['last_window']['process']} - {self.stats['last_window']['title']}",
            )

        layout.update(summary)
        return layout

    async def start(self):
        """Start monitoring asynchronously"""
        logger.info("Starting activity monitor...")

        if platform.system() == "Darwin":
            try:
                from ApplicationServices import AXIsProcessTrusted
                if not AXIsProcessTrusted():
                    logger.error("Accessibility permissions missing")
                    raise PermissionError(
                        "Accessibility permissions still missing. Please restart your terminal after granting permissions."
                    )
            except ImportError:
                logger.warning("PyObjC not available - skipping permission check")

        self.running = True

        # Start input tracking
        if not self.input_tracker.start():
            raise RuntimeError("Failed to start input tracking")

        with Live(self._generate_display(), refresh_per_second=1) as live:
            self.live_display = live
            while self.running:
                try:
                    await self._check_active_window()
                    await self._flush_buffer()
                    if self.live_display:
                        self.live_display.update(self._generate_display())
                    await asyncio.sleep(self.settings.active_window_check_interval)
                except Exception as e:
                    logger.error("Monitor error", error=str(e))

    async def stop(self):
        """Stop monitoring"""
        logger.info("Stopping activity monitor...")
        self.running = False
        self.input_tracker.stop()
        await self._flush_buffer()

    def _on_key_press(self, key):
        """Handle key press events"""
        try:
            char = key.char if hasattr(key, "char") else str(key)
            self.stats["keystrokes"] += 1
            self.buffer.append({"type": "key", "key": char, "time": datetime.now()})
            self.last_activity = datetime.now()
        except Exception as e:
            logger.error("Key press error", error=str(e))

    def _on_key_release(self, key):
        """Handle key release events"""
        pass

    def _on_mouse_move(self, x: int, y: int):
        """Handle mouse movement"""
        self.last_activity = datetime.now()

    def _on_mouse_click(self, x: int, y: int, button: mouse.Button, pressed: bool):
        """Handle mouse clicks"""
        try:
            if pressed:
                button_num = 1 if button == mouse.Button.left else 3
                self.stats["clicks"] += 1
                asyncio.create_task(self.store.store_click(button_num, x, y))
                self.last_activity = datetime.now()
        except Exception as e:
            logger.error("Mouse click error", error=str(e))

    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        """Handle scroll events"""
        try:
            button_num = 4 if dy > 0 else 5
            asyncio.create_task(self.store.store_click(button_num, x, y))
            self.last_activity = datetime.now()
        except Exception as e:
            logger.error("Scroll error", error=str(e))

    async def _flush_buffer(self):
        """Flush keystroke buffer to storage"""
        if (
            self.buffer
            and (datetime.now() - self.last_activity).seconds
            > self.settings.keystroke_buffer_timeout
        ):
            text = "".join(
                item["key"] for item in self.buffer if isinstance(item.get("key"), str)
            )
            if text:
                await self.store.store_keys(text)
                self.buffer.clear()
                self.last_activity = datetime.now()

    async def _check_active_window(self):
        """Check current active window"""
        try:
            window_info = await self.window_tracker.get_active_window()
            if window_info != self.current_window:
                self.current_window = window_info
                self.stats["windows"] += 1
                self.stats["last_window"] = window_info
                await self.store.update_window_info(
                    window_info["process"], window_info["title"], window_info.get("bundle", "")
                )
        except Exception as e:
            logger.error("Window check error", error=str(e))
