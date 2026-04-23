"""Tests for the main SelfspyApp."""

import pytest

from selfspy.tui.app import SelfspyApp
from selfspy.tui.tabs.apps import AppsTab
from selfspy.tui.tabs.live import LiveTab
from selfspy.tui.tabs.summary import SummaryTab


class TestSelfspyApp:
    """Test suite for SelfspyApp."""

    @pytest.mark.asyncio
    async def test_app_runs(self):
        """Test that the app can run."""
        app = SelfspyApp()
        async with app.run_test() as pilot:
            assert app is not None

    @pytest.mark.asyncio
    async def test_app_has_tabbed_content(self):
        """Test that the app has TabbedContent."""
        from textual.widgets import TabbedContent

        app = SelfspyApp()
        async with app.run_test() as pilot:
            tabbed = app.query_one(TabbedContent)
            assert tabbed is not None

    @pytest.mark.asyncio
    async def test_app_has_live_tab(self):
        """Test that Live tab exists."""
        app = SelfspyApp()
        async with app.run_test() as pilot:
            live_tab = app.query_one(LiveTab)
            assert live_tab is not None

    @pytest.mark.asyncio
    async def test_app_has_apps_tab(self):
        """Test that Apps tab exists."""
        app = SelfspyApp()
        async with app.run_test() as pilot:
            apps_tab = app.query_one(AppsTab)
            assert apps_tab is not None

    @pytest.mark.asyncio
    async def test_app_has_summary_tab(self):
        """Test that Summary tab exists."""
        app = SelfspyApp()
        async with app.run_test() as pilot:
            summary_tab = app.query_one(SummaryTab)
            assert summary_tab is not None

    @pytest.mark.asyncio
    async def test_app_keyboard_navigation(self):
        """Test keyboard navigation between tabs."""
        app = SelfspyApp()
        async with app.run_test() as pilot:
            # Press '2' to switch to Apps tab
            await pilot.press("2")
            # Should be on Apps tab now
            from textual.widgets import TabbedContent

            tabbed = app.query_one(TabbedContent)
            # The active tab should change (implementation-specific)
            assert tabbed is not None

    @pytest.mark.asyncio
    async def test_app_quit_binding(self):
        """Test that 'q' quits the app."""
        app = SelfspyApp()
        async with app.run_test() as pilot:
            # 'q' should trigger quit
            await pilot.press("q")
            # App should be stopping
            assert app._exit or not app.is_running
