# TUI Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Rich Live TUI with Textual tabbed interface (Live, Apps, Summary tabs).

**Architecture:** Separate data collection (ActivityMonitor) from display (SelfspyApp). Textual app polls monitor state every second. Three TabPanes for different views.

**Tech Stack:** Textual >=0.50.0, existing Rich (used by Textual internally)

---

## Task 1: Add Textual Dependency

**Files:**
- Modify: `pyproject.toml:37-50`

**Step 1: Add textual to dependencies**

In `pyproject.toml`, add to dependencies list:

```toml
"textual>=0.50.0",
```

**Step 2: Sync dependencies**

Run: `uv sync --group dev --extra macos`
Expected: Successfully installs textual

**Step 3: Verify installation**

Run: `uv run python -c "import textual; print(textual.__version__)"`
Expected: Prints version >= 0.50.0

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add textual for TUI redesign"
```

---

## Task 2: Create TUI Module Structure

**Files:**
- Create: `src/tui/__init__.py`
- Create: `src/tui/tabs/__init__.py`
- Create: `src/tui/widgets/__init__.py`

**Step 1: Create directories and init files**

```python
# src/tui/__init__.py
"""Textual-based TUI for Selfspy"""

# src/tui/tabs/__init__.py
"""Tab components for Selfspy TUI"""

# src/tui/widgets/__init__.py
"""Custom widgets for Selfspy TUI"""
```

**Step 2: Verify structure**

Run: `ls -la src/tui/ src/tui/tabs/ src/tui/widgets/`
Expected: All __init__.py files exist

**Step 3: Commit**

```bash
git add src/tui/
git commit -m "feat(tui): create module structure"
```

---

## Task 3: Create Sparkline Widget

**Files:**
- Create: `src/tui/widgets/sparkline.py`
- Create: `tests/test_tui_widgets.py`

**Step 1: Write the failing test**

```python
# tests/test_tui_widgets.py
"""Tests for TUI widgets"""

import pytest
from src.tui.widgets.sparkline import Sparkline


def test_sparkline_empty_data():
    """Sparkline with no data shows flat line"""
    widget = Sparkline()
    widget.data = []
    assert widget._render_sparkline() == "▁" * 20


def test_sparkline_with_data():
    """Sparkline renders data as bar characters"""
    widget = Sparkline()
    widget.data = [0, 50, 100]
    result = widget._render_sparkline()
    assert result[0] == "▁"  # min value
    assert result[-1] == "█"  # max value


def test_sparkline_uniform_data():
    """Sparkline with uniform data shows flat line"""
    widget = Sparkline()
    widget.data = [50, 50, 50]
    result = widget._render_sparkline()
    # All same value should render as middle bars
    assert len(set(result)) == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tui_widgets.py -v`
Expected: FAIL with "No module named 'src.tui.widgets.sparkline'"

**Step 3: Write implementation**

```python
# src/tui/widgets/sparkline.py
"""Sparkline widget for real-time data visualization"""

from textual.reactive import reactive
from textual.widget import Widget
from textual.app import RenderResult
from rich.text import Text


class Sparkline(Widget):
    """A sparkline chart widget showing recent activity"""

    DEFAULT_CSS = """
    Sparkline {
        height: 1;
        width: auto;
    }
    """

    data: reactive[list[int]] = reactive(list, init=False)
    max_points: int = 40
    max_value: int | None = None

    BARS = "▁▂▃▄▅▆▇█"

    def __init__(
        self,
        max_points: int = 40,
        max_value: int | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.data = []
        self.max_points = max_points
        self.max_value = max_value

    def _render_sparkline(self) -> str:
        """Render data as sparkline characters"""
        if not self.data:
            return "▁" * 20

        display_data = list(self.data)[-self.max_points:]
        max_val = self.max_value or max(display_data) if max(display_data) > 0 else 1

        result = ""
        for value in display_data:
            index = min(
                int((value / max_val) * (len(self.BARS) - 1)),
                len(self.BARS) - 1
            )
            result += self.BARS[index]

        return result

    def render(self) -> RenderResult:
        """Render the sparkline"""
        return Text(self._render_sparkline(), style="yellow")

    def add_point(self, value: int) -> None:
        """Add a data point to the sparkline"""
        new_data = list(self.data)
        new_data.append(value)
        if len(new_data) > self.max_points:
            new_data = new_data[-self.max_points:]
        self.data = new_data
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_tui_widgets.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tui/widgets/sparkline.py tests/test_tui_widgets.py
git commit -m "feat(tui): add sparkline widget with tests"
```

---

## Task 4: Create Live Tab

**Files:**
- Create: `src/tui/tabs/live.py`

**Step 1: Write the Live tab component**

```python
# src/tui/tabs/live.py
"""Live metrics tab showing real-time activity"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Label, Static

from ..widgets.sparkline import Sparkline


class MetricRow(Horizontal):
    """A row showing a metric with sparkline"""

    DEFAULT_CSS = """
    MetricRow {
        height: 1;
        width: 100%;
    }
    MetricRow > Label {
        width: 15;
    }
    MetricRow > .value {
        width: 10;
        text-align: right;
    }
    MetricRow > Sparkline {
        width: 40;
        margin-left: 2;
    }
    MetricRow > .rate {
        width: 10;
        text-align: right;
        color: $text-muted;
    }
    """

    def __init__(self, label: str, metric_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.label = label
        self.metric_id = metric_id

    def compose(self) -> ComposeResult:
        yield Label(self.label)
        yield Static("0", classes="value", id=f"{self.metric_id}-value")
        yield Sparkline(id=f"{self.metric_id}-spark")
        yield Static("0/min", classes="rate", id=f"{self.metric_id}-rate")


class LiveTab(Container):
    """Tab showing real-time activity metrics"""

    DEFAULT_CSS = """
    LiveTab {
        padding: 1 2;
    }
    LiveTab > .section {
        margin-bottom: 1;
    }
    LiveTab > .divider {
        height: 1;
        margin: 1 0;
        border-top: solid $primary;
    }
    LiveTab > .current-window {
        margin-top: 1;
    }
    LiveTab > .status-row {
        margin-top: 1;
    }
    LiveTab > .status-row > Label {
        width: 50%;
    }
    LiveTab > .status-row > .duration {
        width: 50%;
        text-align: right;
    }
    """

    current_window: reactive[str] = reactive("Waiting for activity...")
    status: reactive[str] = reactive("ACTIVE")
    duration: reactive[str] = reactive("00:00:00")

    def compose(self) -> ComposeResult:
        yield MetricRow("Keystrokes", "keys", classes="section")
        yield MetricRow("Clicks", "clicks", classes="section")
        yield Static("", classes="divider")
        yield Static(self.current_window, classes="current-window", id="current-window")
        with Horizontal(classes="status-row"):
            yield Label(id="status-label")
            yield Static(self.duration, classes="duration", id="duration")

    def watch_current_window(self, value: str) -> None:
        """Update current window display"""
        widget = self.query_one("#current-window", Static)
        widget.update(f"Current: {value}")

    def watch_status(self, value: str) -> None:
        """Update status display"""
        label = self.query_one("#status-label", Label)
        style = "green" if value == "ACTIVE" else "yellow"
        label.update(f"[{style}]{value}[/{style}]")

    def watch_duration(self, value: str) -> None:
        """Update duration display"""
        widget = self.query_one("#duration", Static)
        widget.update(value)

    def update_metrics(
        self,
        keystrokes: int,
        keys_rate: int,
        keys_history: list[int],
        clicks: int,
        clicks_rate: int,
        clicks_history: list[int],
    ) -> None:
        """Update all metrics"""
        # Keystrokes
        self.query_one("#keys-value", Static).update(f"{keystrokes:,}")
        self.query_one("#keys-rate", Static).update(f"{keys_rate}/min")
        spark = self.query_one("#keys-spark", Sparkline)
        spark.data = keys_history

        # Clicks
        self.query_one("#clicks-value", Static).update(f"{clicks:,}")
        self.query_one("#clicks-rate", Static).update(f"{clicks_rate}/min")
        spark = self.query_one("#clicks-spark", Sparkline)
        spark.data = clicks_history
```

**Step 2: Verify syntax**

Run: `uv run python -c "from src.tui.tabs.live import LiveTab; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add src/tui/tabs/live.py
git commit -m "feat(tui): add LiveTab component"
```

---

## Task 5: Create Apps Tab

**Files:**
- Create: `src/tui/tabs/apps.py`

**Step 1: Write the Apps tab component**

```python
# src/tui/tabs/apps.py
"""Applications tab showing activity per app"""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable


class AppsTab(Container):
    """Tab showing application activity breakdown"""

    DEFAULT_CSS = """
    AppsTab {
        padding: 1 2;
    }
    AppsTab > DataTable {
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        table = DataTable(id="apps-table")
        table.add_columns("App", "Keys", "Clicks", "Activity")
        table.cursor_type = "row"
        yield table

    def update_apps(self, apps: list[dict]) -> None:
        """Update the applications table

        Args:
            apps: List of dicts with keys: name, keys, clicks, percentage
        """
        table = self.query_one("#apps-table", DataTable)
        table.clear()

        for app in apps:
            # Create activity bar
            bar_length = int(app["percentage"] / 10)
            bar = "█" * bar_length + "░" * (10 - bar_length)
            activity = f"{bar} {app['percentage']:5.1f}%"

            table.add_row(
                app["name"][:25],
                f"{app['keys']:,}",
                f"{app['clicks']:,}",
                activity,
            )
```

**Step 2: Verify syntax**

Run: `uv run python -c "from src.tui.tabs.apps import AppsTab; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add src/tui/tabs/apps.py
git commit -m "feat(tui): add AppsTab component"
```

---

## Task 6: Create Summary Tab

**Files:**
- Create: `src/tui/tabs/summary.py`

**Step 1: Write the Summary tab component**

```python
# src/tui/tabs/summary.py
"""Summary tab showing session statistics"""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static


class SummaryTab(Container):
    """Tab showing session summary statistics"""

    DEFAULT_CSS = """
    SummaryTab {
        padding: 1 2;
    }
    SummaryTab > .stat-row {
        height: 1;
        margin-bottom: 1;
    }
    SummaryTab > .stat-row > .label {
        width: 25;
    }
    SummaryTab > .stat-row > .value {
        width: auto;
    }
    SummaryTab > .divider {
        height: 1;
        margin: 1 0;
    }
    SummaryTab > .comparison {
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        # Time stats
        yield Static("Session Duration", id="duration-label", classes="stat-row label")
        yield Static("00:00:00", id="duration-value", classes="stat-row value")

        yield Static("Active Time", classes="stat-row label")
        yield Static("00:00:00 (100%)", id="active-value", classes="stat-row value")

        yield Static("Idle Time", classes="stat-row label")
        yield Static("00:00:00 (0%)", id="idle-value", classes="stat-row value")

        yield Static("", classes="divider")

        # Activity stats
        yield Static("Total Keystrokes", classes="stat-row label")
        yield Static("0", id="total-keys", classes="stat-row value")

        yield Static("Total Clicks", classes="stat-row label")
        yield Static("0", id="total-clicks", classes="stat-row value")

        yield Static("Windows Switched", classes="stat-row label")
        yield Static("0", id="total-windows", classes="stat-row value")

        yield Static("", classes="divider")

        # Comparison
        yield Static("vs Yesterday", classes="stat-row label")
        yield Static("No data", id="comparison", classes="comparison")

    def update_summary(
        self,
        duration: str,
        active_time: str,
        active_pct: int,
        idle_time: str,
        idle_pct: int,
        total_keys: int,
        total_clicks: int,
        total_windows: int,
        comparison: str | None = None,
    ) -> None:
        """Update all summary statistics"""
        self.query_one("#duration-value", Static).update(duration)
        self.query_one("#active-value", Static).update(f"{active_time} ({active_pct}%)")
        self.query_one("#idle-value", Static).update(f"{idle_time} ({idle_pct}%)")
        self.query_one("#total-keys", Static).update(f"{total_keys:,}")
        self.query_one("#total-clicks", Static).update(f"{total_clicks:,}")
        self.query_one("#total-windows", Static).update(f"{total_windows:,}")

        if comparison:
            self.query_one("#comparison", Static).update(comparison)
```

**Step 2: Verify syntax**

Run: `uv run python -c "from src.tui.tabs.summary import SummaryTab; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add src/tui/tabs/summary.py
git commit -m "feat(tui): add SummaryTab component"
```

---

## Task 7: Create Main App

**Files:**
- Create: `src/tui/app.py`

**Step 1: Write the main Textual app**

```python
# src/tui/app.py
"""Main Textual application for Selfspy"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane

from .tabs.apps import AppsTab
from .tabs.live import LiveTab
from .tabs.summary import SummaryTab

if TYPE_CHECKING:
    from ..activity_monitor import ActivityMonitor


class SelfspyApp(App):
    """Selfspy activity monitor TUI"""

    TITLE = "Selfspy Activity Monitor"

    CSS = """
    TabbedContent {
        height: 100%;
    }
    TabPane {
        padding: 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "show_tab('live')", "Live", show=False),
        Binding("2", "show_tab('apps')", "Apps", show=False),
        Binding("3", "show_tab('summary')", "Summary", show=False),
    ]

    def __init__(self, monitor: "ActivityMonitor", **kwargs) -> None:
        super().__init__(**kwargs)
        self.monitor = monitor
        self._update_interval = 1.0

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="tabs"):
            with TabPane("Live", id="live"):
                yield LiveTab(id="live-tab")
            with TabPane("Apps", id="apps"):
                yield AppsTab(id="apps-tab")
            with TabPane("Summary", id="summary"):
                yield SummaryTab(id="summary-tab")
        yield Footer()

    def on_mount(self) -> None:
        """Start periodic updates when app mounts"""
        self.set_interval(self._update_interval, self._update_display)

    def action_show_tab(self, tab_id: str) -> None:
        """Switch to a specific tab"""
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = tab_id

    def _update_display(self) -> None:
        """Update all displays with current monitor data"""
        self._update_live_tab()
        self._update_apps_tab()
        self._update_summary_tab()

    def _update_live_tab(self) -> None:
        """Update live tab with current metrics"""
        tab = self.query_one("#live-tab", LiveTab)

        stats = self.monitor.stats
        duration = datetime.now() - stats["start_time"]
        duration_seconds = int(duration.total_seconds())

        # Calculate rates
        keys_rate = int(stats["keystrokes"] / max(duration_seconds, 1) * 60)
        clicks_rate = int(stats["clicks"] / max(duration_seconds, 1) * 60)

        tab.update_metrics(
            keystrokes=stats["keystrokes"],
            keys_rate=keys_rate,
            keys_history=list(self.monitor.keystroke_history),
            clicks=stats["clicks"],
            clicks_rate=clicks_rate,
            clicks_history=list(self.monitor.click_history),
        )

        # Update window and status
        if stats.get("last_window"):
            window = stats["last_window"]
            tab.current_window = f"{window.get('process', 'Unknown')} - {window.get('title', '')[:40]}"

        tab.status = "IDLE" if self.monitor.is_idle else "ACTIVE"

        hours, remainder = divmod(duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        tab.duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _update_apps_tab(self) -> None:
        """Update apps tab with application data"""
        tab = self.query_one("#apps-tab", AppsTab)

        # Sort apps by activity
        sorted_apps = sorted(
            self.monitor.app_usage.items(),
            key=lambda x: x[1]["keys"] + x[1]["clicks"],
            reverse=True,
        )[:15]

        total = sum(app["keys"] + app["clicks"] for _, app in sorted_apps) or 1

        apps_data = [
            {
                "name": name,
                "keys": data["keys"],
                "clicks": data["clicks"],
                "percentage": (data["keys"] + data["clicks"]) / total * 100,
            }
            for name, data in sorted_apps
        ]

        tab.update_apps(apps_data)

    def _update_summary_tab(self) -> None:
        """Update summary tab with session data"""
        tab = self.query_one("#summary-tab", SummaryTab)

        stats = self.monitor.stats
        duration = datetime.now() - stats["start_time"]
        duration_seconds = int(duration.total_seconds())

        active = self.monitor.session_active_seconds
        idle = self.monitor.session_idle_seconds
        total = active + idle or 1

        def format_time(seconds: int) -> str:
            h, r = divmod(seconds, 3600)
            m, s = divmod(r, 60)
            return f"{h:02d}:{m:02d}:{s:02d}"

        # Build comparison string
        comparison = None
        if self.monitor.yesterday_data:
            yd = self.monitor.yesterday_data
            today_total = stats["keystrokes"] + stats["clicks"]
            yesterday_total = yd["keystrokes"] + yd["clicks"]
            if yesterday_total > 0:
                pct = ((today_total - yesterday_total) / yesterday_total) * 100
                if pct > 0:
                    comparison = f"[green]▲ {pct:.0f}% more active[/green]"
                elif pct < 0:
                    comparison = f"[red]▼ {abs(pct):.0f}% less active[/red]"
                else:
                    comparison = "[yellow]Same as yesterday[/yellow]"

        tab.update_summary(
            duration=format_time(duration_seconds),
            active_time=format_time(active),
            active_pct=int(active / total * 100),
            idle_time=format_time(idle),
            idle_pct=int(idle / total * 100),
            total_keys=stats["keystrokes"],
            total_clicks=stats["clicks"],
            total_windows=stats["windows"],
            comparison=comparison,
        )
```

**Step 2: Verify syntax**

Run: `uv run python -c "from src.tui.app import SelfspyApp; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add src/tui/app.py
git commit -m "feat(tui): add main SelfspyApp with tabbed interface"
```

---

## Task 8: Update ActivityMonitor to Remove Display Code

**Files:**
- Modify: `src/activity_monitor.py`

**Step 1: Remove display methods and Rich imports**

Remove these methods from ActivityMonitor:
- `_generate_header()`
- `_generate_metrics_panel()`
- `_generate_top_apps_panel()`
- `_generate_current_window_panel()`
- `_generate_productivity_panel()`
- `_generate_comparison_panel()`
- `_generate_display()`

Remove unused imports:
- `from rich.align import Align`
- `from rich.layout import Layout`
- `from rich.live import Live`
- `from rich.panel import Panel`
- `from rich.table import Table`
- `from rich.text import Text`

Keep `_create_sparkline()` and `_update_metrics()` as they update data used by the TUI.

**Step 2: Modify start() to use Textual**

Update the `start()` method to run the Textual app instead of Rich Live:

```python
async def start(self):
    """Start monitoring asynchronously"""
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
                    "Accessibility permissions still missing."
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

    # Fetch yesterday's data for comparison
    asyncio.create_task(self._fetch_yesterday_data())

    # Run Textual app
    from .tui.app import SelfspyApp

    app = SelfspyApp(monitor=self)
    try:
        await app.run_async()
    finally:
        await self._cleanup()
```

**Step 3: Remove self.live_display references**

Remove `self.live_display = None` from __init__ and all references to it.

**Step 4: Verify it compiles**

Run: `uv run python -c "from src.activity_monitor import ActivityMonitor; print('OK')"`
Expected: OK

**Step 5: Commit**

```bash
git add src/activity_monitor.py
git commit -m "refactor: remove Rich display, integrate Textual app"
```

---

## Task 9: Update Exports

**Files:**
- Modify: `src/tui/__init__.py`
- Modify: `src/tui/tabs/__init__.py`
- Modify: `src/tui/widgets/__init__.py`

**Step 1: Update exports**

```python
# src/tui/__init__.py
"""Textual-based TUI for Selfspy"""
from .app import SelfspyApp

__all__ = ["SelfspyApp"]

# src/tui/tabs/__init__.py
"""Tab components for Selfspy TUI"""
from .apps import AppsTab
from .live import LiveTab
from .summary import SummaryTab

__all__ = ["LiveTab", "AppsTab", "SummaryTab"]

# src/tui/widgets/__init__.py
"""Custom widgets for Selfspy TUI"""
from .sparkline import Sparkline

__all__ = ["Sparkline"]
```

**Step 2: Verify imports work**

Run: `uv run python -c "from src.tui import SelfspyApp; from src.tui.tabs import LiveTab, AppsTab, SummaryTab; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add src/tui/
git commit -m "feat(tui): add module exports"
```

---

## Task 10: Test Full Application

**Step 1: Run linter**

Run: `uv run ruff check src/tui/`
Expected: No errors (fix any that appear)

**Step 2: Run type checker**

Run: `uv run mypy src/tui/ --ignore-missing-imports`
Expected: No errors (fix any that appear)

**Step 3: Run existing tests**

Run: `uv run pytest -v`
Expected: All tests pass

**Step 4: Manual test**

Run: `uv run selfspy start --debug`
Expected:
- Textual TUI launches with three tabs
- Tab navigation works with arrows and 1/2/3 keys
- Live tab shows updating metrics
- Apps tab shows application list
- Summary tab shows session stats
- Q quits cleanly

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat(tui): complete Textual-based TUI redesign"
```

---

## Summary

10 tasks total:
1. Add Textual dependency
2. Create module structure
3. Create Sparkline widget (with tests)
4. Create LiveTab
5. Create AppsTab
6. Create SummaryTab
7. Create main SelfspyApp
8. Refactor ActivityMonitor
9. Update exports
10. Test and verify
