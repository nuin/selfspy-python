"""
Activity monitoring implementation
"""

import asyncio
import logging
import platform
from asyncio import Queue
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from pynput import mouse
from rich.layout import Layout
from rich.live import Live
from rich.table import Table

from .activity_store import ActivityStore
from .config import Settings
from .platform.input_tracker import InputTracker
from .terminal_tracker import TerminalTracker

logger = structlog.get_logger()


class ActivityMonitor:
    """Activity monitor implementation"""

    def __init__(self, settings: Settings, store: "ActivityStore", debug: bool = False):
        self.settings = settings
        self.store = store
        self.current_window: Optional[Dict[str, str]] = None
        # Use asyncio Queue for thread-safe buffer
        self.buffer: Queue = Queue(maxsize=1000)  # Limit queue size to prevent memory issues
        self.last_activity = datetime.now()
        self.running = False
        self._shutdown_event = asyncio.Event()

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

        # Initialize terminal tracker
        self.terminal_tracker = TerminalTracker(store)

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

        # Initialize the activity store
        await self.store.initialize()
        logger.info("Activity store initialized")

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

        # Start terminal tracking in background
        asyncio.create_task(self.terminal_tracker.start_tracking())

        try:
            with Live(self._generate_display(), refresh_per_second=1) as live:
                self.live_display = live
                while self.running and not self._shutdown_event.is_set():
                    try:
                        await self._check_active_window()
                        await self._flush_buffer()
                        if self.live_display:
                            self.live_display.update(self._generate_display())
                        await asyncio.sleep(self.settings.active_window_check_interval)
                    except Exception as e:
                        logger.error("Monitor error", error=str(e))
        finally:
            # Ensure cleanup happens
            await self._cleanup()

    async def stop(self):
        """Stop monitoring gracefully"""
        logger.info("Stopping activity monitor...")
        self.running = False
        self._shutdown_event.set()

    async def _cleanup(self):
        """Cleanup resources and flush remaining data"""
        logger.info("Cleaning up activity monitor...")

        # Stop input tracking
        if hasattr(self, 'input_tracker'):
            self.input_tracker.stop()

        # Flush any remaining buffered data
        await self._flush_buffer(force=True)

        # Close database connection
        if hasattr(self, 'store'):
            await self.store.close()

        logger.info("Activity monitor cleanup complete")

    def _on_key_press(self, key):
        """Handle key press events"""
        try:
            char = key.char if hasattr(key, "char") else str(key)
            self.stats["keystrokes"] += 1
            # Use put_nowait for thread-safe queue access from pynput thread
            try:
                self.buffer.put_nowait({"type": "key", "key": char, "time": datetime.now()})
            except asyncio.QueueFull:
                logger.warning("Buffer queue full, dropping keystroke event")
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
                # Buffer click for async storage using thread-safe queue
                try:
                    self.buffer.put_nowait({
                        "type": "click",
                        "button": button_num,
                        "x": x,
                        "y": y,
                        "time": datetime.now()
                    })
                except asyncio.QueueFull:
                    logger.warning("Buffer queue full, dropping click event")
                self.last_activity = datetime.now()
        except Exception as e:
            logger.error("Mouse click error", error=str(e))

    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        """Handle scroll events"""
        try:
            button_num = 4 if dy > 0 else 5
            # Buffer scroll event for async storage using thread-safe queue
            try:
                self.buffer.put_nowait({
                    "type": "click",
                    "button": button_num,
                    "x": x,
                    "y": y,
                    "time": datetime.now()
                })
            except asyncio.QueueFull:
                logger.warning("Buffer queue full, dropping scroll event")
            self.last_activity = datetime.now()
        except Exception as e:
            logger.error("Scroll error", error=str(e))

    async def _flush_buffer(self, force: bool = False):
        """Flush keystroke and click buffer to storage"""
        if self.buffer.empty():
            return

        current_time = datetime.now()
        time_since_activity = (current_time - self.last_activity).seconds

        # Check if we should flush
        should_flush = (
            force or
            time_since_activity > self.settings.keystroke_buffer_timeout or
            self.buffer.qsize() > 50  # Force flush if buffer gets too large
        )

        if should_flush:
            # Collect all items from queue
            items = []
            while not self.buffer.empty():
                try:
                    items.append(self.buffer.get_nowait())
                except asyncio.QueueEmpty:
                    break

            # Process keystrokes
            text = "".join(
                item["key"] for item in items if item.get("type") == "key" and isinstance(item.get("key"), str)
            )
            if text:
                try:
                    await self.store.store_keys(text)
                except Exception as e:
                    logger.error("Error storing keystrokes", error=str(e))

            # Process clicks
            clicks = [item for item in items if item.get("type") == "click"]
            if clicks:
                logger.debug(f"Flushing {len(clicks)} clicks to database")
            for click in clicks:
                try:
                    await self.store.store_click(click["button"], click["x"], click["y"])
                except Exception as e:
                    logger.error("Error storing click", error=str(e))

            self.last_activity = current_time

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
