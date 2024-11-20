"""
macOS-specific window and process monitoring using PyObjC
"""
import asyncio
from datetime import datetime
from typing import Dict, Optional, Tuple

import Quartz
import AppKit

class MacOSWindowTracker:
    """Track active window and process information on macOS"""
    
    def __init__(self):
        self.workspace = AppKit.NSWorkspace.sharedWorkspace()
    
    def cleanup(self):
        """Cleanup resources"""
        pass
        
    async def get_active_window(self) -> Dict[str, str]:
        """Get current active window information"""
        active_app = self.workspace.activeApplication()
        
        if not active_app:
            return {
                'process': 'unknown',
                'title': 'unknown',
                'bundle': 'unknown'
            }
            
        return {
            'process': active_app['NSApplicationName'],
            'title': self._get_window_title(active_app),
            'bundle': active_app['NSApplicationBundleIdentifier']
        }
    
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