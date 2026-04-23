from abc import ABC, abstractmethod


class WindowTracker(ABC):
    """Abstract base class for window tracking"""

    @abstractmethod
    async def get_active_window(self) -> dict[str, str]:
        """Get information about the currently active window"""
        pass

    @abstractmethod
    def get_window_geometry(self) -> tuple[int, int, int, int] | None:
        """Get window geometry (x, y, width, height)"""
        pass

    def cleanup(self):
        """Cleanup resources"""
        pass
