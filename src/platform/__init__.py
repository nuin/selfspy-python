# src/platform/__init__.py
"""
Platform-specific implementations for Selfspy
"""

from .darwin import MacOSWindowTracker
from .screen_capture import MacScreenCapture
from .input_tracker import InputTracker

__all__ = ['MacOSWindowTracker', 'MacScreenCapture', 'InputTracker']