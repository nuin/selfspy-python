"""
Statistics and visualization module for Selfspy
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import select, func, distinct

from .models import Process, Window, Keys, Click
from .config import Settings
from .activity_store import ActivityStore

app = typer.Typer(help="Selfspy Statistics")
console = Console()

@app.callback()
def callback():
    """View statistics about your computer activity"""
    pass

@app.command()
def summary(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze"),
    data_dir: Path = typer.Option(None, "--data-dir", help="Data directory"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password for encrypted data"),
):
    """Show activity summary"""
    try:
        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
        store = ActivityStore(settings, password)
        
        # Create and run async loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            stats = loop.run_until_complete(_get_stats(store, days))
            _display_stats(stats, days)
        finally:
            loop.close()
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)

async def _get_stats(store: ActivityStore, days: int):
    """Get activity statistics"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    async with store.async_session() as session:
        # Get process stats with explicit joins
        process_query = (
            select(
                Process.name,
                func.count(distinct(Window.id)).label('window_count'),
                func.count(distinct(Keys.id)).label('keystroke_count'),
                func.count(distinct(Click.id)).label('click_count')
            )
            .select_from(Process)
            .join(Window, Process.id == Window.process_id)
            .outerjoin(Keys, Window.id == Keys.window_id)
            .outerjoin(Click, Window.id == Click.window_id)
            .where(Window.created_at >= start_date)
            .group_by(Process.name)
        )
        
        process_stats = await session.execute(process_query)
        
        # Get total counts with explicit joins
        totals_query = (
            select(
                func.count(distinct(Keys.id)).label('total_keystrokes'),
                func.count(distinct(Click.id)).label('total_clicks'),
                func.count(distinct(Window.id)).label('total_windows')
            )
            .select_from(Window)
            .outerjoin(Keys, Window.id == Keys.window_id)
            .outerjoin(Click, Window.id == Click.window_id)
            .where(Window.created_at >= start_date)
        )
        
        totals = await session.execute(totals_query)
        
        return {
            'processes': process_stats.all(),
            'totals': totals.first()
        }

def _display_stats(stats, days):
    """Display statistics in a formatted table"""
    # Summary table
    summary = Table(title=f"Activity Summary (Last {days} days)")
    summary.add_column("Metric", style="cyan")
    summary.add_column("Count", justify="right", style="green")
    
    totals = stats['totals']
    summary.add_row("Total Keystrokes", str(totals.total_keystrokes))
    summary.add_row("Total Clicks", str(totals.total_clicks))
    summary.add_row("Windows Tracked", str(totals.total_windows))
    
    console.print(summary)
    console.print()
    
    # Process table
    process_table = Table(title="Activity by Process")
    process_table.add_column("Process", style="cyan")
    process_table.add_column("Windows", justify="right")
    process_table.add_column("Keystrokes", justify="right")
    process_table.add_column("Clicks", justify="right")
    
    for proc in stats['processes']:
        process_table.add_row(
            proc.name,
            str(proc.window_count),
            str(proc.keystroke_count),
            str(proc.click_count)
        )
    
    console.print(process_table)

if __name__ == "__main__":
    app()