"""
Statistics and visualization module for Selfspy
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

from sqlalchemy import select, func
from rich.console import Console
from rich.table import Table
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .models import Process, Window, Keys, Click
from .config import Settings
from .activity_store import ActivityStore

console = Console()
app = FastAPI(title="Selfspy Stats")

class StatsGenerator:
    """Generate statistics from activity data"""
    
    def __init__(self, store: ActivityStore):
        self.store = store
        
    async def get_process_stats(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Get process usage statistics"""
        async with self.store.async_session() as session:
            query = select(
                Process.name,
                Process.bundle_id,
                func.count(Window.id).label('window_count'),
                func.sum(Keys.count).label('keystroke_count'),
                func.count(Click.id).label('click_count')
            ).join(Window).outerjoin(Keys).outerjoin(Click)
            
            if start_date:
                query = query.where(Window.created_at >= start_date)
            if end_date:
                query = query.where(Window.created_at <= end_date)
                
            query = query.group_by(Process.id).order_by(func.count(Window.id).desc())
            
            result = await session.execute(query)
            return [
                {
                    'name': row.name,
                    'bundle_id': row.bundle_id,
                    'window_count': row.window_count,
                    'keystroke_count': row.keystroke_count or 0,
                    'click_count': row.click_count or 0
                }
                for row in result
            ]
            
    async def get_hourly_activity(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Get hourly activity patterns"""
        async with self.store.async_session() as session:
            query = select(
                func.strftime('%H', Window.created_at).label('hour'),
                func.count(Window.id).label('window_count'),
                func.count(Keys.id).label('keystroke_count'),
                func.count(Click.id).label('click_count')
            ).outerjoin(Keys).outerjoin(Click)
            
            if start_date:
                query = query.where(Window.created_at >= start_date)
            if end_date:
                query = query.where(Window.created_at <= end_date)
                
            query = query.group_by('hour').order_by('hour')
            
            result = await session.execute(query)
            return [
                {
                    'hour': int(row.hour),
                    'window_count': row.window_count,
                    'keystroke_count': row.keystroke_count,
                    'click_count': row.click_count
                }
                for row in result
            ]
            
    async def get_active_periods(
        self,
        threshold: int = 300,  # 5 minutes
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Tuple[datetime, datetime]]:
        """Get active time periods"""
        async with self.store.async_session() as session:
            # Get all activity timestamps
            query = select(Window.created_at).union(
                select(Keys.created_at),
                select(Click.created_at)
            ).order_by('created_at')
            
            if start_date:
                query = query.where(Window.created_at >= start_date)
            if end_date:
                query = query.where(Window.created_at <= end_date)
                
            result = await session.execute(query)
            timestamps = [row[0] for row in result]
            
            # Find active periods
            active_periods = []
            if not timestamps:
                return active_periods
                
            period_start = timestamps[0]
            last_time = timestamps[0]
            
            for timestamp in timestamps[1:]:
                if (timestamp - last_time).total_seconds() > threshold:
                    active_periods.append((period_start, last_time))
                    period_start = timestamp
                last_time = timestamp
                
            active_periods.append((period_start, last_time))
            return active_periods

    def format_text_report(
        self,
        process_stats: List[Dict],
        hourly_stats: List[Dict],
        active_periods: List[Tuple[datetime, datetime]]
    ) -> str:
        """Format statistics as text report"""
        # Process table
        process_table = Table(title="Process Usage")
        process_table.add_column("Process")
        process_table.add_column("Windows")
        process_table.add_column("Keystrokes")
        process_table.add_column("Clicks")
        
        for proc in process_stats[:10]:  # Top 10
            process_table.add_row(
                proc['name'],
                str(proc['window_count']),
                str(proc['keystroke_count']),
                str(proc['click_count'])
            )
            
        # Activity periods
        total_active_time = sum(
            (end - start).total_seconds()
            for start, end in active_periods
        )
        
        # Format report
        report = []
        report.append(process_table)
        report.append(f"\nTotal active time: {timedelta(seconds=total_active_time)}")
        
        return "\n".join(str(line) for line in report)

# FastAPI routes for web visualization
@app.get("/", response_class=HTMLResponse)
async def stats_dashboard():
    """Render stats dashboard"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Selfspy Stats</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-3xl font-bold mb-8">Activity Statistics</h1>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div class="bg-white p-6 rounded-lg shadow">
                    <div id="processChart"></div>
                </div>
                <div class="bg-white p-6 rounded-lg shadow">
                    <div id="hourlyChart"></div>
                </div>
            </div>
            
            <div class="mt-8 bg-white p-6 rounded-lg shadow">
                <div id="timelineChart"></div>
            </div>
        </div>
        
        <script>
            async function loadStats() {
                const [processes, hourly, periods] = await Promise.all([
                    fetch('/api/processes').then(r => r.json()),
                    fetch('/api/hourly').then(r => r.json()),
                    fetch('/api/periods').then(r => r.json())
                ]);
                
                // Process chart
                Plotly.newPlot('processChart', [{
                    type: 'bar',
                    x: processes.map(p => p.name),
                    y: processes.map(p => p.window_count),
                    name: 'Windows'
                }], {
                    title: 'Process Usage',
                    barmode: 'stack'
                });
                
                // Hourly chart
                Plotly.newPlot('hourlyChart', [{
                    type: 'scatter',
                    x: hourly.map(h => h.hour),
                    y: hourly.map(h => h.window_count),
                    name: 'Activity'
                }], {
                    title: 'Hourly Activity',
                    xaxis: {title: 'Hour'},
                    yaxis: {title: 'Activity Count'}
                });
                
                // Timeline
                Plotly.newPlot('timelineChart', [{
                    type: 'scatter',
                    x: periods.map(p => p.start),
                    y: periods.map(() => 1),
                    mode: 'markers',
                    name: 'Active Periods'
                }], {
                    title: 'Activity Timeline',
                    xaxis: {
                        type: 'date',
                        title: 'Time'
                    },
                    yaxis: {
                        visible: false
                    }
                });
            }
            
            loadStats();
        </script>
    </body>
    </html>
    """

@app.get("/api/processes")
async def get_processes(
    store: ActivityStore,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get process statistics"""
    stats = StatsGenerator(store)
    return await stats.get_process_stats(
        datetime.fromisoformat(start_date) if start_date else None,
        datetime.fromisoformat(end_date) if end_date else None
    )

@app.get("/api/hourly")
async def get_hourly(
    store: ActivityStore,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get hourly statistics"""
    stats = StatsGenerator(store)
    return await stats.get_hourly_activity(
        datetime.fromisoformat(start_date) if start_date else None,
        datetime.fromisoformat(end_date) if end_date else None
    )

@app.get("/api/periods")
async def get_periods(
    store: ActivityStore,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get active periods"""
    stats = StatsGenerator(store)
    periods = await stats.get_active_periods(
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None
    )
    return [
        {'start': start.isoformat(), 'end': end.isoformat()}
        for start, end in periods
    ]

def main():
    """CLI entry point"""
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()