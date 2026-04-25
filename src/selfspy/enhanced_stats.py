"""
Enhanced statistics and visualization module for Selfspy with rich visuals
"""

import asyncio
from datetime import datetime
from pathlib import Path

import typer
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from .analytics.viz import (
    get_enhanced_stats as _get_enhanced_stats,
)
from .analytics.viz import (
    get_hourly_stats as _get_hourly_stats,
)
from .analytics.viz import (
    get_timeline_data as _get_timeline_data,
)
from .core import Settings
from .storage import Store

app = typer.Typer(help="Enhanced Selfspy Statistics")
console = Console()


def create_bar_chart(
    data: list[tuple[str, int]], max_width: int = 40, title: str = ""
) -> Table:
    """Create a horizontal bar chart using Rich"""
    if not data:
        return Table()

    table = Table(title=title, show_header=False, box=None, padding=(0, 1))
    table.add_column("Label", style="cyan", width=15)
    table.add_column("Bar", style="blue")
    table.add_column("Value", justify="right", style="green")

    max_value = max(item[1] for item in data) if data else 1

    for label, value in data:
        bar_length = int((value / max_value) * max_width) if max_value > 0 else 0
        bar = "█" * bar_length + "░" * (max_width - bar_length)
        percentage = (value / max_value) * 100 if max_value > 0 else 0

        table.add_row(
            f"{label[:15]:<15}", f"[blue]{bar}[/blue]", f"{value:,} ({percentage:.1f}%)"
        )

    return table


def create_time_heatmap(hourly_data: dict[int, int]) -> Table:
    """Create a time-based heatmap"""
    table = Table(title="⏰ Activity Heatmap (24h)", box=None)

    # Create time blocks
    time_blocks = ["🌙 Night", "🌅 Morning", "☀️  Day", "🌆 Evening"]
    hours_per_block = 6

    for i, block_name in enumerate(time_blocks):
        table.add_column(block_name, justify="center")

    # Calculate activity levels for each block
    block_activities = []
    for block in range(4):
        start_hour = block * hours_per_block
        end_hour = start_hour + hours_per_block
        total_activity = sum(hourly_data.get(h, 0) for h in range(start_hour, end_hour))
        block_activities.append(total_activity)

    max_activity = max(block_activities) if block_activities else 1

    # Create visual representation
    intensity_chars = ["⬛", "🟫", "🟨", "🟩", "🟢"]
    row_data = []

    for activity in block_activities:
        intensity = int((activity / max_activity) * 4) if max_activity > 0 else 0
        char = intensity_chars[intensity]
        row_data.append(f"{char}\n{activity:,}")

    table.add_row(*row_data)
    return table


def calculate_productivity_score(stats: dict) -> tuple[int, str, str]:
    """Calculate a productivity score based on activity patterns"""
    keystrokes = stats["totals"].total_keystrokes
    windows = stats["totals"].total_windows
    processes = len(stats["processes"])

    # Basic scoring algorithm
    base_score = min(100, (keystrokes // 50) + (windows * 2) + (processes * 5))

    # Determine productivity level
    if base_score >= 80:
        level = "🚀 Highly Productive"
        color = "green"
    elif base_score >= 60:
        level = "⚡ Very Active"
        color = "yellow"
    elif base_score >= 40:
        level = "📈 Moderately Active"
        color = "blue"
    elif base_score >= 20:
        level = "🐌 Getting Started"
        color = "magenta"
    else:
        level = "😴 Quiet Period"
        color = "red"

    return base_score, level, color


def create_insights_panel(stats: dict, days: int) -> list[Panel]:
    """Generate insights about user activity"""
    panels = []

    # Productivity insights
    score, level, color = calculate_productivity_score(stats)
    productivity_text = f"Productivity Score: [bold {color}]{score}/100[/bold {color}]\nLevel: [bold]{level}[/bold]"

    # Activity insights
    keystrokes_per_day = stats["totals"].total_keystrokes // max(days, 1)
    windows_per_day = stats["totals"].total_windows // max(days, 1)

    activity_text = f"Daily Averages:\n📝 {keystrokes_per_day:,} keystrokes/day\n🪟 {windows_per_day:,} windows/day"

    # Top app insight
    if stats["processes"]:
        top_app = max(stats["processes"], key=lambda x: x.keystroke_count or 0)
        top_app_text = f"Most Active App:\n🥇 [bold cyan]{top_app.name}[/bold cyan]\n📊 {top_app.keystroke_count:,} keystrokes"
    else:
        top_app_text = "No application data available"

    panels.extend(
        [
            Panel(productivity_text, title="🎯 Productivity", border_style=color),
            Panel(activity_text, title="📊 Activity", border_style="blue"),
            Panel(top_app_text, title="🏆 Champion", border_style="cyan"),
        ]
    )

    return panels


@app.command()
def enhanced(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze"),
    data_dir: Path = typer.Option(None, "--data-dir", help="Data directory"),
    password: str | None = typer.Option(
        None, "--password", "-p", help="Password for encrypted data"
    ),
):
    """Show enhanced activity statistics with rich visualizations"""
    try:
        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
        store = Store(settings, password)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with console.status("[bold green]Analyzing your activity data..."):
                stats = loop.run_until_complete(_get_enhanced_stats(store, days))
                hourly_data = loop.run_until_complete(_get_hourly_stats(store, days))

            _display_enhanced_stats(stats, hourly_data, days)
        finally:
            loop.close()

    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1)


@app.command()
def timeline(
    days: int = typer.Option(1, "--days", "-d", help="Number of days to show"),
    data_dir: Path = typer.Option(None, "--data-dir", help="Data directory"),
    password: str | None = typer.Option(
        None, "--password", "-p", help="Password for encrypted data"
    ),
):
    """Show activity timeline"""
    try:
        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
        store = Store(settings, password)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            timeline_data = loop.run_until_complete(_get_timeline_data(store, days))
            _display_timeline(timeline_data, days)
        finally:
            loop.close()

    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1)


def _display_enhanced_stats(stats: dict, hourly_data: dict[int, int], days: int):
    """Display enhanced statistics with rich visualizations"""

    # Header with emoji and styling
    header = Panel(
        Align.center(
            f"[bold blue]🚀 Selfspy Enhanced Analytics[/bold blue]\n"
            f"[dim]Analysis Period: {days} day{'s' if days != 1 else ''}[/dim]"
        ),
        border_style="blue",
    )
    console.print(header)
    console.print()

    # Insights panels
    insights = create_insights_panel(stats, days)
    console.print(Columns(insights, equal=True))
    console.print()

    # Activity heatmap
    if hourly_data:
        heatmap = create_time_heatmap(hourly_data)
        console.print(
            Panel(heatmap, title="🕐 When Are You Most Active?", border_style="yellow")
        )
        console.print()

    # Enhanced totals table
    totals_table = Table(title="📈 Overall Statistics", box=None)
    totals_table.add_column("Metric", style="cyan", width=20)
    totals_table.add_column("Value", style="green", justify="right")
    totals_table.add_column("Daily Avg", style="yellow", justify="right")

    totals = stats["totals"]
    metrics = [
        (
            "🔤 Total Keystrokes",
            totals.total_keystrokes,
            totals.total_keystrokes // max(days, 1),
        ),
        ("🖱️  Total Clicks", totals.total_clicks, totals.total_clicks // max(days, 1)),
        (
            "🪟 Windows Visited",
            totals.total_windows,
            totals.total_windows // max(days, 1),
        ),
        (
            "📱 Applications Used",
            totals.total_processes,
            totals.total_processes // max(days, 1),
        ),
    ]

    for metric, total, daily in metrics:
        totals_table.add_row(metric, f"{total:,}", f"{daily:,}")

    console.print(totals_table)
    console.print()

    # Top applications bar chart
    if stats["processes"]:
        app_data = [
            (proc.name, proc.keystroke_count or 0) for proc in stats["processes"][:10]
        ]
        app_chart = create_bar_chart(app_data, title="🏆 Most Active Applications")
        console.print(app_chart)
        console.print()

    # Detailed process table with more info
    if stats["processes"]:
        process_table = Table(title="📊 Detailed Application Statistics")
        process_table.add_column("Application", style="cyan")
        process_table.add_column("Windows", justify="right")
        process_table.add_column("Keystrokes", justify="right", style="green")
        process_table.add_column("Clicks", justify="right", style="blue")
        process_table.add_column("First Seen", style="dim")
        process_table.add_column("Last Seen", style="dim")

        for proc in stats["processes"][:15]:  # Show top 15
            first_seen = (
                proc.first_seen.strftime("%m/%d %H:%M") if proc.first_seen else "N/A"
            )
            last_seen = (
                proc.last_seen.strftime("%m/%d %H:%M") if proc.last_seen else "N/A"
            )

            process_table.add_row(
                f"[bold]{proc.name}[/bold]",
                str(proc.window_count),
                f"{proc.keystroke_count:,}",
                f"{proc.click_count:,}",
                first_seen,
                last_seen,
            )

        console.print(process_table)


def _display_timeline(timeline_data, days: int):
    """Display activity timeline"""
    console.print(
        Panel(
            Align.center(
                f"[bold cyan]📅 Activity Timeline - Last {days} Day(s)[/bold cyan]"
            ),
            border_style="cyan",
        )
    )
    console.print()

    tree = Tree("🕐 Recent Activity")

    current_hour = None
    hour_node = None

    for row in timeline_data:
        activity_time = row.created_at
        hour_str = activity_time.strftime("%H:00")

        if hour_str != current_hour:
            current_hour = hour_str
            hour_node = tree.add(
                f"[bold blue]{activity_time.strftime('%m/%d %H:00')}[/bold blue]"
            )

        if hour_node:
            keystroke_info = (
                f" ({row.keystrokes:,} keystrokes)" if row.keystrokes > 0 else ""
            )
            activity_info = f"[green]{row.process_name}[/green]: {row.title[:50]}{'...' if len(row.title) > 50 else ''}{keystroke_info}"
            hour_node.add(activity_info)

    console.print(tree)


# Add to the main stats app
@app.command()
def live(
    refresh_rate: int = typer.Option(
        5, "--refresh", "-r", help="Refresh rate in seconds"
    ),
    data_dir: Path = typer.Option(None, "--data-dir", help="Data directory"),
):
    """Live activity dashboard"""
    console.print("[bold green]🔴 Live Activity Monitor[/bold green]")
    console.print("[dim]Press Ctrl+C to exit[/dim]\n")

    try:
        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
        store = Store(settings, password=None)

        with console.screen():
            while True:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    stats = loop.run_until_complete(_get_enhanced_stats(store, 1))

                    console.clear()
                    console.print(
                        f"[bold blue]🚀 Live Dashboard[/bold blue] - Updated: {datetime.now().strftime('%H:%M:%S')}"
                    )
                    console.print(
                        f"Keystrokes today: [green]{stats['totals'].total_keystrokes:,}[/green]"
                    )
                    console.print(
                        f"Windows opened: [yellow]{stats['totals'].total_windows:,}[/yellow]"
                    )

                    if stats["processes"]:
                        top_app = stats["processes"][0]
                        console.print(
                            f"Most active: [cyan]{top_app.name}[/cyan] ({top_app.keystroke_count:,} keystrokes)"
                        )

                    loop.close()

                    import time

                    time.sleep(refresh_rate)

                except KeyboardInterrupt:
                    break

    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")


if __name__ == "__main__":
    app()
