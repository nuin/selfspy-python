"""Tests for storage.Store."""

import pytest
import pytest_asyncio
from sqlalchemy import select

from selfspy.core import Settings
from selfspy.storage import Keys, Store


@pytest_asyncio.fixture
async def store(tmp_path):
    settings = Settings(data_dir=tmp_path, encryption_enabled=False)
    store = Store(settings, password=None)
    await store.initialize()
    yield store
    await store.close()


@pytest.mark.asyncio
async def test_store_initialize_creates_schema(store):
    # initialize() ran in fixture; verify a session can be opened
    async with store.async_session() as session:
        assert session is not None


@pytest.mark.asyncio
async def test_store_start_session_returns_id(store):
    session_id = await store.start_session()
    assert isinstance(session_id, int)
    assert session_id > 0


@pytest.mark.asyncio
async def test_store_update_window_info_creates_process_and_window(store):
    await store.start_session()
    await store.update_window_info("Terminal", "bash - ~", "com.apple.Terminal")
    assert store.current_process_id is not None
    assert store.current_window_id is not None


@pytest.mark.asyncio
async def test_store_store_keys_requires_window(store):
    await store.start_session()
    # No window set yet; should silently no-op
    await store.store_keys("hello")
    # No exception raised


@pytest.mark.asyncio
async def test_store_store_keys_writes_after_window_set(store):
    await store.start_session()
    await store.update_window_info("Terminal", "bash - ~", "com.apple.Terminal")
    await store.store_keys("hello")

    async with store.async_session() as session:
        result = await session.execute(select(Keys))
        keys = result.scalars().all()
        assert len(keys) == 1
        assert keys[0].count == 5
