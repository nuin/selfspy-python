"""
Platform-agnostic input tracking implementation
"""

from collections.abc import Callable


class InputTracker:
    """Track keyboard and mouse input"""

    def __init__(
        self,
        on_key_press: Callable | None = None,
        on_key_release: Callable | None = None,
        on_mouse_move: Callable | None = None,
        on_mouse_click: Callable | None = None,
        on_scroll: Callable | None = None,
    ):
        self.on_key_press = on_key_press
        self.on_key_release = on_key_release
        self.on_mouse_move = on_mouse_move
        self.on_mouse_click = on_mouse_click
        self.on_scroll = on_scroll
        self.running = False

    def start(self):
        """Start input tracking"""
        self.running = True

    def stop(self):
        """Stop input tracking"""
        self.running = False
