"""
AppsTab - Application activity breakdown

Displays a sortable table of applications with keystroke/click counts
and activity percentages, with visual progress bars.
"""

from dataclasses import dataclass
from typing import List

from rich.text import Text
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import DataTable, Static


@dataclass
class AppData:
    """Application activity data."""

    name: str
    keystrokes: int
    clicks: int
    activity_percent: float


class AppsTab(Static):
    """Application activity breakdown tab.

    Shows a scrollable, sortable table of applications with their
    keystroke/click counts and activity percentages.
    """

    DEFAULT_CSS = """
    AppsTab {
        padding: 1 2;
    }

    AppsTab DataTable {
        height: 100%;
    }
    """

    apps: reactive[List[AppData]] = reactive(list, init=False)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apps: List[AppData] = []

    @property
    def apps(self) -> List[AppData]:
        """Get the current apps list."""
        return self._apps

    def compose(self) -> ComposeResult:
        table = DataTable(id="apps-table")
        table.cursor_type = "row"
        table.zebra_stripes = True
        yield table

    def on_mount(self) -> None:
        """Set up the table columns when mounted."""
        table = self.query_one("#apps-table", DataTable)
        table.add_columns("App", "Keys", "Clicks", "Activity")

    def _render_progress_bar(self, percent: float) -> Text:
        """Render a progress bar for activity percentage.

        Args:
            percent: Activity percentage (0-100)

        Returns:
            Rich Text with progress bar
        """
        filled = int(percent / 10)  # 10 chars max
        empty = 10 - filled
        bar = "\u2588" * filled + "\u2591" * empty
        return Text(f"{bar} {percent:5.1f}%")

    def update_apps(self, apps: List[AppData]) -> None:
        """Update the application list.

        Args:
            apps: List of AppData to display (will be sorted by activity)
        """
        # Sort by activity percent descending
        self._apps = sorted(apps, key=lambda a: a.activity_percent, reverse=True)
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh the table with current data."""
        try:
            table = self.query_one("#apps-table", DataTable)
            table.clear()

            for app in self._apps:
                table.add_row(
                    app.name,
                    f"{app.keystrokes:,}",
                    f"{app.clicks:,}",
                    self._render_progress_bar(app.activity_percent),
                )
        except Exception:
            pass  # Widget not mounted yet

    def add_or_update_app(self, app: AppData) -> None:
        """Add or update a single app in the list.

        Args:
            app: AppData to add or update
        """
        # Find existing app by name
        for i, existing in enumerate(self._apps):
            if existing.name == app.name:
                self._apps[i] = app
                break
        else:
            self._apps.append(app)

        # Re-sort
        self._apps = sorted(self._apps, key=lambda a: a.activity_percent, reverse=True)
        self._refresh_table()
