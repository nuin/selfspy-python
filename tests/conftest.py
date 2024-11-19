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
src_path = str(Path(__file__).parent.parent / 'src')
if src_path not in sys.path:
    sys.path.append(src_path)

from models import Base
from activity_store import ActivityStore

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
    
    with Session(engine) as session:
        yield session
        
    Base.metadata.drop_all(engine)
    
@pytest.fixture(scope="function")
def activity_store(db_path):
    """Create a test activity store"""
    store = ActivityStore(db_path, password="test")
    yield store
    store.close()