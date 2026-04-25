"""
SelfspyApp - Main Textual application

The primary TUI application with tabbed interface for Live, Apps, and Summary views.
"""

from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane

from .tabs.apps import AppData, AppsTab
from .tabs.live import LiveTab
from .tabs.summary import SummaryTab


class SelfspyApp(App):
    """Selfspy TUI Application.

    A tabbed interface for real-time activity monitoring:
    - Live: Real-time keystroke/click feedback with sparklines
    - Apps: Application activity breakdown
    - Summary: Session statistics and comparisons
    """

    CSS = """
    Screen {
        background: $surface;
    }

    TabbedContent {
        height: 100%;
    }

    TabPane {
        padding: 0;
    }

    Header {
        dock: top;
    }

    Footer {
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("1", "switch_tab('live')", "Live", show=True),
        Binding("2", "switch_tab('apps')", "Apps", show=True),
        Binding("3", "switch_tab('summary')", "Summary", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    TITLE = "Selfspy"
    SUB_TITLE = "Activity Monitor"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._monitor_state: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Create the app layout."""
        yield Header()
        with TabbedContent(initial="live"):
            with TabPane("Live", id="live"):
                yield LiveTab(id="live-tab")
            with TabPane("Apps", id="apps"):
                yield AppsTab(id="apps-tab")
            with TabPane("Summary", id="summary"):
                yield SummaryTab(id="summary-tab")
        yield Footer()

    def action_switch_tab(self, tab_id: str) -> None:
        """Switch to a specific tab.

        Args:
            tab_id: The ID of the tab to switch to
        """
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = tab_id

    def update_live_metrics(
        self,
        keystrokes: int = 0,
        clicks: int = 0,
        keys_per_min: int = 0,
        clicks_per_min: int = 0,
        current_window: str = "",
        status: str = "ACTIVE",
        session_duration: str = "00:00:00",
    ) -> None:
        """Update live tab metrics.

        Called by ActivityMonitor to update real-time display.
        """
        try:
            live_tab = self.query_one("#live-tab", LiveTab)
            live_tab.update_metrics(
                keystrokes=keystrokes,
                clicks=clicks,
                keys_per_min=keys_per_min,
                clicks_per_min=clicks_per_min,
                current_window=current_window,
                status=status,
                session_duration=session_duration,
            )
        except Exception:
            pass

    def add_activity_samples(self, keystroke_rate: float, click_rate: float) -> None:
        """Add activity rate samples to sparklines.

        Args:
            keystroke_rate: Current keystroke rate (per minute)
            click_rate: Current click rate (per minute)
        """
        try:
            live_tab = self.query_one("#live-tab", LiveTab)
            live_tab.add_keystroke_sample(keystroke_rate)
            live_tab.add_click_sample(click_rate)
        except Exception:
            pass

    def update_apps(self, apps: list[AppData]) -> None:
        """Update the apps tab with application data.

        Args:
            apps: List of AppData to display
        """
        try:
            apps_tab = self.query_one("#apps-tab", AppsTab)
            apps_tab.update_apps(apps)
        except Exception:
            pass

    def update_summary(
        self,
        session_duration: str = "00:00:00",
        active_time: str = "00:00:00",
        active_percent: float = 0.0,
        idle_time: str = "00:00:00",
        idle_percent: float = 0.0,
        total_keystrokes: int = 0,
        total_clicks: int = 0,
        windows_switched: int = 0,
        yesterday_diff: float | None = None,
        more_active: bool = True,
    ) -> None:
        """Update the summary tab with session statistics.

        Args:
            session_duration: Total session duration string
            active_time: Active time string
            active_percent: Percentage of time active
            idle_time: Idle time string
            idle_percent: Percentage of time idle
            total_keystrokes: Total keystroke count
            total_clicks: Total click count
            windows_switched: Number of window switches
            yesterday_diff: Percentage difference from yesterday (optional)
            more_active: True if more active than yesterday
        """
        try:
            summary_tab = self.query_one("#summary-tab", SummaryTab)
            summary_tab.update_stats(
                session_duration=session_duration,
                active_time=active_time,
                active_percent=active_percent,
                idle_time=idle_time,
                idle_percent=idle_percent,
                total_keystrokes=total_keystrokes,
                total_clicks=total_clicks,
                windows_switched=windows_switched,
            )
            if yesterday_diff is not None:
                summary_tab.set_yesterday_comparison(yesterday_diff, more_active)
        except Exception:
            pass

    def set_monitor_state(self, state: dict[str, Any]) -> None:
        """Set the monitor state reference.

        This allows the app to access ActivityMonitor state for polling.

        Args:
            state: Reference to ActivityMonitor's state dictionary
        """
        self._monitor_state = state
