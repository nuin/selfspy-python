"""Tests for tracking.permissions."""

import platform

from selfspy.tracking.permissions import check_macos_permissions


def test_check_macos_permissions_on_non_macos():
    if platform.system() == "Darwin":
        # Skip on macOS — the result depends on system state
        return
    has_perms, msg = check_macos_permissions()
    assert has_perms is True
    assert "Not on macOS" in msg
