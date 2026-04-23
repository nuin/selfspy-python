"""
TUI Tab Components

Each tab provides a focused view of activity data:
- LiveTab: Real-time metrics with sparklines
- AppsTab: Application activity table
- SummaryTab: Session statistics
"""

from .apps import AppData, AppsTab
from .live import LiveTab
from .summary import SummaryTab

__all__ = ["AppData", "AppsTab", "LiveTab", "SummaryTab"]
