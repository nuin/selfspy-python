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
from .platform.darwin import MacOSWindowTracker

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
        
        # Configure logging
        log_level = logging.DEBUG if debug else logging.INFO
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(log_level)
        )
        
        # Initialize platform-specific window tracker
        if platform.system() == 'Darwin':
            self.window_tracker = MacOSWindowTracker()
        else:
            raise NotImplementedError(
                f"Platform {platform.system()} not supported"
            )
        
        # Initialize input listeners
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_scroll
        )

    async def start(self):
        """Start monitoring asynchronously"""
        logger.info("Starting activity monitor...")
        
        if not self._check_permissions():
            raise PermissionError(
                "Accessibility permissions required. Please enable in System Preferences."
            )
        
        self.keyboard_listener.start()
        self.mouse_listener.start()
        
        try:
            while True:
                await self._check_active_window()
                await self._flush_buffer()
                await asyncio.sleep(self.settings.active_window_check_interval)
        except asyncio.CancelledError:
            logger.info("Shutting down monitor...")
            await self.stop()
        except Exception as e:
            logger.error("Monitor error", error=str(e))
            await self.stop()
            raise

    async def stop(self):
        """Stop monitoring gracefully"""
        logger.info("Stopping activity monitor...")
        
        self.keyboard_listener.stop()
        self.mouse_listener.stop()
        self.window_tracker.cleanup()
        
        await self._flush_buffer()
        await self.store.close()

    async def _check_active_window(self):
        """Check current active window"""
        try:
            window_info = await self.window_tracker.get_active_window()
            
            if window_info != self.current_window:
                self.current_window = window_info
                
                # Get window geometry
                if self.settings.track_window_geometry:
                    x, y, width, height = self.window_tracker.get_window_geometry()
                else:
                    x = y = width = height = 0
                
                # Skip excluded bundles
                if window_info['bundle'] in self.settings.excluded_bundles:
                    return
                
                await self.store.update_window_info(
                    process_name=window_info['process'],
                    window_title=window_info['title'],
                    bundle_id=window_info['bundle'],
                    geometry=(x, y, width, height)
                )
                
        except Exception as e:
            if not self.settings.monitor_suppress_errors:
                logger.error("Window check error", error=str(e))
    
    def _check_permissions(self) -> bool:
        """Check required macOS permissions"""
        if not self.settings.check_accessibility:
            return True
            
        try:
            import Quartz
            trusted = Quartz.AXIsProcessTrusted()
            if not trusted:
                logger.error(
                    "Accessibility permissions required. "
                    "Please enable in System Preferences > Security & Privacy > Privacy > Accessibility"
                )
            return trusted
        except Exception as e:
            logger.error("Permission check failed", error=str(e))
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