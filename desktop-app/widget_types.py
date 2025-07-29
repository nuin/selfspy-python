"""
Different widget types for the Selfspy Desktop App
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path to import selfspy modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from Foundation import *
from AppKit import *
import asyncio
import threading

# Import our data integration module
from data_integration import (
    sync_get_activity_summary,
    sync_get_top_applications, 
    sync_get_terminal_activity,
    sync_get_hourly_activity_chart
)


class BaseWidget:
    """Base class for all widget types"""
    
    def __init__(self, width=280, height=200):
        self.width = width
        self.height = height
        self.title = "Base Widget"
        self.data = {}
    
    def draw(self, view, rect):
        """Override this method to draw the widget"""
        pass
    
    def update_data(self, store):
        """Override this method to fetch fresh data"""
        pass


class ActivitySummaryWidget(BaseWidget):
    """Widget showing activity summary for today"""
    
    def __init__(self):
        super().__init__(width=300, height=180)
        self.title = "📊 Today's Activity"
    
    def update_data(self, store):
        """Fetch today's activity summary"""
        try:
            # Get real data from Selfspy
            self.data = sync_get_activity_summary(24)
        except Exception as e:
            print(f"Error updating activity summary: {e}")
            self.data = {}
    
    def draw(self, view, rect):
        """Draw the activity summary widget"""
        margin = 16
        y = rect.size.height - margin - 20
        
        # Title
        title_attrs = {
            NSFontAttributeName: NSFont.boldSystemFontOfSize_(16),
            NSForegroundColorAttributeName: NSColor.whiteColor()
        }
        title = NSAttributedString.alloc().initWithString_attributes_(self.title, title_attrs)
        title.drawAtPoint_(NSMakePoint(margin, y))
        y -= 35
        
        # Statistics
        content_attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(12),
            NSForegroundColorAttributeName: NSColor.colorWithRed_green_blue_alpha_(0.9, 0.9, 0.9, 1.0)
        }
        
        stats = [
            f"⌨️  {self.data.get('keystrokes', 0):,} keystrokes",
            f"🖱️  {self.data.get('clicks', 0):,} clicks",
            f"⏰ {self.data.get('active_time', '0h 0m')} active",
            f"🪟 {self.data.get('windows_visited', 0)} windows",
            f"📈 {self.data.get('productivity_score', 0)}% productive"
        ]
        
        for stat in stats:
            text = NSAttributedString.alloc().initWithString_attributes_(stat, content_attrs)
            text.drawAtPoint_(NSMakePoint(margin, y))
            y -= 22


class TopAppsWidget(BaseWidget):
    """Widget showing top applications"""
    
    def __init__(self):
        super().__init__(width=320, height=220)
        self.title = "🏆 Top Applications"
    
    def update_data(self, store):
        """Fetch top applications data"""
        try:
            # Get real data from Selfspy
            self.data = sync_get_top_applications(5)
        except Exception as e:
            print(f"Error updating top apps: {e}")
            self.data = {}
    
    def draw(self, view, rect):
        """Draw the top applications widget"""
        margin = 16
        y = rect.size.height - margin - 20
        
        # Title
        title_attrs = {
            NSFontAttributeName: NSFont.boldSystemFontOfSize_(16),
            NSForegroundColorAttributeName: NSColor.whiteColor()
        }
        title = NSAttributedString.alloc().initWithString_attributes_(self.title, title_attrs)
        title.drawAtPoint_(NSMakePoint(margin, y))
        y -= 35
        
        # Applications list
        apps = self.data.get('apps', [])
        for i, app in enumerate(apps[:4]):  # Show top 4
            # App name and time
            name_attrs = {
                NSFontAttributeName: NSFont.systemFontOfSize_(12),
                NSForegroundColorAttributeName: NSColor.whiteColor()
            }
            time_attrs = {
                NSFontAttributeName: NSFont.systemFontOfSize_(11),
                NSForegroundColorAttributeName: NSColor.colorWithRed_green_blue_alpha_(0.7, 0.7, 0.7, 1.0)
            }
            
            name = NSAttributedString.alloc().initWithString_attributes_(
                f"{i+1}. {app['name']}", name_attrs
            )
            time_text = NSAttributedString.alloc().initWithString_attributes_(
                app['time'], time_attrs
            )
            
            name.drawAtPoint_(NSMakePoint(margin, y))
            time_text.drawAtPoint_(NSMakePoint(margin + 140, y))
            
            # Progress bar
            bar_rect = NSMakeRect(margin, y - 8, 200, 4)
            NSColor.colorWithRed_green_blue_alpha_(0.3, 0.3, 0.3, 1.0).set()
            NSBezierPath.fillRect_(bar_rect)
            
            # Fill based on percentage
            fill_width = (app['percentage'] / 100) * 200
            fill_rect = NSMakeRect(margin, y - 8, fill_width, 4)
            NSColor.colorWithRed_green_blue_alpha_(0.0, 0.7, 1.0, 1.0).set()
            NSBezierPath.fillRect_(fill_rect)
            
            y -= 32


class TerminalWidget(BaseWidget):
    """Widget showing terminal command activity"""
    
    def __init__(self):
        super().__init__(width=350, height=200)
        self.title = "🔧 Terminal Activity"
    
    def update_data(self, store):
        """Fetch terminal activity data"""
        try:
            # Get real data from Selfspy terminal tracking
            self.data = sync_get_terminal_activity()
        except Exception as e:
            print(f"Error updating terminal data: {e}")
            self.data = {}
    
    def draw(self, view, rect):
        """Draw the terminal activity widget"""
        margin = 16
        y = rect.size.height - margin - 20
        
        # Title
        title_attrs = {
            NSFontAttributeName: NSFont.boldSystemFontOfSize_(16),
            NSForegroundColorAttributeName: NSColor.whiteColor()
        }
        title = NSAttributedString.alloc().initWithString_attributes_(self.title, title_attrs)
        title.drawAtPoint_(NSMakePoint(margin, y))
        y -= 35
        
        # Summary stats
        summary_attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(11),
            NSForegroundColorAttributeName: NSColor.colorWithRed_green_blue_alpha_(0.8, 0.8, 0.8, 1.0)
        }
        
        summary = f"📊 {self.data.get('commands_today', 0)} commands today  •  🏆 {self.data.get('most_used_command', 'N/A')}  •  📁 {self.data.get('current_project', 'N/A')}"
        summary_text = NSAttributedString.alloc().initWithString_attributes_(summary, summary_attrs)
        summary_text.drawAtPoint_(NSMakePoint(margin, y))
        y -= 25
        
        # Recent commands
        recent_attrs = {
            NSFontAttributeName: NSFont.fontWithName_size_("Monaco", 10),  # Monospace font
            NSForegroundColorAttributeName: NSColor.colorWithRed_green_blue_alpha_(0.9, 0.9, 0.9, 1.0)
        }
        
        recent_label = NSAttributedString.alloc().initWithString_attributes_(
            "Recent commands:", 
            {NSFontAttributeName: NSFont.systemFontOfSize_(11), 
             NSForegroundColorAttributeName: NSColor.colorWithRed_green_blue_alpha_(0.7, 0.7, 0.7, 1.0)}
        )
        recent_label.drawAtPoint_(NSMakePoint(margin, y))
        y -= 20
        
        for cmd in self.data.get('recent_commands', [])[:4]:
            cmd_text = NSAttributedString.alloc().initWithString_attributes_(f"$ {cmd}", recent_attrs)
            cmd_text.drawAtPoint_(NSMakePoint(margin + 8, y))
            y -= 16


class MiniChartsWidget(BaseWidget):
    """Widget showing mini charts and graphs"""
    
    def __init__(self):
        super().__init__(width=280, height=160)
        self.title = "📈 Activity Charts"
    
    def update_data(self, store):
        """Fetch chart data"""
        try:
            # Get real chart data from Selfspy
            self.data = sync_get_hourly_activity_chart(12)
        except Exception as e:
            print(f"Error updating charts: {e}")
            self.data = {}
    
    def draw(self, view, rect):
        """Draw mini charts"""
        margin = 16
        y = rect.size.height - margin - 20
        
        # Title
        title_attrs = {
            NSFontAttributeName: NSFont.boldSystemFontOfSize_(16),
            NSForegroundColorAttributeName: NSColor.whiteColor()
        }
        title = NSAttributedString.alloc().initWithString_attributes_(self.title, title_attrs)
        title.drawAtPoint_(NSMakePoint(margin, y))
        y -= 35
        
        # Simple bar chart for hourly activity
        chart_height = 60
        chart_width = rect.size.width - (margin * 2)
        bar_width = chart_width / 12
        
        activity_data = self.data.get('hourly_activity', [])
        max_value = max(activity_data) if activity_data else 100
        
        for i, value in enumerate(activity_data):
            bar_height = (value / max_value) * chart_height
            bar_rect = NSMakeRect(
                margin + (i * bar_width), 
                y - chart_height, 
                bar_width - 2, 
                bar_height
            )
            
            # Color based on activity level
            if value > 70:
                color = NSColor.colorWithRed_green_blue_alpha_(0.0, 0.8, 0.4, 0.8)  # Green
            elif value > 40:
                color = NSColor.colorWithRed_green_blue_alpha_(1.0, 0.8, 0.0, 0.8)  # Yellow
            else:
                color = NSColor.colorWithRed_green_blue_alpha_(0.6, 0.6, 0.6, 0.8)  # Gray
            
            color.set()
            NSBezierPath.fillRect_(bar_rect)
        
        y -= chart_height + 15
        
        # Stats below chart  
        stats_attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(11),
            NSForegroundColorAttributeName: NSColor.colorWithRed_green_blue_alpha_(0.8, 0.8, 0.8, 1.0)
        }
        
        stats_text = f"🔥 Current streak: {self.data.get('current_streak', '0m')}  •  ⚡ Peak: {self.data.get('peak_hour', 0)}:00"
        stats = NSAttributedString.alloc().initWithString_attributes_(stats_text, stats_attrs)
        stats.drawAtPoint_(NSMakePoint(margin, y))


# Widget registry
WIDGET_TYPES = {
    'activity': ActivitySummaryWidget,
    'apps': TopAppsWidget, 
    'terminal': TerminalWidget,
    'charts': MiniChartsWidget
}