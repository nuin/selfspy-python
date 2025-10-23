from typing import Dict, Optional, Tuple

from .base import WindowTracker


class FallbackWindowTracker(WindowTracker):
    """Basic window tracker that works without system-specific APIs"""

    async def get_active_window(self) -> Dict[str, str]:
        """Get basic window info"""
        return {"process": "unknown", "title": "unknown", "bundle": "unknown"}

    def get_window_geometry(self) -> Optional[Tuple[int, int, int, int]]:
        """Get window geometry"""
        return (0, 0, 0, 0)
