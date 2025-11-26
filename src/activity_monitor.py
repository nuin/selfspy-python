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

        # Idle detection (3 minutes without activity = idle)
        self.idle_threshold = timedelta(minutes=3)
        self.last_activity_time = datetime.now()
        self.is_idle = False
        self.idle_start_time: Optional[datetime] = None
        self.session_active_seconds = 0
        self.session_idle_seconds = 0

        # Historical comparison data
        self.yesterday_data: Optional[Dict[str, Any]] = None
        self.yesterday_fetched = False

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

        # Calculate active/idle percentages
        total_seconds = self.session_active_seconds + self.session_idle_seconds
        active_pct = (self.session_active_seconds / total_seconds * 100) if total_seconds > 0 else 100

        # Idle status indicator
        idle_indicator = "💤 IDLE" if self.is_idle else "✓ ACTIVE"
        idle_style = "yellow" if self.is_idle else "green"

        grid = Table.grid(padding=1)
        grid.add_column(justify="left", style="cyan bold")
        grid.add_column(justify="center")
        grid.add_column(justify="right", style="magenta bold")

        # Format session time with active percentage
        session_info = f"⏱  {hours:02d}h {minutes:02d}m {seconds:02d}s  •  {active_pct:.0f}% active"

        grid.add_row(
            session_info,
            Text("SELFSPY ACTIVITY MONITOR", style="bold white"),
            Text(idle_indicator, style=idle_style)
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
        table.add_column("App", style="white", width=20)
        table.add_column("Keys", justify="right", style="green")
        table.add_column("Clicks", justify="right", style="yellow")
        table.add_column("Windows", justify="right", style="magenta")
        table.add_column("Activity", justify="left", width=20)

        # Calculate total for percentages
        total_activity = sum(app["keys"] + app["clicks"] for _, app in sorted_apps)

        for app_name, metrics in sorted_apps[:8]:
            activity = metrics["keys"] + metrics["clicks"]
            percentage = (activity / total_activity * 100) if total_activity > 0 else 0

            # Create mini progress bar - use only filled blocks, fixed format
            max_bar_width = 10
            bar_length = int((percentage / 100) * max_bar_width)
            bar = "█" * bar_length

            # Fixed width format: bar padded to 10 chars + space + percentage
            activity_display = f"{bar:<10} {percentage:5.1f}%"

            table.add_row(
                app_name[:20],
                f"{metrics['keys']:,}",
                f"{metrics['clicks']:,}",
                str(metrics['windows']),
                activity_display
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

    def _generate_comparison_panel(self) -> Panel:
        """Generate comparison with yesterday's data"""
        if not self.yesterday_data:
            return Panel(
                Align.center("[dim]No yesterday data yet[/dim]"),
                title="[bold]📊 vs Yesterday[/bold]",
                border_style="cyan"
            )

        grid = Table.grid(padding=(0, 2))
        grid.add_column("Metric", style="cyan")
        grid.add_column("Change", style="white")

        # Calculate differences
        key_diff = self.stats["keystrokes"] - self.yesterday_data["keystrokes"]
        click_diff = self.stats["clicks"] - self.yesterday_data["clicks"]
        active_diff = self.session_active_seconds - self.yesterday_data["active_seconds"]

        # Format with arrows and colors
        def format_change(diff, total_yesterday):
            if total_yesterday == 0:
                return "[dim]N/A[/dim]"
            pct = (diff / total_yesterday) * 100
            if abs(pct) < 1:
                return "[dim]~same[/dim]"
            arrow = "▲" if diff > 0 else "▼"
            color = "green" if diff > 0 else "red"
            return f"[{color}]{arrow} {abs(pct):.0f}%[/{color}]"

        grid.add_row(
            "⌨  Keystrokes",
            format_change(key_diff, self.yesterday_data["keystrokes"])
        )
        grid.add_row(
            "🖱  Clicks",
            format_change(click_diff, self.yesterday_data["clicks"])
        )
        grid.add_row(
            "⚡ Active Time",
            format_change(active_diff, self.yesterday_data["active_seconds"])
        )

        # Overall verdict
        overall_change = (
            (self.stats["keystrokes"] + self.stats["clicks"]) -
            (self.yesterday_data["keystrokes"] + self.yesterday_data["clicks"])
        )
        yesterday_total = self.yesterday_data["keystrokes"] + self.yesterday_data["clicks"]

        if yesterday_total > 0:
            pct_change = (overall_change / yesterday_total) * 100
            if abs(pct_change) < 5:
                verdict = "[yellow]Similar activity[/yellow]"
            elif pct_change > 0:
                verdict = f"[green]▲ {pct_change:.0f}% more active[/green]"
            else:
                verdict = f"[red]▼ {abs(pct_change):.0f}% less active[/red]"
        else:
            verdict = "[dim]No comparison data[/dim]"

        grid.add_row("", "")
        grid.add_row("Overall", verdict)

        return Panel(grid, title="[bold]📊 vs Yesterday[/bold]", border_style="cyan")

    async def _fetch_yesterday_data(self):
        """Fetch yesterday's session data for comparison"""
        if self.yesterday_fetched:
            return

        try:
            from datetime import date
            from sqlalchemy import func, select
            from .models import Session, Keys, Click

            yesterday = date.today() - timedelta(days=1)
            yesterday_start = datetime.combine(yesterday, datetime.min.time())
            yesterday_end = datetime.combine(yesterday, datetime.max.time())

            async with self.store.async_session() as session:
                # Get all yesterday's sessions
                sessions_query = select(Session).where(
                    Session.start_time >= yesterday_start,
                    Session.start_time <= yesterday_end
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
                        "session_count": len(sessions)
                    }
                    logger.info(f"Fetched yesterday's data: {len(sessions)} sessions")

            self.yesterday_fetched = True
        except Exception as e:
            logger.warning(f"Could not fetch yesterday's data: {e}")
            self.yesterday_fetched = True  # Don't keep trying

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

        # Split right into three panels
        layout["right"].split_column(
            Layout(name="current", ratio=1),
            Layout(name="productivity", ratio=1),
            Layout(name="comparison", ratio=1)
        )

        # Populate panels
        layout["header"].update(self._generate_header())
        layout["metrics"].update(self._generate_metrics_panel())
        layout["apps"].update(self._generate_top_apps_panel())
        layout["current"].update(self._generate_current_window_panel())
        layout["productivity"].update(self._generate_productivity_panel())
        layout["comparison"].update(self._generate_comparison_panel())

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

    async def _monitor_idle_state(self):
        """Monitor idle state and update session metrics"""
        while self.running:
            now = datetime.now()
            time_since_activity = now - self.last_activity_time

            # Check if we've gone idle
            if not self.is_idle and time_since_activity > self.idle_threshold:
                self.is_idle = True
                self.idle_start_time = self.last_activity_time + self.idle_threshold
                logger.info(f"User went idle after {self.idle_threshold.total_seconds()}s of inactivity")

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
        if hasattr(self, 'input_tracker'):
            self.input_tracker.stop()

        # Flush any remaining buffered data
        await self._flush_buffer(force=True)

        # Update final session metrics
        if self.is_idle and self.idle_start_time:
            idle_duration = int((datetime.now() - self.idle_start_time).total_seconds())
            await self.store.update_session_metrics(idle_seconds=idle_duration)

        # Close database connection (this will end the session)
        if hasattr(self, 'store'):
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
                # Reset idle state
                self.last_activity_time = datetime.now()

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
                    await self.store.store_click(click["button"], click["x"], click["y"])
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
                    window_info["process"], window_info["title"], window_info.get("bundle", "")
                )
        except Exception as e:
            logger.error("Window check error", error=str(e))
