"""Tests for the SummaryTab component."""

import pytest
from textual.app import App, ComposeResult

from selfspy.tui.tabs.summary import SummaryTab


class SummaryTabTestApp(App):
    """Test app for SummaryTab."""

    def compose(self) -> ComposeResult:
        yield SummaryTab()


class TestSummaryTab:
    """Test suite for SummaryTab component."""

    @pytest.mark.asyncio
    async def test_summary_tab_mounts(self):
        """Test that SummaryTab can be mounted."""
        app = SummaryTabTestApp()
        async with app.run_test() as pilot:
            summary_tab = app.query_one(SummaryTab)
            assert summary_tab is not None

    @pytest.mark.asyncio
    async def test_summary_tab_has_metrics(self):
        """Test that SummaryTab displays session metrics."""
        app = SummaryTabTestApp()
        async with app.run_test() as pilot:
            summary_tab = app.query_one(SummaryTab)
            # Should have labels for metrics
            labels = app.query("Label")
            assert len(list(labels)) > 0

    @pytest.mark.asyncio
    async def test_summary_tab_update_stats(self):
        """Test updating stats on SummaryTab."""
        app = SummaryTabTestApp()
        async with app.run_test() as pilot:
            summary_tab = app.query_one(SummaryTab)
            summary_tab.update_stats(
                session_duration="02:15:30",
                active_time="01:52:00",
                active_percent=83.0,
                idle_time="00:23:30",
                idle_percent=17.0,
                total_keystrokes=4521,
                total_clicks=342,
                windows_switched=47,
            )
            # Values should be stored
            assert summary_tab.session_duration == "02:15:30"
            assert summary_tab.total_keystrokes == 4521

    @pytest.mark.asyncio
    async def test_summary_tab_yesterday_comparison(self):
        """Test yesterday comparison display."""
        app = SummaryTabTestApp()
        async with app.run_test() as pilot:
            summary_tab = app.query_one(SummaryTab)
            summary_tab.set_yesterday_comparison(12.5, more_active=True)
            assert summary_tab.yesterday_diff == 12.5
            assert summary_tab.more_active_than_yesterday is True

    @pytest.mark.asyncio
    async def test_summary_tab_negative_comparison(self):
        """Test negative yesterday comparison."""
        app = SummaryTabTestApp()
        async with app.run_test() as pilot:
            summary_tab = app.query_one(SummaryTab)
            summary_tab.set_yesterday_comparison(8.0, more_active=False)
            assert summary_tab.yesterday_diff == 8.0
            assert summary_tab.more_active_than_yesterday is False
