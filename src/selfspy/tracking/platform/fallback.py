from .base import WindowTracker


class FallbackWindowTracker(WindowTracker):
    """Basic window tracker that works without system-specific APIs"""

    async def get_active_window(self) -> dict[str, str]:
        """Get basic window info"""
        return {"process": "unknown", "title": "unknown", "bundle": "unknown"}

    def get_window_geometry(self) -> tuple[int, int, int, int] | None:
        """Get window geometry"""
        return (0, 0, 0, 0)
