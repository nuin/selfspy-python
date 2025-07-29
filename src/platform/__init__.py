# src/platform/__init__.py
"""
Platform-specific implementations for Selfspy
"""

from .darwin import MacOSWindowTracker
from .input_tracker import InputTracker
from .screen_capture import MacScreenCapture

__all__ = ["MacOSWindowTracker", "MacScreenCapture", "InputTracker"]
