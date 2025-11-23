"""
Activity monitoring implementation
"""

import asyncio
import logging
import platform
from asyncio import Queue
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import structlog
from pynput import mouse
from rich.align import Align
from rich.console import Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

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

        # Rich metrics tracking
        self.keystroke_history = deque(maxlen=60)  # Last 60 seconds
        self.click_history = deque(maxlen=60)
        self.app_usage = defaultdict(lambda: {"time": 0, "keys": 0, "clicks": 0, "windows": 0})
        self.last_metric_time = datetime.now()
        self.current_second_keys = 0
        self.current_second_clicks = 0

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

    def _update_metrics(self):
        """Update per-second metrics for charts"""
        now = datetime.now()
        if (now - self.last_metric_time).total_seconds() >= 1.0:
            self.keystroke_history.append(self.current_second_keys)
            self.click_history.append(self.current_second_clicks)
            self.current_second_keys = 0
            self.current_second_clicks = 0
            self.last_metric_time = now

    def _create_sparkline(self, data: deque, max_val: int = None) -> str:
        """Create a sparkline chart from data"""
        if not data:
            return "▁" * 20

        bars = "▁▂▃▄▅▆▇█"
        max_value = max_val or max(data) if max(data) > 0 else 1

        # Take last 40 data points for display
        display_data = list(data)[-40:]
        sparkline = ""
        for value in display_data:
            index = min(int((value / max_value) * (len(bars) - 1)), len(bars) - 1)
            sparkline += bars[index]

        return sparkline

    def _generate_header(self) -> Panel:
        """Generate header panel with session info"""
        duration = datetime.now() - self.stats["start_time"]
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        seconds = duration.seconds % 60

        grid = Table.grid(padding=1)
        grid.add_column(justify="left", style="cyan bold")
        grid.add_column(justify="center")
        grid.add_column(justify="right", style="magenta bold")

        grid.add_row(
            f"⏱  Session: {hours:02d}h {minutes:02d}m {seconds:02d}s",
            Text("SELFSPY ACTIVITY MONITOR", style="bold white"),
            f"Buffer: {self.buffer.qsize()}/1000"
        )

        return Panel(grid, style="bold blue")

    def _generate_metrics_panel(self) -> Panel:
        """Generate real-time metrics with sparklines"""
        # Update metrics
        self._update_metrics()

        table = Table.grid(padding=(0, 2))
        table.add_column("Label", style="cyan")
        table.add_column("Value", style="green bold", justify="right")
        table.add_column("Chart", style="yellow")
        table.add_column("Rate", style="dim")

        # Calculate rates
        duration = (datetime.now() - self.stats["start_time"]).total_seconds()
        keys_per_min = int((self.stats["keystrokes"] / duration) * 60) if duration > 0 else 0
        clicks_per_min = int((self.stats["clicks"] / duration) * 60) if duration > 0 else 0

        # Recent activity (last 60 seconds)
        recent_keys = sum(self.keystroke_history) if self.keystroke_history else 0
        recent_clicks = sum(self.click_history) if self.click_history else 0

        table.add_row(
            "⌨  Keystrokes",
            f"{self.stats['keystrokes']:,}",
            self._create_sparkline(self.keystroke_history, max_val=100),
            f"{keys_per_min}/min"
        )
        table.add_row(
            "🖱  Clicks",
            f"{self.stats['clicks']:,}",
            self._create_sparkline(self.click_history, max_val=50),
            f"{clicks_per_min}/min"
        )
        table.add_row(
            "🪟  Windows",
            f"{self.stats['windows']:,}",
            "",
            f"{len(self.app_usage)} apps"
        )
        table.add_row(
            "🔄  Recent Activity",
            f"{recent_keys + recent_clicks:,}",
            "",
            "last 60s"
        )

        return Panel(table, title="[bold]📊 Real-time Metrics[/bold]", border_style="green")

    def _generate_top_apps_panel(self) -> Panel:
        """Generate top applications panel"""
        # Sort apps by keystroke activity
        sorted_apps = sorted(
            self.app_usage.items(),
            key=lambda x: x[1]["keys"] + x[1]["clicks"],
            reverse=True
        )[:10]

        if not sorted_apps:
            return Panel(
                Align.center("[dim]No application data yet...[/dim]"),
                title="[bold]🏆 Top Applications[/bold]",
                border_style="blue"
            )

        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("App", style="white")
        table.add_column("Keys", justify="right", style="green")
        table.add_column("Clicks", justify="right", style="yellow")
        table.add_column("Windows", justify="right", style="magenta")
        table.add_column("Activity", justify="right")

        # Calculate total for percentages
        total_activity = sum(app["keys"] + app["clicks"] for _, app in sorted_apps)

        for app_name, metrics in sorted_apps[:8]:
            activity = metrics["keys"] + metrics["clicks"]
            percentage = (activity / total_activity * 100) if total_activity > 0 else 0

            # Create mini progress bar
            bar_length = int(percentage / 5)  # Scale to 20 chars max
            bar = "█" * bar_length + "░" * (20 - bar_length)

            table.add_row(
                app_name[:20],
                f"{metrics['keys']:,}",
                f"{metrics['clicks']:,}",
                str(metrics['windows']),
                f"{bar} {percentage:.1f}%"
            )

        return Panel(table, title="[bold]🏆 Top Applications[/bold]", border_style="blue")

    def _generate_current_window_panel(self) -> Panel:
        """Generate current window/activity panel"""
        if not self.stats.get("last_window"):
            content = Align.center("[dim]Waiting for activity...[/dim]")
        else:
            window = self.stats["last_window"]
            app_name = window.get("process", "Unknown")
            window_title = window.get("title", "Unknown")

            # Get current app stats
            app_stats = self.app_usage.get(app_name, {"keys": 0, "clicks": 0, "windows": 0})

            grid = Table.grid(padding=(0, 2))
            grid.add_column(style="cyan")
            grid.add_column(style="white")

            grid.add_row("Application:", f"[bold green]{app_name}[/bold green]")
            grid.add_row("Window:", f"[dim]{window_title[:50]}[/dim]")
            grid.add_row("", "")
            grid.add_row("Session Stats:", "")
            grid.add_row("  └ Keystrokes:", f"[green]{app_stats['keys']:,}[/green]")
            grid.add_row("  └ Clicks:", f"[yellow]{app_stats['clicks']:,}[/yellow]")
            grid.add_row("  └ Windows:", f"[magenta]{app_stats['windows']}[/magenta]")

            content = grid

        return Panel(content, title="[bold]🎯 Current Focus[/bold]", border_style="magenta")

    def _generate_productivity_panel(self) -> Panel:
        """Generate productivity insights panel"""
        duration = (datetime.now() - self.stats["start_time"]).total_seconds()

        # Calculate productivity metrics
        if duration > 0:
            avg_keys_per_min = (self.stats["keystrokes"] / duration) * 60
            avg_clicks_per_min = (self.stats["clicks"] / duration) * 60

            # Activity score (simple heuristic)
            activity_score = min(100, int((avg_keys_per_min + avg_clicks_per_min) / 2))

            # Determine activity level
            if activity_score > 80:
                activity_level = "[bold green]Very High ⚡[/bold green]"
            elif activity_score > 60:
                activity_level = "[green]High 📈[/green]"
            elif activity_score > 40:
                activity_level = "[yellow]Moderate 📊[/yellow]"
            elif activity_score > 20:
                activity_level = "[yellow]Low 📉[/yellow]"
            else:
                activity_level = "[dim]Very Low 💤[/dim]"
        else:
            activity_score = 0
            activity_level = "[dim]Starting...[/dim]"

        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="cyan")
        grid.add_column(style="white")

        grid.add_row("Activity Level:", activity_level)
        grid.add_row("Activity Score:", f"[bold]{activity_score}/100[/bold]")
        grid.add_row("", "")
        grid.add_row("Averages:", "")
        if duration > 0:
            grid.add_row("  └ Keys/min:", f"[green]{avg_keys_per_min:.1f}[/green]")
            grid.add_row("  └ Clicks/min:", f"[yellow]{avg_clicks_per_min:.1f}[/yellow]")

        return Panel(grid, title="[bold]💡 Productivity Insights[/bold]", border_style="yellow")

    def _generate_display(self) -> Layout:
        """Generate rich TUI display layout"""
        layout = Layout()

        # Create main layout structure
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=1)
        )

        # Split main into left and right
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )

        # Split left into top and bottom
        layout["left"].split_column(
            Layout(name="metrics", ratio=1),
            Layout(name="apps", ratio=2)
        )

        # Split right into current and productivity
        layout["right"].split_column(
            Layout(name="current", ratio=1),
            Layout(name="productivity", ratio=1)
        )

        # Populate panels
        layout["header"].update(self._generate_header())
        layout["metrics"].update(self._generate_metrics_panel())
        layout["apps"].update(self._generate_top_apps_panel())
        layout["current"].update(self._generate_current_window_panel())
        layout["productivity"].update(self._generate_productivity_panel())

        # Footer
        footer_text = Text()
        footer_text.append("Press ", style="dim")
        footer_text.append("Ctrl+C", style="bold red")
        footer_text.append(" to quit  •  ", style="dim")
        footer_text.append(f"Data: {self.settings.data_dir}", style="dim cyan")
        layout["footer"].update(Align.center(footer_text))

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
            self.current_second_keys += 1

            # Track per-app metrics
            if self.stats.get("last_window"):
                app_name = self.stats["last_window"].get("process", "Unknown")
                self.app_usage[app_name]["keys"] += 1

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
                self.current_second_clicks += 1

                # Track per-app metrics
                if self.stats.get("last_window"):
                    app_name = self.stats["last_window"].get("process", "Unknown")
                    self.app_usage[app_name]["clicks"] += 1

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

                # Track per-app window count
                app_name = window_info.get("process", "Unknown")
                self.app_usage[app_name]["windows"] += 1

                await self.store.update_window_info(
                    window_info["process"], window_info["title"], window_info.get("bundle", "")
                )
        except Exception as e:
            logger.error("Window check error", error=str(e))
