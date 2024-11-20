"""
macOS-specific window and process monitoring using PyObjC
"""
import asyncio
from datetime import datetime
from typing import Dict, Optional, Tuple

import Quartz
import AppKit
from pynput import keyboard, mouse

from .input_tracker import InputTracker

class MacOSInputTracker(InputTracker):
    """MacOS input tracking implementation"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keyboard_listener = None
        self.mouse_listener = None
        
    def start(self):
        """Start input tracking"""
        super().start()
        
        # Initialize keyboard listener
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        
        # Initialize mouse listener
        self.mouse_listener = mouse.Listener(
            on_move=self.on_mouse_move,
            on_click=self.on_mouse_click,
            on_scroll=self.on_scroll
        )
        
        # Start listeners
        self.keyboard_listener.start()
        self.mouse_listener.start()
        
    def stop(self):
        """Stop input tracking"""
        super().stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()

class MacOSWindowTracker:
    """Track active window and process information on macOS"""
    
    def __init__(self):
        self.workspace = AppKit.NSWorkspace.sharedWorkspace()
    
    def cleanup(self):
        """Cleanup resources"""
        pass
        
    async def get_active_window(self) -> Optional[Dict[str, str]]:
        """Get active window information"""
        try:
            workspace = Quartz.NSWorkspace.sharedWorkspace()
            active_app = workspace.activeApplication()
            
            if active_app:
                return {
                    'title': str(active_app['NSApplicationName']),
                    'process': str(active_app['NSApplicationName'])
                }
        except Exception:
            pass
        return None
    
    def get_window_geometry(self) -> Tuple[int, int, int, int]:
        """Get current window geometry"""
        try:
            # Get frontmost app info
            app_info = self.workspace.activeApplication()
            if not app_info:
                return (0, 0, 0, 0)
            
            # Get window bounds
            pid = app_info['NSApplicationProcessIdentifier']
            app = AppKit.NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
            if not app:
                return (0, 0, 0, 0)
            
            # Get window bounds from Accessibility API
            import ApplicationServices as AS
            element = AS.AXUIElementCreateApplication(pid)
            window = None
            
            AS.AXUIElementCopyAttributeValue(element, AS.kAXFocusedWindowAttribute, window)
            if not window:
                return (0, 0, 0, 0)
            
            position = AS.AXValueCreate(AS.kAXValueCGPointType, None)
            size = AS.AXValueCreate(AS.kAXValueCGSizeType, None)
            
            AS.AXUIElementCopyAttributeValue(window, AS.kAXPositionAttribute, position)
            AS.AXUIElementCopyAttributeValue(window, AS.kAXSizeAttribute, size)
            
            x = int(position.x)
            y = int(position.y)
            width = int(size.width)
            height = int(size.height)
            
            return (x, y, width, height)
            
        except Exception:
            return (0, 0, 0, 0)
    
    def _get_window_title(self, app_info: dict) -> str:
        """Get window title for application"""
        try:
            pid = app_info['NSApplicationProcessIdentifier']
            app = AppKit.NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
            if app:
                return app.localizedName() or 'unknown'
        except:
            pass
        return 'unknown'
    
    def _get_window_frame(self) -> Optional[AppKit.NSRect]:
        """Get frame of active window"""
        try:
            windows = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly | 
                Quartz.kCGWindowListExcludeDesktopElements,
                Quartz.kCGNullWindowID
            )
            if windows and windows[0]:
                bounds = windows[0].get(Quartz.kCGWindowBounds)
                if bounds:
                    return AppKit.NSRect(bounds)
        except:
            pass
        return None