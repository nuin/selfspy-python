from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple


class WindowTracker(ABC):
    """Abstract base class for window tracking"""

    @abstractmethod
    async def get_active_window(self) -> Dict[str, str]:
        """Get information about the currently active window"""
        pass

    @abstractmethod
    def get_window_geometry(self) -> Optional[Tuple[int, int, int, int]]:
        """Get window geometry (x, y, width, height)"""
        pass

    def cleanup(self):
        """Cleanup resources"""
        pass
