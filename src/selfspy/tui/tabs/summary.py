"""
SummaryTab - Session statistics and comparisons

Displays session totals, active/idle time breakdown, and
comparison with yesterday's activity.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Label, Static


class StatRow(Static):
    """A single statistic row with label and value."""

    DEFAULT_CSS = """
    StatRow {
        height: 1;
        width: 100%;
    }

    StatRow Horizontal {
        width: 100%;
    }

    StatRow .stat-label {
        width: 20;
        color: $text-muted;
    }

    StatRow .stat-value {
        width: auto;
    }

    StatRow .stat-percent {
        width: 10;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        label: str,
        value: str = "",
        percent: str = "",
        id: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(id=id, **kwargs)
        self.label_text = label
        self._value = value
        self._percent = percent

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(self.label_text, classes="stat-label")
            yield Label(self._value, classes="stat-value", id="value")
            if self._percent:
                yield Label(f"({self._percent})", classes="stat-percent", id="percent")

    def update(self, value: str, percent: str = "") -> None:
        """Update the value and percent."""
        self._value = value
        self._percent = percent
        try:
            self.query_one("#value", Label).update(value)
            if percent:
                try:
                    self.query_one("#percent", Label).update(f"({percent})")
                except Exception:
                    pass
        except Exception:
            pass


class SummaryTab(Static):
    """Session statistics summary tab.

    Shows session totals, active/idle time breakdown, and
    comparison with yesterday's activity.
    """

    DEFAULT_CSS = """
    SummaryTab {
        padding: 1 2;
    }

    SummaryTab .section-header {
        text-style: bold;
        margin-bottom: 1;
    }

    SummaryTab .section-divider {
        height: 1;
        margin: 1 0;
    }

    SummaryTab .comparison-positive {
        color: $success;
    }

    SummaryTab .comparison-negative {
        color: $error;
    }
    """

    # Reactive properties
    session_duration: reactive[str] = reactive("00:00:00")
    active_time: reactive[str] = reactive("00:00:00")
    active_percent: reactive[float] = reactive(0.0)
    idle_time: reactive[str] = reactive("00:00:00")
    idle_percent: reactive[float] = reactive(0.0)
    total_keystrokes: reactive[int] = reactive(0)
    total_clicks: reactive[int] = reactive(0)
    windows_switched: reactive[int] = reactive(0)
    yesterday_diff: reactive[float] = reactive(0.0)
    more_active_than_yesterday: reactive[bool] = reactive(True)

    def compose(self) -> ComposeResult:
        # Time section
        yield Label("Time", classes="section-header")
        yield StatRow("Session Duration", id="duration-row")
        yield StatRow("Active Time", id="active-row")
        yield StatRow("Idle Time", id="idle-row")

        yield Static("", classes="section-divider")

        # Activity section
        yield Label("Activity", classes="section-header")
        yield StatRow("Total Keystrokes", id="keystrokes-row")
        yield StatRow("Total Clicks", id="clicks-row")
        yield StatRow("Windows Switched", id="windows-row")

        yield Static("", classes="section-divider")

        # Comparison section
        yield Label("Comparison", classes="section-header")
        yield Label("vs Yesterday: --", id="yesterday-comparison")

    def update_stats(
        self,
        session_duration: str = "00:00:00",
        active_time: str = "00:00:00",
        active_percent: float = 0.0,
        idle_time: str = "00:00:00",
        idle_percent: float = 0.0,
        total_keystrokes: int = 0,
        total_clicks: int = 0,
        windows_switched: int = 0,
    ) -> None:
        """Update all statistics at once."""
        self.session_duration = session_duration
        self.active_time = active_time
        self.active_percent = active_percent
        self.idle_time = idle_time
        self.idle_percent = idle_percent
        self.total_keystrokes = total_keystrokes
        self.total_clicks = total_clicks
        self.windows_switched = windows_switched

        # Update display
        try:
            self.query_one("#duration-row", StatRow).update(session_duration)
            self.query_one("#active-row", StatRow).update(
                active_time, f"{active_percent:.0f}%"
            )
            self.query_one("#idle-row", StatRow).update(
                idle_time, f"{idle_percent:.0f}%"
            )
            self.query_one("#keystrokes-row", StatRow).update(f"{total_keystrokes:,}")
            self.query_one("#clicks-row", StatRow).update(f"{total_clicks:,}")
            self.query_one("#windows-row", StatRow).update(f"{windows_switched:,}")
        except Exception:
            pass  # Widgets not mounted yet

    def set_yesterday_comparison(self, diff_percent: float, more_active: bool) -> None:
        """Set the yesterday comparison display.

        Args:
            diff_percent: Percentage difference from yesterday
            more_active: True if more active than yesterday
        """
        self.yesterday_diff = diff_percent
        self.more_active_than_yesterday = more_active

        try:
            comparison_label = self.query_one("#yesterday-comparison", Label)
            if more_active:
                comparison_label.update(
                    f"vs Yesterday: +{diff_percent:.0f}% more active"
                )
                comparison_label.set_classes("comparison-positive")
            else:
                comparison_label.update(
                    f"vs Yesterday: -{diff_percent:.0f}% less active"
                )
                comparison_label.set_classes("comparison-negative")
        except Exception:
            pass
