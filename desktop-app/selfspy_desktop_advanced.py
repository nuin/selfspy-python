#!/usr/bin/env python3
"""
Selfspy Desktop Widget Manager - Advanced Version

A sophisticated desktop widget system with multiple widget types,
customization options, and advanced macOS integration.
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

# Import widget types
from widget_types import WIDGET_TYPES, BaseWidget

# Import selfspy modules
try:
    from config import Settings
    from activity_store import ActivityStore
except ImportError as e:
    print(f"⚠️  Warning: Could not import selfspy modules: {e}")
    print("Some features may not work correctly")


class SelfspyWidgetView(NSView):
    """Enhanced NSView for displaying different widget types"""
    
    def initWithFrame_widgetType_(self, frame, widget_type):
        self = super().initWithFrame_(frame)
        if self:
            self.widget_type = widget_type
            self.widget = WIDGET_TYPES.get(widget_type, BaseWidget)()
            self.last_update = datetime.now()
            self.is_dragging = False
            self.setup_appearance()
            self.setup_menu()
        return self
    
    def setup_appearance(self):
        """Set up the visual appearance"""
        self.setWantsLayer_(True)
        
        # Modern rounded rectangle with subtle gradient
        self.layer().setBackgroundColor_(
            NSColor.colorWithRed_green_blue_alpha_(0.05, 0.05, 0.05, 0.9).CGColor()
        )
        self.layer().setCornerRadius_(16.0)
        
        # Subtle border and shadow
        self.layer().setBorderWidth_(0.5)
        self.layer().setBorderColor_(
            NSColor.colorWithRed_green_blue_alpha_(0.3, 0.3, 0.3, 0.6).CGColor()
        )
        
        # Add shadow for depth
        self.layer().setShadowOpacity_(0.3)
        self.layer().setShadowRadius_(8.0)
        self.layer().setShadowOffset_(NSMakeSize(0, -2))
    
    def setup_menu(self):
        """Set up the right-click context menu"""
        menu = NSMenu.alloc().init()
        
        # Widget type submenu
        widget_menu = NSMenu.alloc().init()
        for widget_key, widget_class in WIDGET_TYPES.items():
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                widget_class().title, 
                "changeWidgetType:",
                ""
            )
            item.setTag_(hash(widget_key))
            item.setRepresentedObject_(widget_key)
            widget_menu.addItem_(item)
        
        widget_type_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Widget Type", None, ""
        )
        widget_type_item.setSubmenu_(widget_menu)
        menu.addItem_(widget_type_item)
        
        menu.addItem_(NSMenuItem.separatorItem())
        
        # Other options
        menu.addItem_(NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Always on Top", "toggleAlwaysOnTop:", ""
        ))
        menu.addItem_(NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Click Through", "toggleClickThrough:", ""
        ))
        
        menu.addItem_(NSMenuItem.separatorItem())
        
        menu.addItem_(NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Close Widget", "closeWidget:", ""
        ))
        
        self.setMenu_(menu)
    
    def changeWidgetType_(self, sender):
        """Change the widget type"""
        widget_key = sender.representedObject()
        if widget_key in WIDGET_TYPES:
            self.widget_type = widget_key
            self.widget = WIDGET_TYPES[widget_key]()
            self.setNeedsDisplay_(True)
            print(f"🔄 Changed widget to: {self.widget.title}")
    
    def toggleAlwaysOnTop_(self, sender):
        """Toggle always on top"""
        window = self.window()
        if window:
            current_level = window.level()
            if current_level == NSFloatingWindowLevel:
                window.setLevel_(NSNormalWindowLevel)
                print("📌 Always on top: OFF")
            else:
                window.setLevel_(NSFloatingWindowLevel)
                print("📌 Always on top: ON")
    
    def toggleClickThrough_(self, sender):
        """Toggle click-through mode"""
        window = self.window()
        if window:
            current_policy = window.collectionBehavior()
            if current_policy & NSWindowCollectionBehaviorIgnoresCycle:
                # Disable click-through
                window.setCollectionBehavior_(
                    NSWindowCollectionBehaviorCanJoinAllSpaces |
                    NSWindowCollectionBehaviorStationary
                )
                print("👆 Click through: OFF")
            else:
                # Enable click-through
                window.setCollectionBehavior_(
                    NSWindowCollectionBehaviorCanJoinAllSpaces |
                    NSWindowCollectionBehaviorStationary |
                    NSWindowCollectionBehaviorIgnoresCycle
                )
                print("👆 Click through: ON")
    
    def closeWidget_(self, sender):
        """Close this widget"""
        window = self.window()
        if window:
            window.close()
    
    def update_widget_data(self, store):
        """Update the widget with fresh data"""
        if self.widget:
            self.widget.update_data(store)
            self.last_update = datetime.now()
            self.setNeedsDisplay_(True)
    
    def drawRect_(self, rect):
        """Custom drawing"""
        # Clear background
        NSColor.clearColor().set()
        NSBezierPath.fillRect_(rect)
        
        # Draw the widget
        if self.widget:
            self.widget.draw(self, rect)
        
        # Draw update indicator in corner
        self.draw_update_indicator(rect)
    
    def draw_update_indicator(self, rect):
        """Draw a small indicator showing last update time"""
        time_since_update = (datetime.now() - self.last_update).total_seconds()
        
        # Color based on freshness
        if time_since_update < 10:
            color = NSColor.colorWithRed_green_blue_alpha_(0.0, 0.8, 0.0, 0.6)  # Green
        elif time_since_update < 30:
            color = NSColor.colorWithRed_green_blue_alpha_(1.0, 0.8, 0.0, 0.6)  # Yellow
        else:
            color = NSColor.colorWithRed_green_blue_alpha_(0.8, 0.0, 0.0, 0.6)  # Red
        
        # Draw small circle in top-right corner
        indicator_size = 8
        indicator_rect = NSMakeRect(
            rect.size.width - indicator_size - 8,
            rect.size.height - indicator_size - 8,
            indicator_size,
            indicator_size
        )
        
        color.set()
        NSBezierPath.bezierPathWithOvalInRect_(indicator_rect).fill()
    
    # Mouse event handling for dragging
    def mouseDown_(self, event):
        """Handle mouse down for dragging"""
        self.is_dragging = True
        self.drag_start_point = event.locationInWindow()
        window = self.window()
        if window:
            self.window_start_point = window.frame().origin
    
    def mouseDragged_(self, event):
        """Handle mouse dragging"""
        if self.is_dragging:
            current_point = event.locationInWindow()
            window = self.window()
            if window:
                delta_x = current_point.x - self.drag_start_point.x
                delta_y = current_point.y - self.drag_start_point.y
                
                new_origin = NSMakePoint(
                    self.window_start_point.x + delta_x,
                    self.window_start_point.y + delta_y
                )
                
                frame = window.frame()
                frame.origin = new_origin
                window.setFrame_display_(frame, True)
    
    def mouseUp_(self, event):
        """Handle mouse up"""
        self.is_dragging = False


class SelfspyWidgetManager(NSObject):
    """Manager for multiple desktop widgets"""
    
    def init(self):
        self = super().init()
        if self:
            self.widgets = []
            self.settings = None
            self.store = None
            self.update_thread = None
            self.should_update = True
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
            print("   Make sure Selfspy is installed and configured")
    
    def create_widget(self, widget_type, x=None, y=None):
        """Create a new widget of the specified type"""
        if widget_type not in WIDGET_TYPES:
            print(f"❌ Unknown widget type: {widget_type}")
            return None
        
        widget_class = WIDGET_TYPES[widget_type]
        widget_instance = widget_class()
        
        # Determine position
        if x is None or y is None:
            screen_frame = NSScreen.mainScreen().frame()
            x = x or screen_frame.size.width - widget_instance.width - 20
            y = y or screen_frame.size.height - widget_instance.height - (100 + len(self.widgets) * 50)
        
        # Create window
        window_rect = NSMakeRect(x, y, widget_instance.width, widget_instance.height)
        window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            window_rect,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False
        )
        
        # Window properties
        window.setLevel_(NSFloatingWindowLevel)
        window.setOpaque_(False)
        window.setBackgroundColor_(NSColor.clearColor())
        window.setHasShadow_(True)
        window.setMovableByWindowBackground_(False)  # We handle dragging manually
        window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces |
            NSWindowCollectionBehaviorStationary
        )
        
        # Create widget view
        content_rect = NSMakeRect(0, 0, widget_instance.width, widget_instance.height)
        widget_view = SelfspyWidgetView.alloc().initWithFrame_widgetType_(
            content_rect, widget_type
        )
        
        window.setContentView_(widget_view)
        window.makeKeyAndOrderFront_(None)
        
        # Store widget info
        widget_info = {
            'window': window,
            'view': widget_view,
            'type': widget_type,
            'instance': widget_instance
        }
        self.widgets.append(widget_info)
        
        print(f"🎯 Created {widget_instance.title} widget")
        return widget_info
    
    def start_update_loop(self):
        """Start the background update loop"""
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
        print("🔄 Started widget update loop")
    
    def update_loop(self):
        """Background loop to update all widgets"""
        while self.should_update:
            try:
                # Update all widgets
                for widget_info in self.widgets[:]:  # Copy list to avoid modification during iteration
                    try:
                        widget_view = widget_info['view']
                        if widget_view and widget_view.window():
                            # Update on main thread
                            def update_widget():
                                widget_view.update_widget_data(self.store)
                            
                            NSOperationQueue.mainQueue().addOperationWithBlock_(update_widget)
                        else:
                            # Widget was closed, remove from list
                            self.widgets.remove(widget_info)
                    
                    except Exception as e:
                        print(f"Error updating widget: {e}")
                
                # Wait before next update
                time.sleep(10)  # Update every 10 seconds
                
            except Exception as e:
                print(f"Error in update loop: {e}")
                time.sleep(5)
    
    def load_default_widgets(self):
        """Load the default set of widgets"""
        # Create default widgets
        self.create_widget('activity')
        self.create_widget('apps', y=400)
        self.create_widget('terminal', y=600)
    
    def applicationWillTerminate_(self, notification):
        """Clean up when terminating"""
        self.should_update = False
        print("👋 Selfspy Widget Manager shutting down...")


def main():
    """Main entry point for the advanced desktop app"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Selfspy Desktop Widgets")
    parser.add_argument('--widget', '-w', 
                       choices=list(WIDGET_TYPES.keys()), 
                       help='Create a specific widget type')
    parser.add_argument('--list-widgets', '-l', 
                       action='store_true',
                       help='List available widget types')
    
    args = parser.parse_args()
    
    if args.list_widgets:
        print("📋 Available widget types:")
        for key, widget_class in WIDGET_TYPES.items():
            widget = widget_class()
            print(f"  {key:12} - {widget.title}")
        return
    
    print("🚀 Selfspy Desktop Widget Manager")
    print("==================================")
    
    # Create the application
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    
    # Create widget manager
    manager = SelfspyWidgetManager.alloc().init()
    app.setDelegate_(manager)
    
    # Create specified widget or defaults
    if args.widget:
        manager.create_widget(args.widget)
    else:
        manager.load_default_widgets()
    
    # Start the update loop
    manager.start_update_loop()
    
    print("🎯 Widgets created! Right-click on any widget for options.")
    print("💡 Press Ctrl+C to exit")
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Exiting...")


if __name__ == "__main__":
    main()