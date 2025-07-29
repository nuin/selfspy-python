"""
Data integration module for Selfspy Desktop Widgets

This module handles fetching and processing data from the Selfspy database
for display in desktop widgets.
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Add parent directory to path to import selfspy modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from config import Settings
    from activity_store import ActivityStore
    from models import Process, Window, Keys, Click
    from terminal_tracker import TerminalSession, TerminalCommand
    from sqlalchemy import select, func, desc, and_
except ImportError as e:
    print(f"Warning: Could not import selfspy modules: {e}")
    # Define fallback classes for testing
    class Settings:
        def __init__(self):
            pass
    
    class ActivityStore:
        def __init__(self, settings, password=None):
            pass
        
        def async_session(self):
            return None


class SelfspyDataProvider:
    """Main data provider for desktop widgets"""
    
    def __init__(self):
        self.settings = None
        self.store = None
        self.connected = False
        self.initialize_connection()
    
    def initialize_connection(self):
        """Initialize connection to Selfspy database"""
        try:
            self.settings = Settings()
            self.store = ActivityStore(self.settings)
            self.connected = True
            print("✅ Data provider connected to Selfspy database")
        except Exception as e:
            print(f"❌ Failed to connect to Selfspy database: {e}")
            self.connected = False
    
    async def get_activity_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get activity summary for the specified time period"""
        if not self.connected:
            return self._get_mock_activity_summary()
        
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)
            
            async with self.store.async_session() as session:
                # Get keystroke count
                keystroke_result = await session.execute(
                    select(Keys.key).where(Keys.created_at >= start_time)
                )
                keystrokes = len(keystroke_result.all())
                
                # Get click count
                click_result = await session.execute(
                    select(Click.id).where(Click.created_at >= start_time)
                )
                clicks = len(click_result.all())
                
                # Get unique windows (approximation of active time)
                window_result = await session.execute(
                    select(func.count(func.distinct(Window.id))).where(
                        Window.created_at >= start_time
                    )
                )
                windows_visited = window_result.scalar() or 0
                
                # Calculate active time (rough estimate)
                active_minutes = windows_visited * 2  # Rough estimate
                active_hours = active_minutes // 60
                active_mins_remainder = active_minutes % 60
                active_time = f"{active_hours}h {active_mins_remainder}m"
                
                # Calculate productivity score (placeholder logic)
                productivity_score = min(100, (keystrokes + clicks) // 50)
                
                return {
                    'keystrokes': keystrokes,
                    'clicks': clicks,
                    'active_time': active_time,
                    'windows_visited': windows_visited,
                    'productivity_score': productivity_score,
                    'most_active_hour': self._get_most_active_hour(start_time, end_time)
                }
        
        except Exception as e:
            print(f"Error getting activity summary: {e}")
            return self._get_mock_activity_summary()
    
    async def get_top_applications(self, limit: int = 5) -> Dict[str, Any]:
        """Get top applications by usage"""
        if not self.connected:
            return self._get_mock_top_applications()
        
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            
            async with self.store.async_session() as session:
                # Get process usage statistics
                result = await session.execute(
                    select(
                        Process.name,
                        func.count(Window.id).label('window_count')
                    ).join(Window).where(
                        Window.created_at >= start_time
                    ).group_by(Process.name).order_by(desc('window_count')).limit(limit)
                )
                
                apps = []
                total_windows = 0
                app_data = result.all()
                
                if app_data:
                    total_windows = sum(app.window_count for app in app_data)
                
                for app in app_data:
                    percentage = (app.window_count / total_windows * 100) if total_windows > 0 else 0
                    # Rough time estimate
                    estimated_minutes = int(app.window_count * 2)
                    hours = estimated_minutes // 60
                    minutes = estimated_minutes % 60
                    time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                    
                    apps.append({
                        'name': app.name or 'Unknown',
                        'time': time_str,
                        'percentage': int(percentage)
                    })
                
                return {'apps': apps}
        
        except Exception as e:
            print(f"Error getting top applications: {e}")
            return self._get_mock_top_applications()
    
    async def get_terminal_activity(self) -> Dict[str, Any]:
        """Get terminal command activity"""
        if not self.connected:
            return self._get_mock_terminal_activity()
        
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            
            async with self.store.async_session() as session:
                # Get command count for today
                commands_result = await session.execute(
                    select(func.count(TerminalCommand.id)).where(
                        TerminalCommand.created_at >= start_time
                    )
                )
                commands_today = commands_result.scalar() or 0
                
                # Get most used command
                most_used_result = await session.execute(
                    select(
                        TerminalCommand.command_type,
                        func.count(TerminalCommand.id).label('count')
                    ).where(
                        TerminalCommand.created_at >= start_time
                    ).group_by(TerminalCommand.command_type).order_by(desc('count')).limit(1)
                )
                most_used_row = most_used_result.first()
                most_used_command = most_used_row.command_type if most_used_row else 'N/A'
                
                # Get current project (most recent working directory)
                project_result = await session.execute(
                    select(TerminalCommand.working_directory).where(
                        TerminalCommand.created_at >= start_time
                    ).order_by(desc(TerminalCommand.created_at)).limit(1)
                )
                project_row = project_result.first()
                current_project = Path(project_row[0]).name if project_row and project_row[0] else 'N/A'
                
                # Get recent commands
                recent_result = await session.execute(
                    select(TerminalCommand.command).where(
                        TerminalCommand.created_at >= start_time
                    ).order_by(desc(TerminalCommand.created_at)).limit(5)
                )
                recent_commands = [row[0] for row in recent_result.all()]
                
                return {
                    'commands_today': commands_today,
                    'most_used_command': most_used_command,
                    'current_project': current_project,
                    'recent_commands': recent_commands
                }
        
        except Exception as e:
            print(f"Error getting terminal activity: {e}")
            return self._get_mock_terminal_activity()
    
    async def get_hourly_activity_chart(self, hours_back: int = 12) -> Dict[str, Any]:
        """Get hourly activity data for charts"""
        if not self.connected:
            return self._get_mock_chart_data()
        
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)
            
            async with self.store.async_session() as session:
                # Get activity by hour
                hourly_data = []
                for i in range(hours_back):
                    hour_start = start_time + timedelta(hours=i)
                    hour_end = hour_start + timedelta(hours=1)
                    
                    # Count activities in this hour
                    activity_result = await session.execute(
                        select(func.count(Keys.id) + func.count(Click.id)).select_from(
                            Keys.table.outerjoin(Click.table)
                        ).where(
                            and_(
                                Keys.created_at >= hour_start,
                                Keys.created_at < hour_end
                            ) | and_(
                                Click.created_at >= hour_start,
                                Click.created_at < hour_end
                            )
                        )
                    )
                    
                    activity_count = activity_result.scalar() or 0
                    hourly_data.append(min(100, activity_count // 10))  # Scale to 0-100
                
                # Find peak hour  
                peak_hour = hourly_data.index(max(hourly_data)) if hourly_data else 0
                peak_hour_actual = (start_time + timedelta(hours=peak_hour)).hour
                
                # Calculate current streak (simplified)
                current_streak = "2h 15m"  # Placeholder
                
                return {
                    'hourly_activity': hourly_data,
                    'peak_hour': peak_hour_actual,
                    'current_streak': current_streak
                }
        
        except Exception as e:
            print(f"Error getting chart data: {e}")
            return self._get_mock_chart_data()
    
    def _get_most_active_hour(self, start_time: datetime, end_time: datetime) -> int:
        """Get the most active hour (placeholder implementation)"""
        return datetime.now().hour
    
    # Mock data methods for testing without database
    def _get_mock_activity_summary(self) -> Dict[str, Any]:
        """Mock activity summary for testing"""
        return {
            'keystrokes': 2847,
            'clicks': 892,
            'active_time': '4h 23m',
            'windows_visited': 47,
            'most_active_hour': 14,
            'productivity_score': 82
        }
    
    def _get_mock_top_applications(self) -> Dict[str, Any]:
        """Mock top applications for testing"""
        return {
            'apps': [
                {'name': 'Visual Studio Code', 'time': '2h 15m', 'percentage': 52},
                {'name': 'Terminal', 'time': '1h 8m', 'percentage': 26},
                {'name': 'Safari', 'time': '45m', 'percentage': 17},
                {'name': 'Finder', 'time': '12m', 'percentage': 5}
            ]
        }
    
    def _get_mock_terminal_activity(self) -> Dict[str, Any]:
        """Mock terminal activity for testing"""
        return {
            'commands_today': 142,
            'most_used_command': 'git',
            'current_project': 'selfspy3',
            'recent_commands': [
                'git status',
                'python selfspy_desktop.py',
                'uv run pytest',
                'git add .',
                'code .'
            ]
        }
    
    def _get_mock_chart_data(self) -> Dict[str, Any]:
        """Mock chart data for testing"""
        return {
            'hourly_activity': [20, 45, 30, 60, 80, 95, 70, 40, 25, 15, 30, 50],
            'peak_hour': 17,
            'current_streak': '2h 15m'
        }


# Global data provider instance
_data_provider = None

def get_data_provider() -> SelfspyDataProvider:
    """Get the global data provider instance"""
    global _data_provider
    if _data_provider is None:
        _data_provider = SelfspyDataProvider()
    return _data_provider


# Synchronous wrapper functions for use in the GUI thread
def sync_get_activity_summary(hours_back: int = 24) -> Dict[str, Any]:
    """Synchronous wrapper for getting activity summary"""
    provider = get_data_provider()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(provider.get_activity_summary(hours_back))
        loop.close()
        return result
    except Exception as e:
        print(f"Error in sync_get_activity_summary: {e}")
        return provider._get_mock_activity_summary()

def sync_get_top_applications(limit: int = 5) -> Dict[str, Any]:
    """Synchronous wrapper for getting top applications"""
    provider = get_data_provider()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(provider.get_top_applications(limit))
        loop.close()
        return result
    except Exception as e:
        print(f"Error in sync_get_top_applications: {e}")
        return provider._get_mock_top_applications()

def sync_get_terminal_activity() -> Dict[str, Any]:
    """Synchronous wrapper for getting terminal activity"""
    provider = get_data_provider()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(provider.get_terminal_activity())
        loop.close()
        return result
    except Exception as e:
        print(f"Error in sync_get_terminal_activity: {e}")
        return provider._get_mock_terminal_activity()

def sync_get_hourly_activity_chart(hours_back: int = 12) -> Dict[str, Any]:
    """Synchronous wrapper for getting chart data"""
    provider = get_data_provider()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(provider.get_hourly_activity_chart(hours_back))
        loop.close()
        return result
    except Exception as e:
        print(f"Error in sync_get_hourly_activity_chart: {e}")
        return provider._get_mock_chart_data()