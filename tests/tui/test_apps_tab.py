"""Tests for the AppsTab component."""

import pytest
from src.tui.tabs.apps import AppData, AppsTab
from textual.app import App, ComposeResult


class AppsTabTestApp(App):
    """Test app for AppsTab."""

    def compose(self) -> ComposeResult:
        yield AppsTab()


class TestAppData:
    """Test suite for AppData dataclass."""

    def test_app_data_creation(self):
        """Test AppData can be created."""
        app = AppData(
            name="VS Code",
            keystrokes=500,
            clicks=100,
            activity_percent=62.5,
        )
        assert app.name == "VS Code"
        assert app.keystrokes == 500
        assert app.clicks == 100
        assert app.activity_percent == 62.5


class TestAppsTab:
    """Test suite for AppsTab component."""

    @pytest.mark.asyncio
    async def test_apps_tab_mounts(self):
        """Test that AppsTab can be mounted."""
        app = AppsTabTestApp()
        async with app.run_test() as pilot:
            apps_tab = app.query_one(AppsTab)
            assert apps_tab is not None

    @pytest.mark.asyncio
    async def test_apps_tab_has_table(self):
        """Test that AppsTab has a data table."""
        app = AppsTabTestApp()
        async with app.run_test() as pilot:
            apps_tab = app.query_one(AppsTab)
            # Should have a DataTable
            from textual.widgets import DataTable

            table = apps_tab.query_one(DataTable)
            assert table is not None

    @pytest.mark.asyncio
    async def test_apps_tab_update_apps(self):
        """Test updating app data."""
        app = AppsTabTestApp()
        async with app.run_test() as pilot:
            apps_tab = app.query_one(AppsTab)
            apps_tab.update_apps(
                [
                    AppData("VS Code", 500, 100, 62.5),
                    AppData("Firefox", 200, 50, 25.0),
                ]
            )
            assert len(apps_tab.apps) == 2

    @pytest.mark.asyncio
    async def test_apps_tab_sort_by_activity(self):
        """Test that apps are sorted by activity percent."""
        app = AppsTabTestApp()
        async with app.run_test() as pilot:
            apps_tab = app.query_one(AppsTab)
            apps_tab.update_apps(
                [
                    AppData("Low Activity", 50, 10, 10.0),
                    AppData("High Activity", 500, 100, 80.0),
                    AppData("Medium Activity", 200, 50, 40.0),
                ]
            )
            # First app should be highest activity
            assert apps_tab.apps[0].name == "High Activity"
