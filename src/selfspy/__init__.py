"""
Selfspy - A tool for monitoring and analyzing your computer activity
"""

import sys
from pathlib import Path

from .activity_monitor import ActivityMonitor
from .storage import Click, Keys, Process, Store, Window

__version__ = "1.0.0"
__author__ = "nuin"
__email__ = "nuin@genedrift.org"

# Add src directory to Python path
src_path = str(Path(__file__).parent.absolute())
if src_path not in sys.path:
    sys.path.append(src_path)

__all__ = [
    "ActivityMonitor",
    "Click",
    "Keys",
    "Process",
    "Store",
    "Window",
]
