"""
Selfspy TUI - Textual-based Terminal User Interface

A tabbed interface for real-time activity monitoring with three focused views:
- Live: Real-time keystroke/click feedback with sparklines
- Apps: Application activity breakdown
- Summary: Session statistics and comparisons
"""

from .app import SelfspyApp
from .tabs import AppsTab, LiveTab, SummaryTab
from .widgets import Sparkline

__all__ = [
    "AppsTab",
    "LiveTab",
    "SelfspyApp",
    "Sparkline",
    "SummaryTab",
]
