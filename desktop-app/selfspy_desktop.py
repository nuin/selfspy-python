#!/usr/bin/env python3
"""
Selfspy Desktop Widget - macOS

A beautiful desktop widget that displays Selfspy activity statistics in real-time.
"""

import os
import sys
import time
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to import selfspy modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import objc
from Foundation import *
from AppKit import *
from Quartz import *

# Import selfspy modules
try:
    from config import Settings
    from activity_store import ActivityStore
    from enhanced_stats import get_enhanced_statistics
except ImportError as e:
    print(f"Error importing selfspy modules: {e}")
    print("Make sure you're running from the selfspy3 directory")
    sys.exit(1)


class SelfspyWidget(NSView):
    """Custom NSView for displaying Selfspy statistics"""
    
    def initWithFrame_(self, frame):
        self = super().initWithFrame_(frame)
        if self:
            self.stats_data = {}
            self.last_update = datetime.now()
            self.setup_appearance()
        return self
    
    def setup_appearance(self):
        """Set up the visual appearance of the widget"""
        # Enable layer backing for better performance
        self.setWantsLayer_(True)
        
        # Set background with transparency
        self.layer().setBackgroundColor_(
            NSColor.colorWithRed_green_blue_alpha_(0.0, 0.0, 0.0, 0.8).CGColor()
        )
        self.layer().setCornerRadius_(12.0)
        
        # Add subtle border
        self.layer().setBorderWidth_(1.0)
        self.layer().setBorderColor_(
            NSColor.colorWithRed_green_blue_alpha_(0.3, 0.3, 0.3, 0.8).CGColor()
        )
    
    def update_stats(self, stats_data):
        """Update the widget with new statistics data"""
        self.stats_data = stats_data
        self.last_update = datetime.now()
        self.setNeedsDisplay_(True)
    
    def drawRect_(self, rect):
        """Custom drawing method for the widget"""
        # Clear the background
        NSColor.clearColor().set()
        NSBezierPath.fillRect_(rect)
        
        if not self.stats_data:
            self.draw_loading_message(rect)
            return
        
        # Draw the statistics
        self.draw_statistics(rect)
    
    def draw_loading_message(self, rect):
        """Draw a loading message when no data is available"""
        message = "Loading Selfspy data..."
        attributes = {
            NSFontAttributeName: NSFont.systemFontOfSize_(14),
            NSForegroundColorAttributeName: NSColor.whiteColor()
        }
        
        string = NSAttributedString.alloc().initWithString_attributes_(message, attributes)
        text_size = string.size()
        
        # Center the text
        x = (rect.size.width - text_size.width) / 2
        y = (rect.size.height - text_size.height) / 2
        text_rect = NSMakeRect(x, y, text_size.width, text_size.height)
        
        string.drawInRect_(text_rect)
    
    def draw_statistics(self, rect):
        """Draw the main statistics display"""
        margin = 16
        y_offset = rect.size.height - margin - 20
        
        # Title
        title_attrs = {
            NSFontAttributeName: NSFont.boldSystemFontOfSize_(16),
            NSForegroundColorAttributeName: NSColor.whiteColor()
        }
        title = NSAttributedString.alloc().initWithString_attributes_(
            "📊 Selfspy Activity", title_attrs
        )
        title.drawAtPoint_(NSMakePoint(margin, y_offset))
        y_offset -= 35
        
        # Statistics content
        content_attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(12),
            NSForegroundColorAttributeName: NSColor.colorWithRed_green_blue_alpha_(0.9, 0.9, 0.9, 1.0)
        }
        
        # Sample statistics (this will be replaced with real data)
        stats_lines = [
            f"🔤 Keystrokes: {self.stats_data.get('keystrokes', 0):,}",
            f"🖱️ Clicks: {self.stats_data.get('clicks', 0):,}",
            f"⏱️ Active Time: {self.stats_data.get('active_time', '0h 0m')}",
            f"💻 Top App: {self.stats_data.get('top_app', 'Unknown')}",
            f"📈 Productivity: {self.stats_data.get('productivity_score', 0)}%",
        ]
        
        for line in stats_lines:
            stat = NSAttributedString.alloc().initWithString_attributes_(line, content_attrs)
            stat.drawAtPoint_(NSMakePoint(margin, y_offset))
            y_offset -= 22
        
        # Last update timestamp
        update_time = self.last_update.strftime("%H:%M:%S")
        timestamp_attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(10),
            NSForegroundColorAttributeName: NSColor.colorWithRed_green_blue_alpha_(0.6, 0.6, 0.6, 1.0)
        }
        timestamp = NSAttributedString.alloc().initWithString_attributes_(
            f"Updated: {update_time}", timestamp_attrs
        )
        timestamp.drawAtPoint_(NSMakePoint(margin, 8))


class SelfspyDesktopApp(NSObject):
    """Main application class for the Selfspy Desktop Widget"""
    
    def init(self):
        self = super().init()
        if self:
            self.window = None
            self.widget_view = None
            self.stats_thread = None
            self.should_update = True
            self.settings = None
            self.store = None
            self.setup_selfspy_connection()
        return self
    
    def setup_selfspy_connection(self):
        """Set up connection to Selfspy data"""
        try:
            self.settings = Settings()
            self.store = ActivityStore(self.settings)
            print("✅ Connected to Selfspy database")
        except Exception as e:
            print(f"❌ Error connecting to Selfspy: {e}")
            print("Make sure Selfspy is installed and has been run at least once")
    
    def create_window(self):
        """Create the main widget window"""
        # Window size and position
        window_width = 280
        window_height = 200
        
        # Position on right side of screen
        screen_frame = NSScreen.mainScreen().frame()
        x = screen_frame.size.width - window_width - 20
        y = screen_frame.size.height - window_height - 100
        
        window_rect = NSMakeRect(x, y, window_width, window_height)
        
        # Create window with special properties
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            window_rect,
            NSWindowStyleMaskBorderless,  # No title bar
            NSBackingStoreBuffered,
            False
        )
        
        # Window properties for desktop widget
        self.window.setLevel_(NSFloatingWindowLevel)  # Always on top
        self.window.setOpaque_(False)  # Allow transparency
        self.window.setBackgroundColor_(NSColor.clearColor())
        self.window.setHasShadow_(True)
        self.window.setMovableByWindowBackground_(True)  # Allow dragging
        self.window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces |
            NSWindowCollectionBehaviorStationary
        )
        
        # Create and set up the widget view
        content_rect = NSMakeRect(0, 0, window_width, window_height)
        self.widget_view = SelfspyWidget.alloc().initWithFrame_(content_rect)
        self.window.setContentView_(self.widget_view)
        
        # Show the window
        self.window.makeKeyAndOrderFront_(None)
        
        print("🖥️ Desktop widget created")
    
    def start_stats_updates(self):
        """Start the background thread for updating statistics"""
        self.stats_thread = threading.Thread(target=self.stats_update_loop, daemon=True)
        self.stats_thread.start()
        print("🔄 Started statistics update thread")
    
    def stats_update_loop(self):
        """Background loop to update statistics"""
        while self.should_update:
            try:
                # Get fresh statistics data
                stats_data = self.get_current_stats()
                
                # Update the widget on the main thread
                def update_widget():
                    if self.widget_view:
                        self.widget_view.update_stats(stats_data)
                
                NSOperationQueue.mainQueue().addOperationWithBlock_(update_widget)
                
            except Exception as e:
                print(f"Error updating stats: {e}")
            
            # Wait before next update
            time.sleep(5)  # Update every 5 seconds
    
    def get_current_stats(self):
        """Get current statistics from Selfspy"""
        if not self.store:
            return {}
        
        try:
            # Get today's statistics
            end_date = datetime.now()
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # This is a simplified version - in a real implementation,
            # you would call the actual selfspy statistics functions
            stats_data = {
                'keystrokes': 1234,  # Placeholder
                'clicks': 567,       # Placeholder
                'active_time': '3h 45m',  # Placeholder
                'top_app': 'Code',   # Placeholder
                'productivity_score': 78,  # Placeholder
            }
            
            return stats_data
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
    
    def run(self):
        """Run the desktop application"""
        print("🚀 Starting Selfspy Desktop Widget...")
        
        # Create the widget window
        self.create_window()
        
        # Start updating statistics
        self.start_stats_updates()
        
        # Run the application
        NSApp.run()
    
    def applicationWillTerminate_(self, notification):
        """Clean up when the application terminates"""
        self.should_update = False
        print("👋 Selfspy Desktop Widget closing...")


def main():
    """Main entry point"""
    print("🎯 Selfspy Desktop Widget for macOS")
    print("=====================================")
    
    # Create the application
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)  # Don't show in dock
    
    # Create and run the desktop app
    desktop_app = SelfspyDesktopApp.alloc().init()
    app.setDelegate_(desktop_app)
    
    desktop_app.run()


if __name__ == "__main__":
    main()