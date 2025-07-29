"""
Pytest configuration and fixtures
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Add src to Python path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from src.activity_store import ActivityStore
from src.config import Settings
from src.models import Base


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for test data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture(scope="session")
def db_path(temp_dir):
    """Create a test database path"""
    return os.path.join(temp_dir, "test.db")


@pytest.fixture(scope="function")
def db_session(db_path):
    """Create a new database session for a test"""
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            yield session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture(scope="function")
def activity_store(temp_dir):
    """Create a test activity store"""
    settings = Settings(data_dir=temp_dir, debug=True)
    store = ActivityStore(settings, password="test")
    try:
        yield store
    finally:
        # Clean up async resources
        import asyncio

        try:
            asyncio.run(store.engine.dispose())
        except Exception:
            pass
