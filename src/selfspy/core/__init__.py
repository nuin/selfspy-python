"""Core orchestration: config, lifecycle, and monitor.

Only ``Settings`` is re-exported eagerly. ``Monitor`` and ``run_monitor`` pull in
platform-specific dependencies (pynput, AppKit) and must be imported from their
submodules (``selfspy.core.monitor``, ``selfspy.core.lifecycle``) so that
non-monitoring consumers (tests, analytics, CLI subcommands that only need
config) can import this package on any platform.
"""

from .config import Settings

__all__ = ["Settings"]
