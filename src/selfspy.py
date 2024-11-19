"""
Selfspy - Activity Monitor using pynput instead of PyObjC
"""

import os
import sys
import time
import hashlib
import argparse
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

from pynput import mouse, keyboard
from Crypto.Cipher import Blowfish
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Binary, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Constants
DATA_DIR = os.path.expanduser('~/.selfspy')
DBNAME = 'selfspy.sqlite'
MAGIC_STRING = b'\xc5\x7fdh\x05\xf6\xc5=\xcfh\xafv\xc0\xf4\x13i*.O'

Base = declarative_base()

class Process(Base):
    __tablename__ = 'process'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True, unique=True)
    created_at = Column(DateTime, default=datetime.now, index=True)

class Window(Base):
    __tablename__ = 'window'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, index=True)
    process_id = Column(Integer, ForeignKey('process.id'), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now, index=True)
    
    process = relationship("Process", backref='windows')

class Keys(Base):
    __tablename__ = 'keys'
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now, index=True)
    text = Column(Binary, nullable=False)
    process_id = Column(Integer, ForeignKey('process.id'), nullable=False)
    window_id = Column(Integer, ForeignKey('window.id'), nullable=False)
    
    process = relationship("Process", backref='keys')
    window = relationship("Window", backref='keys')

class Click(Base):
    __tablename__ = 'click'
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now, index=True)
    button = Column(Integer, nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    process_id = Column(Integer, ForeignKey('process.id'), nullable=False)
    window_id = Column(Integer, ForeignKey('window.id'), nullable=False)
    
    process = relationship("Process", backref='clicks')
    window = relationship("Window", backref='clicks')

class ActivityMonitor:
    def __init__(self, store: 'ActivityStore'):
        self.store = store
        self.current_window = None
        self.current_process = None
        self.buffer = []
        self.last_activity = time.time()
        
        # Initialize listeners
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        self.mouse_listener = mouse.Listener(
            on_move=self.on_mouse_move,
            on_click=self.on_mouse_click,
            on_scroll=self.on_scroll
        )

    def start(self):
        """Start monitoring"""
        self.keyboard_listener.start()
        self.mouse_listener.start()
        
        try:
            while True:
                self.check_active_window()
                self.flush_buffer()
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop monitoring"""
        self.keyboard_listener.stop()
        self.mouse_listener.stop()
        self.flush_buffer()

    def check_active_window(self):
        """Check current active window using AppKit"""
        try:
            import AppKit
            workspace = AppKit.NSWorkspace.sharedWorkspace()
            active_app = workspace.activeApplication()
            
            if active_app:
                process_name = active_app['NSApplicationName']
                window_title = self._get_active_window_title()
                
                if (process_name != self.current_process or 
                    window_title != self.current_window):
                    self.current_process = process_name
                    self.current_window = window_title
                    self.store.update_window_info(process_name, window_title)
                    
        except Exception as e:
            print(f"Error checking active window: {e}", file=sys.stderr)

    def _get_active_window_title(self) -> str:
        """Get the title of the active window"""
        try:
            import AppKit
            windows = AppKit.NSApplication.sharedApplication().windows()
            for window in windows:
                if window.isKeyWindow():
                    return window.title() or ''
        except:
            pass
        return ''

    def on_key_press(self, key):
        """Handle key press events"""
        try:
            if hasattr(key, 'char'):
                char = key.char
            else:
                char = str(key)
            
            self.buffer.append({
                'type': 'key',
                'key': char,
                'time': time.time()
            })
            self.last_activity = time.time()
            
        except Exception as e:
            print(f"Error handling key press: {e}", file=sys.stderr)

    def on_key_release(self, key):
        """Handle key release events"""
        pass

    def on_mouse_move(self, x, y):
        """Handle mouse movement"""
        self.last_activity = time.time()

    def on_mouse_click(self, x, y, button, pressed):
        """Handle mouse clicks"""
        if pressed:
            try:
                button_num = 1 if button == mouse.Button.left else 3
                self.store.store_click(button_num, x, y)
                self.last_activity = time.time()
            except Exception as e:
                print(f"Error handling mouse click: {e}", file=sys.stderr)

    def on_scroll(self, x, y, dx, dy):
        """Handle scroll events"""
        try:
            button_num = 4 if dy > 0 else 5
            self.store.store_click(button_num, x, y)
            self.last_activity = time.time()
        except Exception as e:
            print(f"Error handling scroll: {e}", file=sys.stderr)

    def flush_buffer(self):
        """Flush keystroke buffer to storage"""
        if self.buffer and time.time() - self.last_activity > 1.0:
            text = ''.join(item['key'] for item in self.buffer 
                          if isinstance(item.get('key'), str))
            if text:
                self.store.store_keys(text)
            self.buffer.clear()

class ActivityStore:
    def __init__(self, db_path: str, password: Optional[str] = None):
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        
        if password:
            self.cipher = Blowfish.new(
                hashlib.md5(password.encode()).digest(),
                Blowfish.MODE_ECB
            )
        else:
            self.cipher = None
            
        self.current_process_id = None
        self.current_window_id = None

    def encrypt_text(self, text: str) -> bytes:
        """Encrypt text data"""
        if not self.cipher:
            return text.encode()
            
        padding = 8 - (len(text) % 8)
        padded_text = text + '\0' * padding
        return self.cipher.encrypt(padded_text.encode())

    def update_window_info(self, process_name: str, window_title: str):
        """Update current process and window information"""
        # Get or create process
        process = self.session.query(Process).filter_by(name=process_name).first()
        if not process:
            process = Process(name=process_name)
            self.session.add(process)
            self.session.commit()
            
        # Create new window
        window = Window(title=window_title, process_id=process.id)
        self.session.add(window)
        self.session.commit()
        
        self.current_process_id = process.id
        self.current_window_id = window.id

    def store_keys(self, text: str):
        """Store keystroke data"""
        if self.current_process_id and self.current_window_id:
            encrypted_text = self.encrypt_text(text)
            keys = Keys(
                text=encrypted_text,
                process_id=self.current_process_id,
                window_id=self.current_window_id
            )
            self.session.add(keys)
            self.session.commit()

    def store_click(self, button: int, x: int, y: int):
        """Store mouse click data"""
        if self.current_process_id and self.current_window_id:
            click = Click(
                button=button,
                x=x,
                y=y,
                process_id=self.current_process_id,
                window_id=self.current_window_id
            )
            self.session.add(click)
            self.session.commit()

    def close(self):
        """Clean up database connection"""
        self.session.close()

def main():
    parser = argparse.ArgumentParser(
        description='Monitor and store computer activity using pynput'
    )
    parser.add_argument(
        '-p', '--password',
        help='Encryption password for sensitive data'
    )
    parser.add_argument(
        '-d', '--data-dir',
        default=DATA_DIR,
        help='Data directory for storing the database'
    )
    parser.add_argument(
        '--no-text',
        action='store_true',
        help='Do not store text data (keystrokes)'
    )
    
    args = parser.parse_args()

    # Ensure data directory exists
    os.makedirs(args.data_dir, exist_ok=True)
    
    db_path = os.path.join(args.data_dir, DBNAME)
    store = ActivityStore(db_path, None if args.no_text else args.password)
    
    try:
        monitor = ActivityMonitor(store)
        monitor.start()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    finally:
        store.close()

if __name__ == '__main__':
    main()