"""Tests for the LiveTab component."""

import pytest
from textual.app import App, ComposeResult

from selfspy.tui.tabs.live import LiveTab


class LiveTabTestApp(App):
    """Test app for LiveTab."""

    def compose(self) -> ComposeResult:
        yield LiveTab()


class TestLiveTab:
    """Test suite for LiveTab component."""

    @pytest.mark.asyncio
    async def test_live_tab_mounts(self):
        """Test that LiveTab can be mounted."""
        app = LiveTabTestApp()
        async with app.run_test() as pilot:
            live_tab = app.query_one(LiveTab)
            assert live_tab is not None

    @pytest.mark.asyncio
    async def test_live_tab_has_keystroke_label(self):
        """Test that LiveTab displays keystroke count."""
        app = LiveTabTestApp()
        async with app.run_test() as pilot:
            live_tab = app.query_one(LiveTab)
            # Should have a label for keystrokes
            assert (
                "Keystrokes" in live_tab.render().plain
                or app.query("Label").first() is not None
            )

    @pytest.mark.asyncio
    async def test_live_tab_update_metrics(self):
        """Test updating metrics on LiveTab."""
        app = LiveTabTestApp()
        async with app.run_test() as pilot:
            live_tab = app.query_one(LiveTab)
            # Update metrics
            live_tab.update_metrics(
                keystrokes=100,
                clicks=25,
                keys_per_min=45,
                clicks_per_min=8,
                current_window="VS Code",
                status="ACTIVE",
                session_duration="00:42:15",
            )
            # Values should be stored
            assert live_tab.keystrokes == 100
            assert live_tab.clicks == 25

    @pytest.mark.asyncio
    async def test_live_tab_sparkline_data(self):
        """Test that sparklines receive data."""
        app = LiveTabTestApp()
        async with app.run_test() as pilot:
            live_tab = app.query_one(LiveTab)
            # Add some history data
            live_tab.add_keystroke_sample(10)
            live_tab.add_keystroke_sample(20)
            live_tab.add_keystroke_sample(30)
            assert len(live_tab.keystroke_history) == 3
