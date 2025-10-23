"""
Enhanced macOS input tracking implementation with proper event handling
"""

import AppKit
import Quartz
import structlog
from pynput.keyboard import Key
from pynput.mouse import Button

from .input_tracker import InputTracker

logger = structlog.get_logger()


class MacOSInputTracker(InputTracker):
    """Track keyboard and mouse input using native macOS APIs"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_tap = None
        self.run_loop = None

    def start(self):
        """Start input tracking using CGEventTap"""
        super().start()

        # Create event tap for keyboard and mouse events
        mask = (
            Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
            | Quartz.CGEventMaskBit(Quartz.kCGEventLeftMouseDown)
            | Quartz.CGEventMaskBit(Quartz.kCGEventRightMouseDown)
            | Quartz.CGEventMaskBit(Quartz.kCGEventScrollWheel)
        )

        self.event_tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            mask,
            self._event_callback,
            None,
        )

        if self.event_tap:
            # Enable the event tap
            Quartz.CGEventTapEnable(self.event_tap, True)

            # Create and add the run loop source
            run_loop_source = Quartz.CGEventTapCreateRunLoopSource(
                None, self.event_tap, 0
            )

            # Get the current run loop
            self.run_loop = Quartz.CFRunLoopGetCurrent()
            Quartz.CFRunLoopAddSource(
                self.run_loop, run_loop_source, Quartz.kCFRunLoopCommonModes
            )

            logger.info("MacOS input tracking started")
            return True

        logger.error("Failed to create event tap")
        return False

    def _event_callback(self, proxy, event_type, event, refcon):
        """Handle input events from CGEventTap"""
        try:
            if event_type == Quartz.kCGEventKeyDown and self.on_key_press:
                # Get key info
                keycode = Quartz.CGEventGetIntegerValueField(
                    event, Quartz.kCGKeyboardEventKeycode
                )
                self.on_key_press(Key(keycode))

            elif event_type == Quartz.kCGEventLeftMouseDown and self.on_mouse_click:
                # Get mouse coordinates
                point = Quartz.CGEventGetLocation(event)
                self.on_mouse_click(int(point.x), int(point.y), Button.left, True)

            elif event_type == Quartz.kCGEventRightMouseDown and self.on_mouse_click:
                point = Quartz.CGEventGetLocation(event)
                self.on_mouse_click(int(point.x), int(point.y), Button.right, True)

            elif event_type == Quartz.kCGEventScrollWheel and self.on_scroll:
                # Get scroll deltas
                dy = Quartz.CGEventGetIntegerValueField(
                    event, Quartz.kCGScrollWheelEventDeltaAxis1
                )
                dx = Quartz.CGEventGetIntegerValueField(
                    event, Quartz.kCGScrollWheelEventDeltaAxis2
                )
                point = Quartz.CGEventGetLocation(event)
                self.on_scroll(int(point.x), int(point.y), dx, dy)

        except Exception as e:
            logger.error("Event callback error", error=str(e))

        return event

    def _keycode_to_key(self, keycode: int):
        """Convert macOS keycode to pynput key"""
        try:
            # Get character from keycode
            keyboard = AppKit.NSEvent.keyboardLayout()
            if not keyboard:
                return None

            # Get characters for keycode
            chars = keyboard.keyStringForKeyCode_modifierFlags_(keycode, 0)
            if chars and len(chars) > 0:
                return Key.from_char(chars[0])
            return None

        except Exception:
            return None

    def stop(self):
        """Stop input tracking"""
        super().stop()
        if self.event_tap:
            Quartz.CGEventTapEnable(self.event_tap, False)
            self.event_tap = None
            logger.info("MacOS input tracking stopped")
