"""
macOS-specific window and process monitoring using NSWorkspace and Quartz
"""
import asyncio
from datetime import datetime
import time
from typing import Dict, Optional, Tuple

import Quartz
from Foundation import (
    NSWorkspace,
    NSNotificationCenter,
    NSRunLoop,
    NSDate,
    NSObject,
    NSMakeRect
)

class MacOSWindowObserver:
    """Observer for macOS window and workspace notifications"""
    
    def __init__(self):
        self.workspace = NSWorkspace.sharedWorkspace()
        self._setup_observers()
        self.current_app = None
        
    def _setup_observers(self):
        """Set up workspace notifications"""
        notification_center = self.workspace.notificationCenter()
        
        # Register for active application changes
        notification_center.addObserver_selector_name_object_(
            self,
            'applicationActivated:',
            'NSWorkspaceDidActivateApplicationNotification',
            None
        )
        
        # Register for window focus changes
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self,
            'windowFocused:',
            'NSWindowDidBecomeMainNotification',
            None
        )

    def applicationActivated_(self, notification):
        """Handle application activation"""
        self.current_app = notification.userInfo()['NSWorkspaceApplicationKey']

    def windowFocused_(self, notification):
        """Handle window focus changes"""
        pass

    def cleanup(self):
        """Remove notification observers"""
        NSNotificationCenter.defaultCenter().removeObserver_(self)
        self.workspace.notificationCenter().removeObserver_(self)

class MacOSWindowTracker:
    """Track active window and process information on macOS"""
    
    def __init__(self):
        self.observer = MacOSWindowObserver()
        
    async def get_active_window(self) -> Dict[str, str]:
        """Get current active window information"""
        workspace = NSWorkspace.sharedWorkspace()
        active_app = workspace.activeApplication()
        
        if not active_app:
            return {
                'process': 'unknown',
                'title': 'unknown',
                'bundle': 'unknown'
            }
            
        process_name = active_app['NSApplicationName']
        bundle_id = active_app['NSApplicationBundleIdentifier']
        window_title = await self._get_window_title()
        
        return {
            'process': process_name,
            'title': window_title,
            'bundle': bundle_id
        }
    
    async def _get_window_title(self) -> str:
        """Get the title of the active window using Quartz"""
        windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | 
            Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        )
        
        if not windows:
            return ''
            
        for window in windows:
            # Check if window is active/main
            if window.get(Quartz.kCGWindowLayer, 0) == 0:
                return window.get(Quartz.kCGWindowName, '')
                
        return ''
    
    def get_window_geometry(self) -> Tuple[int, int, int, int]:
        """Get the geometry of the active window"""
        windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | 
            Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        )
        
        if not windows:
            return (0, 0, 0, 0)
            
        for window in windows:
            if window.get(Quartz.kCGWindowLayer, 0) == 0:
                bounds = window.get(Quartz.kCGWindowBounds)
                if bounds:
                    return (
                        int(bounds['X']),
                        int(bounds['Y']),
                        int(bounds['Width']),
                        int(bounds['Height'])
                    )
                    
        return (0, 0, 0, 0)
    
    @staticmethod
    def get_screen_info() -> Dict[str, int]:
        """Get information about connected displays"""
        main_screen = Quartz.CGMainDisplayBounds()
        display_count = len(Quartz.CGGetActiveDisplayList()[0])
        
        return {
            'primary_width': int(main_screen.size.width),
            'primary_height': int(main_screen.size.height),
            'display_count': display_count
        }
    
    def cleanup(self):
        """Clean up observers and resources"""
        self.observer.cleanup()