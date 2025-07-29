#!/usr/bin/env python3
"""
Simple Selfspy Desktop Widget - Standalone Version

A simplified desktop widget that works without complex dependencies.
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

import objc
from Foundation import *
from AppKit import *
from Quartz import *


class SimpleActivityWidget(NSView):
    """Simple activity widget with mock data"""
    
    def initWithFrame_(self, frame):
        self = objc.super(SimpleActivityWidget, self).initWithFrame_(frame)
        if self:
            self.stats_data = {
                'keystrokes': 2847,
                'clicks': 892,
                'active_time': '4h 23m',
                'windows_visited': 47,
                'productivity_score': 82,
                'top_app': 'Visual Studio Code',
                'commands_today': 142,
                'last_command': 'git status'
            }
            self.last_update = datetime.now()
            self.setup_appearance()
        return self
    
    def setup_appearance(self):
        """Set up the visual appearance"""
        self.setWantsLayer_(True)
        
        # Modern dark background with transparency
        self.layer().setBackgroundColor_(
            NSColor.colorWithRed_green_blue_alpha_(0.05, 0.05, 0.05, 0.92).CGColor()
        )
        self.layer().setCornerRadius_(16.0)
        
        # Subtle border
        self.layer().setBorderWidth_(0.5)
        self.layer().setBorderColor_(
            NSColor.colorWithRed_green_blue_alpha_(0.3, 0.3, 0.3, 0.6).CGColor()
        )
        
        # Drop shadow
        self.layer().setShadowOpacity_(0.3)
        self.layer().setShadowRadius_(8.0)
        self.layer().setShadowOffset_(NSMakeSize(0, -2))
    
    def update_stats(self):
        """Update stats with simulated live data"""
        import random
        
        # Simulate changing data
        self.stats_data['keystrokes'] += random.randint(0, 10)
        self.stats_data['clicks'] += random.randint(0, 3)
        self.stats_data['productivity_score'] = min(100, max(0, 
            self.stats_data['productivity_score'] + random.randint(-2, 3)))
        
        self.last_update = datetime.now()
        self.setNeedsDisplay_(True)
    
    def drawRect_(self, rect):
        """Custom drawing"""
        # Clear background
        NSColor.clearColor().set()
        NSBezierPath.fillRect_(rect)
        
        margin = 16
        y = rect.size.height - margin - 20
        
        # Title
        title_attrs = {
            NSFontAttributeName: NSFont.boldSystemFontOfSize_(16),
            NSForegroundColorAttributeName: NSColor.whiteColor()
        }
        title = NSAttributedString.alloc().initWithString_attributes_(
            "📊 Selfspy Activity", title_attrs
        )
        title.drawAtPoint_(NSMakePoint(margin, y))
        y -= 35
        
        # Statistics
        content_attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(12),
            NSForegroundColorAttributeName: NSColor.colorWithRed_green_blue_alpha_(0.9, 0.9, 0.9, 1.0)
        }
        
        stats_lines = [
            f"⌨️  {self.stats_data['keystrokes']:,} keystrokes",
            f"🖱️  {self.stats_data['clicks']:,} clicks", 
            f"⏰ {self.stats_data['active_time']} active",
            f"🪟 {self.stats_data['windows_visited']} windows",
            f"💻 {self.stats_data['top_app']}",
            f"📈 {self.stats_data['productivity_score']}% productive",
            f"🔧 {self.stats_data['commands_today']} terminal commands",
            f"💾 Last: {self.stats_data['last_command']}"
        ]
        
        for line in stats_lines:
            stat = NSAttributedString.alloc().initWithString_attributes_(line, content_attrs)
            stat.drawAtPoint_(NSMakePoint(margin, y))
            y -= 18
        
        # Update indicator
        self.draw_update_indicator(rect)
    
    def draw_update_indicator(self, rect):
        """Draw update status indicator"""
        time_since_update = (datetime.now() - self.last_update).total_seconds()
        
        # Green if recent, yellow if older, red if very old
        if time_since_update < 10:
            color = NSColor.colorWithRed_green_blue_alpha_(0.0, 0.8, 0.0, 0.8)
        elif time_since_update < 30:
            color = NSColor.colorWithRed_green_blue_alpha_(1.0, 0.8, 0.0, 0.8)
        else:
            color = NSColor.colorWithRed_green_blue_alpha_(0.8, 0.0, 0.0, 0.8)
        
        # Small circle in top-right
        indicator_size = 8
        indicator_rect = NSMakeRect(
            rect.size.width - indicator_size - 8,
            rect.size.height - indicator_size - 8,
            indicator_size,
            indicator_size
        )
        
        color.set()
        NSBezierPath.bezierPathWithOvalInRect_(indicator_rect).fill()
        
        # Timestamp
        timestamp_attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(9),
            NSForegroundColorAttributeName: NSColor.colorWithRed_green_blue_alpha_(0.6, 0.6, 0.6, 1.0)
        }
        timestamp = NSAttributedString.alloc().initWithString_attributes_(
            f"Updated: {self.last_update.strftime('%H:%M:%S')}", timestamp_attrs
        )
        timestamp.drawAtPoint_(NSMakePoint(8, 8))


class SimpleWidgetApp(NSObject):
    """Simple widget application"""
    
    def init(self):
        self = objc.super(SimpleWidgetApp, self).init()
        if self:
            self.window = None
            self.widget_view = None
            self.update_thread = None
            self.should_update = True
        return self
    
    def create_window(self):
        """Create the widget window"""
        # Window size and position
        window_width = 320
        window_height = 240
        
        # Position on right side of screen
        screen_frame = NSScreen.mainScreen().frame()
        x = screen_frame.size.width - window_width - 20
        y = screen_frame.size.height - window_height - 100
        
        window_rect = NSMakeRect(x, y, window_width, window_height)
        
        # Create window
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            window_rect,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False
        )
        
        # Window properties for desktop widget
        self.window.setLevel_(NSFloatingWindowLevel)  # Always on top
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(NSColor.clearColor())
        self.window.setHasShadow_(True)
        self.window.setMovableByWindowBackground_(True)
        self.window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces |
            NSWindowCollectionBehaviorStationary
        )
        
        # Create widget view
        content_rect = NSMakeRect(0, 0, window_width, window_height)
        self.widget_view = SimpleActivityWidget.alloc().initWithFrame_(content_rect)
        self.window.setContentView_(self.widget_view)
        
        # Show window
        self.window.makeKeyAndOrderFront_(None)
        
        print("🎯 Simple desktop widget created!")
        print("💡 Drag to move, Cmd+Q to quit")
    
    def start_updates(self):
        """Start the update thread"""
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
        print("🔄 Started update loop")
    
    def update_loop(self):
        """Background update loop"""
        while self.should_update:
            try:
                # Update widget on main thread
                def update_widget():
                    if self.widget_view:
                        self.widget_view.update_stats()
                
                NSOperationQueue.mainQueue().addOperationWithBlock_(update_widget)
                
                # Wait before next update
                time.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                print(f"Update error: {e}")
                time.sleep(5)
    
    def run(self):
        """Run the application"""
        print("🚀 Starting Simple Selfspy Widget...")
        
        # Create window and start updates
        self.create_window()
        self.start_updates()
        
        # Run the app
        NSApp.run()
    
    def applicationWillTerminate_(self, notification):
        """Clean up on exit"""
        self.should_update = False
        print("👋 Simple widget closing...")


def main():
    """Main entry point"""
    print("🎯 Simple Selfspy Desktop Widget")
    print("=================================")
    print("💡 This is a demo widget with simulated data")
    print("📊 Shows what the full widget system will look like")
    print()
    
    # Create application
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)  # Hide from dock
    
    # Create and run widget
    widget_app = SimpleWidgetApp.alloc().init()
    app.setDelegate_(widget_app)
    
    try:
        widget_app.run()
    except KeyboardInterrupt:
        print("\n👋 Exiting...")


if __name__ == "__main__":
    main()