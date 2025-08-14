"""
Tests for database models
"""

import sys
from pathlib import Path

# Add src to Python path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from src.models import Process, Window


def test_process_creation(db_session):
    """Test creating a process"""
    process = Process(name="test_process")
    db_session.add(process)
    db_session.commit()

    retrieved = db_session.query(Process).filter_by(name="test_process").first()
    assert retrieved is not None
    assert retrieved.name == "test_process"


def test_window_creation(db_session):
    """Test creating a window with associated process"""
    # Create process first
    process = Process(name="test_process")
    db_session.add(process)
    db_session.commit()

    # Create window
    window = Window(title="test_window", process_id=process.id)
    db_session.add(window)
    db_session.commit()

    # Test retrieval
    retrieved = db_session.query(Window).filter_by(title="test_window").first()
    assert retrieved is not None
    assert retrieved.title == "test_window"
    assert retrieved.process.name == "test_process"
