"""
Activity monitoring implementation
"""

import asyncio
import logging
import platform
from asyncio import Queue
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any

import structlog
from pynput import mouse

from .config import Settings
from .storage import Store
from .tracking import TerminalTracker
from .tracking.platform.input_tracker import InputTracker

logger = structlog.get_logger()


class ActivityMonitor:
    """Activity monitor implementation"""

    def __init__(self, settings: Settings, store: "Store", debug: bool = False):
        self.settings = settings
        self.store = store
        self.current_window: dict[str, str] | None = None
        # Use asyncio Queue for buffering events
        self.buffer: Queue = Queue(
            maxsize=1000
        )  # Limit queue size to prevent memory issues
        self.last_activity = datetime.now()
        self.running = False
        self._shutdown_event = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = (
            None  # Set when start() is called
        )

        # Initialize stats
        self.stats = {
            "keystrokes": 0,
            "clicks": 0,
            "windows": 0,
            "last_window": None,
            "start_time": datetime.now(),
        }
        self.live_display = None

        # Rich metrics tracking
        self.keystroke_history = deque(maxlen=60)  # Last 60 seconds
        self.click_history = deque(maxlen=60)
        self.app_usage = defaultdict(
            lambda: {"time": 0, "keys": 0, "clicks": 0, "windows": 0}
        )
        self.last_metric_time = datetime.now()
        self.current_second_keys = 0
        self.current_second_clicks = 0

        # Idle detection (3 minutes without activity = idle)
        self.idle_threshold = timedelta(minutes=3)
        self.last_activity_time = datetime.now()
        self.is_idle = False
        self.idle_start_time: datetime | None = None
        self.session_active_seconds = 0
        self.session_idle_seconds = 0

        # Historical comparison data
        self.yesterday_data: dict[str, Any] | None = None
        self.yesterday_fetched = False

        # Configure logging
        log_level = logging.DEBUG if debug else logging.INFO
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(log_level)
        )

        # Initialize terminal tracker
        self.terminal_tracker = TerminalTracker(store)

        # Initialize platform-specific trackers
        self._init_platform_trackers()

    def _threadsafe_buffer_put(self, item: dict[str, Any]) -> None:
        """Thread-safe method to put items on the buffer queue from pynput threads"""
        if self._loop is None:
            return
        try:
            # Use call_soon_threadsafe to safely schedule the put from another thread
            self._loop.call_soon_threadsafe(self._buffer_put_nowait, item)
        except RuntimeError:
            # Loop may be closed during shutdown
            pass

    def _buffer_put_nowait(self, item: dict[str, Any]) -> None:
        """Helper called on the event loop thread to actually put the item"""
        try:
            self.buffer.put_nowait(item)
        except asyncio.QueueFull:
            logger.warning("Buffer queue full, dropping event")

    def _init_platform_trackers(self) -> None:
        """Initialize platform-specific trackers"""
        try:
            if platform.system() == "Darwin":
                from .tracking.platform.darwin import (
                    MacOSInputTracker,
                    MacOSWindowTracker,
                )

                self.window_tracker = MacOSWindowTracker()
                self.input_tracker = MacOSInputTracker(
                    on_key_press=self._on_key_press,
                    on_key_release=self._on_key_release,
                    on_mouse_move=self._on_mouse_move,
                    on_mouse_click=self._on_mouse_click,
                    on_scroll=self._on_scroll,
                )
            else:
                from .tracking.platform.fallback import FallbackWindowTracker

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
            logger.warning(f"Using fallback trackers: {e!s}")
            from .tracking.platform.fallback import FallbackWindowTracker

            self.window_tracker = FallbackWindowTracker()
            self.input_tracker = InputTracker(
                on_key_press=self._on_key_press,
                on_key_release=self._on_key_release,
                on_mouse_move=self._on_mouse_move,
                on_mouse_click=self._on_mouse_click,
                on_scroll=self._on_scroll,
            )

    def _update_metrics(self):
        """Update per-second metrics for charts"""
        now = datetime.now()
        if (now - self.last_metric_time).total_seconds() >= 1.0:
            self.keystroke_history.append(self.current_second_keys)
            self.click_history.append(self.current_second_clicks)
            self.current_second_keys = 0
            self.current_second_clicks = 0
            self.last_metric_time = now

    def get_current_state(self) -> dict[str, Any]:
        """Get current monitoring state for TUI display.

        Returns a dictionary with all the data the TUI needs to display.
        """
        duration = datetime.now() - self.stats["start_time"]
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        seconds = duration.seconds % 60
        session_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Calculate rates
        duration_secs = duration.total_seconds()
        keys_per_min = (
            int((self.stats["keystrokes"] / duration_secs) * 60)
            if duration_secs > 0
            else 0
        )
        clicks_per_min = (
            int((self.stats["clicks"] / duration_secs) * 60) if duration_secs > 0 else 0
        )

        # Calculate active/idle percentages
        total_seconds = self.session_active_seconds + self.session_idle_seconds
        active_percent = (
            (self.session_active_seconds / total_seconds * 100)
            if total_seconds > 0
            else 100
        )
        idle_percent = 100 - active_percent

        # Format active/idle time
        active_hours = self.session_active_seconds // 3600
        active_mins = (self.session_active_seconds % 3600) // 60
        active_secs = self.session_active_seconds % 60
        active_time = f"{active_hours:02d}:{active_mins:02d}:{active_secs:02d}"

        idle_hours = self.session_idle_seconds // 3600
        idle_mins = (self.session_idle_seconds % 3600) // 60
        idle_secs = self.session_idle_seconds % 60
        idle_time = f"{idle_hours:02d}:{idle_mins:02d}:{idle_secs:02d}"

        # Current window info
        current_window = ""
        if self.stats.get("last_window"):
            window = self.stats["last_window"]
            current_window = f"{window.get('process', 'Unknown')} - {window.get('title', 'Unknown')[:50]}"

        # Get app data for Apps tab
        apps_data = self.get_apps_data()

        # Yesterday comparison
        yesterday_diff = None
        more_active = True
        if self.yesterday_data:
            yesterday_total = (
                self.yesterday_data["keystrokes"] + self.yesterday_data["clicks"]
            )
            if yesterday_total > 0:
                current_total = self.stats["keystrokes"] + self.stats["clicks"]
                diff = current_total - yesterday_total
                pct_change = (diff / yesterday_total) * 100
                yesterday_diff = abs(pct_change)
                more_active = diff >= 0

        return {
            # Live tab data
            "keystrokes": self.stats["keystrokes"],
            "clicks": self.stats["clicks"],
            "keys_per_min": keys_per_min,
            "clicks_per_min": clicks_per_min,
            "current_window": current_window,
            "status": "IDLE" if self.is_idle else "ACTIVE",
            "session_duration": session_duration,
            "keystroke_history": list(self.keystroke_history),
            "click_history": list(self.click_history),
            # Summary tab data
            "active_time": active_time,
            "active_percent": active_percent,
            "idle_time": idle_time,
            "idle_percent": idle_percent,
            "windows_switched": self.stats["windows"],
            "yesterday_diff": yesterday_diff,
            "more_active": more_active,
            # Apps tab data
            "apps": apps_data,
        }

    def get_apps_data(self) -> list[dict[str, Any]]:
        """Get application activity data for Apps tab.

        Returns list of app data sorted by activity.
        """
        # Sort apps by activity
        sorted_apps = sorted(
            self.app_usage.items(),
            key=lambda x: x[1]["keys"] + x[1]["clicks"],
            reverse=True,
        )

        if not sorted_apps:
            return []

        # Calculate total for percentages
        total_activity = sum(app["keys"] + app["clicks"] for _, app in sorted_apps)

        apps_data = []
        for app_name, metrics in sorted_apps[:20]:  # Top 20 apps
            activity = metrics["keys"] + metrics["clicks"]
            percentage = (activity / total_activity * 100) if total_activity > 0 else 0
            apps_data.append(
                {
                    "name": app_name,
                    "keystrokes": metrics["keys"],
                    "clicks": metrics["clicks"],
                    "activity_percent": percentage,
                }
            )

        return apps_data

    async def _fetch_yesterday_data(self):
        """Fetch yesterday's session data for comparison"""
        if self.yesterday_fetched:
            return

        try:
            from datetime import date

            from sqlalchemy import select

            from .storage import Session

            yesterday = date.today() - timedelta(days=1)
            yesterday_start = datetime.combine(yesterday, datetime.min.time())
            yesterday_end = datetime.combine(yesterday, datetime.max.time())

            async with self.store.async_session() as session:
                # Get all yesterday's sessions
                sessions_query = select(Session).where(
                    Session.start_time >= yesterday_start,
                    Session.start_time <= yesterday_end,
                )
                result = await session.execute(sessions_query)
                sessions = result.scalars().all()

                if sessions:
                    # Aggregate data from all sessions
                    total_keystrokes = sum(s.total_keystrokes for s in sessions)
                    total_clicks = sum(s.total_clicks for s in sessions)
                    total_active = sum(s.active_seconds for s in sessions)
                    total_idle = sum(s.idle_seconds for s in sessions)

                    self.yesterday_data = {
                        "keystrokes": total_keystrokes,
                        "clicks": total_clicks,
                        "active_seconds": total_active,
                        "idle_seconds": total_idle,
                        "session_count": len(sessions),
                    }
                    logger.info(f"Fetched yesterday's data: {len(sessions)} sessions")

            self.yesterday_fetched = True
        except Exception as e:
            logger.warning(f"Could not fetch yesterday's data: {e}")
            self.yesterday_fetched = True  # Don't keep trying

    async def start(self, use_tui: bool = True):
        """Start monitoring asynchronously.

        Args:
            use_tui: If True, starts the Textual TUI. If False, runs headless.
        """
        logger.info("Starting activity monitor...")

        # Store reference to event loop for thread-safe queue access
        self._loop = asyncio.get_running_loop()

        # Initialize the activity store
        await self.store.initialize()
        logger.info("Activity store initialized")

        # Start new monitoring session
        await self.store.start_session()
        logger.info(f"Started session {self.store.current_session_id}")

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

        # Start idle detection task
        asyncio.create_task(self._monitor_idle_state())

        # Fetch yesterday's data for comparison (async background task)
        asyncio.create_task(self._fetch_yesterday_data())

        try:
            if use_tui:
                await self._run_with_tui()
            else:
                await self._run_headless()
        finally:
            # Ensure cleanup happens
            await self._cleanup()

    async def _run_with_tui(self):
        """Run with the Textual TUI (delegates to tui.runner)."""
        from .tui.runner import run_tui

        await run_tui(self)

    async def _run_headless(self):
        """Run without any display (headless mode)."""
        logger.info("Running in headless mode")
        while self.running and not self._shutdown_event.is_set():
            try:
                await self._check_active_window()
                await self._flush_buffer()
                self._update_metrics()
                await asyncio.sleep(self.settings.active_window_check_interval)
            except Exception as e:
                logger.error("Monitor error", error=str(e))

    async def stop(self):
        """Stop monitoring gracefully"""
        logger.info("Stopping activity monitor...")
        self.running = False
        self._shutdown_event.set()

    async def _monitor_idle_state(self):
        """Monitor idle state and update session metrics"""
        while self.running:
            now = datetime.now()
            time_since_activity = now - self.last_activity_time

            # Check if we've gone idle
            if not self.is_idle and time_since_activity > self.idle_threshold:
                self.is_idle = True
                self.idle_start_time = self.last_activity_time + self.idle_threshold
                logger.info(
                    f"User went idle after {self.idle_threshold.total_seconds()}s of inactivity"
                )

            # Check if we've resumed activity
            elif self.is_idle and time_since_activity <= self.idle_threshold:
                self.is_idle = False
                if self.idle_start_time:
                    idle_duration = int((now - self.idle_start_time).total_seconds())
                    self.session_idle_seconds += idle_duration
                    # Update session metrics
                    await self.store.update_session_metrics(idle_seconds=idle_duration)
                    logger.info(f"User resumed activity after {idle_duration}s idle")
                self.idle_start_time = None

            # Update active time if not idle
            if not self.is_idle:
                self.session_active_seconds += 1
                await self.store.update_session_metrics(active_seconds=1)

            await asyncio.sleep(1)

    async def _cleanup(self):
        """Cleanup resources and flush remaining data"""
        logger.info("Cleaning up activity monitor...")

        # Stop input tracking
        if hasattr(self, "input_tracker"):
            self.input_tracker.stop()

        # Flush any remaining buffered data
        await self._flush_buffer(force=True)

        # Update final session metrics
        if self.is_idle and self.idle_start_time:
            idle_duration = int((datetime.now() - self.idle_start_time).total_seconds())
            await self.store.update_session_metrics(idle_seconds=idle_duration)

        # Close database connection (this will end the session)
        if hasattr(self, "store"):
            await self.store.close()

        logger.info("Activity monitor cleanup complete")

    def _on_key_press(self, key):
        """Handle key press events"""
        try:
            # Reset idle state
            self.last_activity_time = datetime.now()

            char = key.char if hasattr(key, "char") else str(key)
            self.stats["keystrokes"] += 1
            self.current_second_keys += 1

            # Track per-app metrics
            if self.stats.get("last_window"):
                app_name = self.stats["last_window"].get("process", "Unknown")
                self.app_usage[app_name]["keys"] += 1

            # Use thread-safe method to put on queue from pynput thread
            self._threadsafe_buffer_put(
                {"type": "key", "key": char, "time": datetime.now()}
            )
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
                # Reset idle state
                self.last_activity_time = datetime.now()

                button_num = 1 if button == mouse.Button.left else 3
                self.stats["clicks"] += 1
                self.current_second_clicks += 1

                # Track per-app metrics
                if self.stats.get("last_window"):
                    app_name = self.stats["last_window"].get("process", "Unknown")
                    self.app_usage[app_name]["clicks"] += 1

                # Use thread-safe method to put on queue from pynput thread
                self._threadsafe_buffer_put(
                    {
                        "type": "click",
                        "button": button_num,
                        "x": x,
                        "y": y,
                        "time": datetime.now(),
                    }
                )
                self.last_activity = datetime.now()
        except Exception as e:
            logger.error("Mouse click error", error=str(e))

    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        """Handle scroll events"""
        try:
            button_num = 4 if dy > 0 else 5
            # Use thread-safe method to put on queue from pynput thread
            self._threadsafe_buffer_put(
                {
                    "type": "click",
                    "button": button_num,
                    "x": x,
                    "y": y,
                    "time": datetime.now(),
                }
            )
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
            force
            or time_since_activity > self.settings.keystroke_buffer_timeout
            or self.buffer.qsize() > 50  # Force flush if buffer gets too large
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
                item["key"]
                for item in items
                if item.get("type") == "key" and isinstance(item.get("key"), str)
            )
            keystroke_count = len(text)
            if text:
                try:
                    await self.store.store_keys(text)
                    # Update session metrics with keystroke count
                    await self.store.update_session_metrics(keystrokes=keystroke_count)
                except Exception as e:
                    logger.error("Error storing keystrokes", error=str(e))

            # Process clicks
            clicks = [item for item in items if item.get("type") == "click"]
            click_count = len(clicks)
            if clicks:
                logger.debug(f"Flushing {len(clicks)} clicks to database")
            for click in clicks:
                try:
                    await self.store.store_click(
                        click["button"], click["x"], click["y"]
                    )
                except Exception as e:
                    logger.error("Error storing click", error=str(e))

            # Update session metrics with click count
            if click_count > 0:
                try:
                    await self.store.update_session_metrics(clicks=click_count)
                except Exception as e:
                    logger.error("Error updating session click metrics", error=str(e))

            self.last_activity = current_time

    async def _check_active_window(self):
        """Check current active window"""
        try:
            window_info = await self.window_tracker.get_active_window()
            if window_info != self.current_window:
                self.current_window = window_info
                self.stats["windows"] += 1
                self.stats["last_window"] = window_info

                # Track per-app window count
                app_name = window_info.get("process", "Unknown")
                self.app_usage[app_name]["windows"] += 1

                await self.store.update_window_info(
                    window_info["process"],
                    window_info["title"],
                    window_info.get("bundle", ""),
                )
        except Exception as e:
            logger.error("Window check error", error=str(e))
