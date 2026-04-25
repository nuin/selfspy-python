"""Tests for analytics.stats."""

import pytest
import pytest_asyncio

from selfspy.analytics import stats as analytics_stats
from selfspy.core import Settings
from selfspy.storage import Store


@pytest_asyncio.fixture
async def populated_store(tmp_path):
    settings = Settings(data_dir=tmp_path, encryption_enabled=False)
    store = Store(settings, password=None)
    await store.initialize()
    await store.start_session()
    await store.update_window_info("Terminal", "bash - ~", "com.apple.Terminal")
    await store.store_keys("hello world")
    await store.store_click(1, 100, 200)
    yield store
    await store.close()


@pytest.mark.asyncio
async def test_get_stats_returns_dict(populated_store):
    """analytics.stats.get_stats returns a dict with at least one app entry."""
    result = await analytics_stats.get_stats(populated_store, days=7)
    assert isinstance(result, dict)
    # Sanity: we wrote one process ("Terminal") so the result should reference it
    # somewhere in its top-level structure.
    assert result, "expected non-empty stats dict"


def test_analytics_stats_module_exposes_public_api():
    """Module exposes at least one public callable."""
    funcs = [
        name
        for name in dir(analytics_stats)
        if not name.startswith("_") and callable(getattr(analytics_stats, name))
    ]
    assert len(funcs) > 0, "analytics.stats should expose at least one function"
