"""Tracking layer: input, window, terminal capture and permissions."""

from .permissions import (
    check_and_request_permissions,
    check_macos_permissions,
)
from .terminal import TerminalTracker

__all__ = [
    "TerminalTracker",
    "check_and_request_permissions",
    "check_macos_permissions",
]
