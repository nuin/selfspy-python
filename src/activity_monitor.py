"""
Activity monitoring implementation
"""
import asyncio
import logging
import platform
from datetime import datetime
from typing import Optional, Dict, Any

import structlog
from pynput import mouse, keyboard

from .config import Settings
from .platform import MacOSWindowTracker, MacScreenCapture  # Updated import

import sys
from pathlib import Path

from .platform.input_tracker import InputTracker

logger = structlog.get_logger()


class ActivityMonitor:
    """Activity monitor implementation"""
    
    def __init__(
        self,
        settings: Settings,
        store: 'ActivityStore',
        debug: bool = False
    ):
        self.settings = settings
        self.store = store
        self.current_window: Optional[Dict[str, str]] = None
        self.buffer: list[Dict[str, Any]] = []
        self.last_activity = datetime.now()
        self.running = False
        
        # Configure logging
        log_level = logging.DEBUG if debug else logging.INFO
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(log_level)
        )
        
        # Initialize platform-specific window tracker
        try:
            if platform.system() == 'Darwin':
                from .platform.darwin import MacOSWindowTracker
                self.window_tracker = MacOSWindowTracker()
            else:
                from .platform.fallback import FallbackWindowTracker
                self.window_tracker = FallbackWindowTracker()
                logger.warning(f"Platform {platform.system()} has limited window tracking support")
        except Exception as e:
            logger.warning(f"Using fallback window tracker: {str(e)}")
            from .platform.fallback import FallbackWindowTracker
            self.window_tracker = FallbackWindowTracker()
        
        # Initialize input tracker
        self.input_tracker = InputTracker(
            on_key_press=self._on_key_press,
            on_key_release=self._on_key_release,
            on_mouse_move=self._on_mouse_move,
            on_mouse_click=self._on_mouse_click,
            on_scroll=self._on_scroll
        )

    async def start(self):
        """Start monitoring asynchronously"""
        logger.info("Starting activity monitor...")
        
        if not self._check_permissions():
            raise PermissionError(
                "Accessibility permissions required. Please enable in System Settings."
            )
        
        self.running = True
        self.input_tracker.start()
        
        # Start screen capture if enabled
        if hasattr(self, 'screen_capture') and self.settings.enable_screenshots:
            await self.screen_capture.start_periodic_capture()
            
            # Schedule cleanup of old screenshots
            if self.settings.screenshot_cleanup_days > 0:
                asyncio.create_task(
                    self._schedule_screenshot_cleanup(
                        self.settings.screenshot_cleanup_days
                    )
                )
        
        while self.running:
            try:
                await self._check_active_window()
                await self._flush_buffer()
                await asyncio.sleep(self.settings.active_window_check_interval)
            except Exception as e:
                logger.error("Monitor error", error=str(e))
                if not self.settings.monitor_suppress_errors:
                    raise

    async def stop(self):
        """Stop monitoring gracefully"""
        logger.info("Stopping activity monitor...")
        self.running = False
        
        if self.input_tracker.running:
            self.input_tracker.stop()
        
        # Stop screen capture
        if hasattr(self, 'screen_capture'):
            await self.screen_capture.stop_periodic_capture()
            
        self.window_tracker.cleanup()
        await self._flush_buffer()
        await self.store.close()

    async def _check_active_window(self):
        """Check current active window"""
        try:
            window_info = await self.window_tracker.get_active_window()
            if window_info != self.current_window:
                self.current_window = window_info
                
                # Get window geometry if enabled
                geometry = None
                if self.settings.track_window_geometry:
                    geometry = self.window_tracker.get_window_geometry()
                
                # Update window info
                await self.store.update_window_info(
                    process_name=window_info['process'],
                    window_title=window_info['title'],
                    bundle=window_info['bundle'],
                    geometry=geometry
                )
                
                # Update screen capture if enabled
                if hasattr(self, 'screen_capture') and self.settings.enable_screenshots:
                    await self.screen_capture.update_window_info(window_info)
                
        except Exception as e:
            if not self.settings.monitor_suppress_errors:
                logger.error("Window check error", error=str(e))
    
    def _check_permissions(self) -> bool:
        """Check required macOS permissions"""
        if not self.settings.check_accessibility:
            return True
        
        try:
            from ApplicationServices import AXIsProcessTrusted
            
            # Direct check for accessibility permissions
            trusted = AXIsProcessTrusted()
            
            if not trusted:
                try:
                    # Try to open System Settings
                    import Foundation
                    url_str = Foundation.NSString.stringWithString_(
                        "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
                    )
                    url = Foundation.NSURL.URLWithString_(url_str)
                    Foundation.NSWorkspace.sharedWorkspace().openURL_(url)
                    
                    logger.info(
                        "Waiting for accessibility permissions...\n"
                        "Please enable access in System Settings when prompted"
                    )
                except Exception as e:
                    logger.error("Failed to open System Settings", error=str(e))
                    
            return trusted
                    
        except ImportError:
            logger.error("MacOS libraries not found. Please run: poetry install")
            raise ImportError("Required macOS libraries not found")
        except Exception as e:
            if not self.settings.monitor_suppress_errors:
                logger.error("Permission check error", error=str(e))
            return False

    def _on_key_press(self, key):
        """Handle key press events"""
        try:
            char = key.char if hasattr(key, 'char') else str(key)
            
            self.buffer.append({
                'type': 'key',
                'key': char,
                'time': datetime.now()
            })
            self.last_activity = datetime.now()
            
        except Exception as e:
            logger.error("Key press error", error=str(e))

    def _on_key_release(self, key):
        """Handle key release events"""
        pass

    def _on_mouse_move(self, x: int, y: int):
        """Handle mouse movement"""
        self.last_activity = datetime.now()

    def _on_mouse_click(self, x: int, y: int, button: mouse.Button, pressed: bool):
        """Handle mouse clicks"""
        if pressed:
            try:
                button_num = 1 if button == mouse.Button.left else 3
                asyncio.create_task(self.store.store_click(button_num, x, y))
                self.last_activity = datetime.now()
            except Exception as e:
                logger.error("Mouse click error", error=str(e))

    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        """Handle scroll events"""
        try:
            button_num = 4 if dy > 0 else 5
            asyncio.create_task(self.store.store_click(button_num, x, y))
            self.last_activity = datetime.now()
        except Exception as e:
            logger.error("Scroll error", error=str(e))

    async def _flush_buffer(self):
        """Flush keystroke buffer to storage"""
        if self.buffer and (datetime.now() - self.last_activity).seconds > self.settings.keystroke_buffer_timeout:
            text = ''.join(
                item['key'] for item in self.buffer 
                if isinstance(item.get('key'), str)
            )
            if text:
                await self.store.store_keys(text)
            self.buffer.clear()

    async def _schedule_screenshot_cleanup(self, days: int):
        """Schedule periodic cleanup of old screenshots"""
        while self.running:
            try:
                await self.screen_capture.cleanup_old_captures(days)
            except Exception as e:
                logger.error("Screenshot cleanup error", error=str(e))
            
            # Run cleanup once per day
            await asyncio.sleep(24 * 60 * 60)