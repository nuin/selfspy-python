"""
Selfspy - A tool for monitoring and analyzing your computer activity
"""
from pathlib import Path

__version__ = "1.0.0"
__author__ = "nuin"
__email__ = "nuin@genedrift.org"

# Add src directory to Python path
import sys
src_path = str(Path(__file__).parent.absolute())
if src_path not in sys.path:
    sys.path.append(src_path)

from monitor import ActivityMonitor
from activity_store import ActivityStore
from models import Process, Window, Keys, Click

__all__ = [
    'ActivityMonitor',
    'ActivityStore',
    'Process',
    'Window',
    'Keys',
    'Click',
]