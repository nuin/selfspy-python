"""
Selfspy - Modern Python Activity Monitor
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import structlog
from pynput import mouse, keyboard
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from .models import Base, Process, Window, Keys, Click
from .config import Settings
from .encryption import create_cipher, check_password

logger = structlog.get_logger()

class ActivityMonitor:
    """Modern asynchronous activity monitor"""
    
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
        
        # Initialize listeners
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
        
        self.keyboard_listener.start()
        self.mouse_listener.start()
        
        try:
            while True:
                await self._check_active_window()
                await self._flush_buffer()
                await asyncio.sleep(0.1)
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
        await self._flush_buffer()
        await self.store.close()

    async def _check_active_window(self):
        """Check current active window"""
        try:
            window_info = await self._get_window_info()
            
            if window_info != self.current_window:
                self.current_window = window_info
                await self.store.update_window_info(
                    window_info['process'],
                    window_info['title']
                )
                
        except Exception as e:
            logger.error("Window check error", error=str(e))

    async def _get_window_info(self) -> Dict[str, str]:
        """Get active window information"""
        # Platform-specific window detection
        # This is a placeholder - actual implementation would use 
        # platform-specific APIs (AppKit, Win32, Xlib etc.)
        return {
            'process': 'unknown',
            'title': 'unknown'
        }

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
        if self.buffer and (datetime.now() - self.last_activity).seconds > 1:
            text = ''.join(
                item['key'] for item in self.buffer 
                if isinstance(item.get('key'), str)
            )
            if text:
                await self.store.store_keys(text)
            self.buffer.clear()

class ActivityStore:
    """Asynchronous activity data store"""
    
    def __init__(
        self,
        settings: Settings,
        password: Optional[str] = None
    ):
        self.settings = settings
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{settings.database_path}",
            echo=settings.debug
        )
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        
        self.cipher = create_cipher(password) if password else None
        self.current_window_id: Optional[int] = None
        self.current_process_id: Optional[int] = None

    async def initialize(self):
        """Initialize database"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        if self.settings.encryption_enabled:
            await check_password(
                self.settings.data_dir,
                self.cipher,
                self.settings.read_only
            )

    async def update_window_info(self, process_name: str, window_title: str):
        """Update current process and window information"""
        async with self.async_session() as session:
            async with session.begin():
                # Get or create process
                stmt = select(Process).filter_by(name=process_name)
                result = await session.execute(stmt)
                process = result.scalar_one_or_none()
                
                if not process:
                    process = Process(name=process_name)
                    session.add(process)
                    await session.flush()
                
                # Create new window
                window = Window(title=window_title, process_id=process.id)
                session.add(window)
                await session.flush()
                
                self.current_process_id = process.id
                self.current_window_id = window.id

    async def store_keys(self, text: str):
        """Store keystroke data"""
        if not self.current_process_id or not self.current_window_id:
            return
            
        encrypted_text = self._encrypt_text(text)
        
        async with self.async_session() as session:
            async with session.begin():
                keys = Keys(
                    text=encrypted_text,
                    process_id=self.current_process_id,
                    window_id=self.current_window_id
                )
                session.add(keys)

    async def store_click(self, button: int, x: int, y: int):
        """Store mouse click data"""
        if not self.current_process_id or not self.current_window_id:
            return
            
        async with self.async_session() as session:
            async with session.begin():
                click = Click(
                    button=button,
                    x=x,
                    y=y,
                    process_id=self.current_process_id,
                    window_id=self.current_window_id
                )
                session.add(click)

    def _encrypt_text(self, text: str) -> bytes:
        """Encrypt text data"""
        if not self.cipher:
            return text.encode()
            
        padding = 8 - (len(text) % 8)
        padded_text = text + '\0' * padding
        return self.cipher.encrypt(padded_text.encode())

    async def close(self):
        """Clean up database connection"""
        await self.engine.dispose()