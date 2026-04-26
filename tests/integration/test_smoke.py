"""Smoke test: simulate input events and verify they reach the DB."""

import asyncio
from datetime import datetime

import pytest

# Importing Monitor pulls in pynput + macOS-only AppKit. Skip the entire module
# on platforms where these aren't available (e.g., headless Linux CI).
pytest.importorskip("AppKit")

from sqlalchemy import select  # noqa: E402

from selfspy.core import Settings  # noqa: E402
from selfspy.core.monitor import Monitor  # noqa: E402
from selfspy.storage import Click, Keys, Store  # noqa: E402

pytestmark = pytest.mark.macos


@pytest.mark.asyncio
async def test_buffer_flushes_keys_to_db(tmp_path):
    """Pushing keys onto the monitor's buffer results in DB writes after flush."""
    settings = Settings(
        data_dir=tmp_path,
        encryption_enabled=False,
        keystroke_buffer_timeout=0,  # force immediate flush
    )
    store = Store(settings, password=None)
    await store.initialize()
    await store.start_session()
    await store.update_window_info("Test", "Test Window", "")

    monitor = Monitor(settings, store, debug=True)
    monitor._loop = asyncio.get_running_loop()

    # Inject events directly (bypass pynput thread)
    monitor.buffer.put_nowait({"type": "key", "key": "h", "time": datetime.now()})
    monitor.buffer.put_nowait({"type": "key", "key": "i", "time": datetime.now()})

    await monitor._flush_buffer(force=True)

    async with store.async_session() as session:
        result = await session.execute(select(Keys))
        keys = result.scalars().all()
        assert len(keys) >= 1
        total_count = sum(k.count for k in keys)
        assert total_count == 2

    await store.close()


@pytest.mark.asyncio
async def test_buffer_flushes_clicks_to_db(tmp_path):
    """Pushing clicks onto the monitor's buffer results in DB writes after flush."""
    settings = Settings(
        data_dir=tmp_path,
        encryption_enabled=False,
        keystroke_buffer_timeout=0,
    )
    store = Store(settings, password=None)
    await store.initialize()
    await store.start_session()
    await store.update_window_info("Test", "Test Window", "")

    monitor = Monitor(settings, store, debug=True)
    monitor._loop = asyncio.get_running_loop()

    monitor.buffer.put_nowait(
        {"type": "click", "button": 1, "x": 10, "y": 20, "time": datetime.now()}
    )
    monitor.buffer.put_nowait(
        {"type": "click", "button": 3, "x": 30, "y": 40, "time": datetime.now()}
    )

    await monitor._flush_buffer(force=True)

    async with store.async_session() as session:
        result = await session.execute(select(Click))
        clicks = result.scalars().all()
        assert len(clicks) == 2
        coords = {(c.x, c.y) for c in clicks}
        assert coords == {(10, 20), (30, 40)}

    await store.close()
