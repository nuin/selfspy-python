"""
LiveTab - Real-time activity feedback

Displays current keystroke/click counts with sparklines showing
recent activity patterns, current window focus, and session status.
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import Label, Static

from ..widgets.sparkline import Sparkline


class MetricDisplay(Static):
    """A metric with label, value, sparkline, and rate."""

    DEFAULT_CSS = """
    MetricDisplay {
        height: 1;
        width: 100%;
    }

    MetricDisplay Horizontal {
        width: 100%;
    }

    MetricDisplay .metric-label {
        width: 12;
        text-style: bold;
    }

    MetricDisplay .metric-value {
        width: 10;
        text-align: right;
    }

    MetricDisplay .metric-rate {
        width: 10;
        text-align: right;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        label: str,
        value: int = 0,
        rate: int = 0,
        rate_suffix: str = "/min",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.label_text = label
        self._value = value
        self._rate = rate
        self.rate_suffix = rate_suffix
        self._sparkline_data: list[float] = []

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(self.label_text, classes="metric-label")
            yield Label(f"{self._value:,}", classes="metric-value", id="value")
            yield Sparkline(data=self._sparkline_data, max_width=20, id="sparkline")
            yield Label(
                f"{self._rate}{self.rate_suffix}", classes="metric-rate", id="rate"
            )

    def update(self, value: int, rate: int) -> None:
        """Update the metric value and rate."""
        self._value = value
        self._rate = rate
        try:
            self.query_one("#value", Label).update(f"{value:,}")
            self.query_one("#rate", Label).update(f"{rate}{self.rate_suffix}")
        except Exception:
            pass  # Widget not mounted yet

    def add_sample(self, value: float) -> None:
        """Add a sample to the sparkline."""
        self._sparkline_data.append(value)
        if len(self._sparkline_data) > 60:  # Keep 60 samples (1 minute at 1/sec)
            self._sparkline_data = self._sparkline_data[-60:]
        try:
            sparkline = self.query_one("#sparkline", Sparkline)
            sparkline.data = self._sparkline_data
        except Exception:
            pass


class LiveTab(Static):
    """Live activity monitoring tab.

    Shows real-time keystroke and click counts with sparklines,
    current window information, and session status.
    """

    DEFAULT_CSS = """
    LiveTab {
        padding: 1 2;
    }

    LiveTab .section-divider {
        height: 1;
        margin: 1 0;
        color: $border;
    }

    LiveTab .current-info {
        margin-top: 1;
    }

    LiveTab .info-label {
        width: 10;
        color: $text-muted;
    }

    LiveTab .info-value {
        width: auto;
    }

    LiveTab .status-active {
        color: $success;
        text-style: bold;
    }

    LiveTab .status-idle {
        color: $warning;
    }

    LiveTab .session-time {
        text-align: right;
        width: 12;
    }
    """

    # Reactive properties for live updates
    keystrokes: reactive[int] = reactive(0)
    clicks: reactive[int] = reactive(0)
    keys_per_min: reactive[int] = reactive(0)
    clicks_per_min: reactive[int] = reactive(0)
    current_window: reactive[str] = reactive("")
    status: reactive[str] = reactive("ACTIVE")
    session_duration: reactive[str] = reactive("00:00:00")

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.keystroke_history: list[float] = []
        self.click_history: list[float] = []

    def compose(self) -> ComposeResult:
        yield MetricDisplay("Keystrokes", id="keystroke-metric")
        yield MetricDisplay("Clicks", id="click-metric")

        yield Static("─" * 50, classes="section-divider")

        with Container(classes="current-info"):
            with Horizontal():
                yield Label("Current:", classes="info-label")
                yield Label(
                    self.current_window or "None",
                    classes="info-value",
                    id="current-window",
                )

            with Horizontal():
                yield Label("Status:", classes="info-label")
                yield Label(
                    self.status,
                    classes="info-value status-active"
                    if self.status == "ACTIVE"
                    else "info-value status-idle",
                    id="status-label",
                )
                yield Label(
                    self.session_duration, classes="session-time", id="session-time"
                )

    def update_metrics(
        self,
        keystrokes: int = 0,
        clicks: int = 0,
        keys_per_min: int = 0,
        clicks_per_min: int = 0,
        current_window: str = "",
        status: str = "ACTIVE",
        session_duration: str = "00:00:00",
    ) -> None:
        """Update all metrics at once."""
        self.keystrokes = keystrokes
        self.clicks = clicks
        self.keys_per_min = keys_per_min
        self.clicks_per_min = clicks_per_min
        self.current_window = current_window
        self.status = status
        self.session_duration = session_duration

        # Update metric displays
        try:
            self.query_one("#keystroke-metric", MetricDisplay).update(
                keystrokes, keys_per_min
            )
            self.query_one("#click-metric", MetricDisplay).update(
                clicks, clicks_per_min
            )
            self.query_one("#current-window", Label).update(current_window or "None")

            status_label = self.query_one("#status-label", Label)
            status_label.update(status)
            status_label.set_classes(
                "info-value status-active"
                if status == "ACTIVE"
                else "info-value status-idle"
            )

            self.query_one("#session-time", Label).update(session_duration)
        except Exception:
            pass  # Widgets not mounted yet

    def add_keystroke_sample(self, value: float) -> None:
        """Add a keystroke rate sample for sparkline."""
        self.keystroke_history.append(value)
        if len(self.keystroke_history) > 60:
            self.keystroke_history = self.keystroke_history[-60:]
        try:
            self.query_one("#keystroke-metric", MetricDisplay).add_sample(value)
        except Exception:
            pass

    def add_click_sample(self, value: float) -> None:
        """Add a click rate sample for sparkline."""
        self.click_history.append(value)
        if len(self.click_history) > 60:
            self.click_history = self.click_history[-60:]
        try:
            self.query_one("#click-metric", MetricDisplay).add_sample(value)
        except Exception:
            pass
