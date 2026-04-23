"""
Statistics and visualization module for Selfspy
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import typer
from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from sqlalchemy import distinct, func, select

from .config import Settings
from .storage import Click, Keys, Process, Store, Window

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
    password: str | None = typer.Option(
        None, "--password", "-p", help="Password for encrypted data"
    ),
):
    """Show activity summary"""
    try:
        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
        store = Store(settings, password)

        # Create and run async loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            stats = loop.run_until_complete(_get_stats(store, days))
            _display_stats(stats, days)
        finally:
            loop.close()

    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1)


async def _get_stats(store: Store, days: int):
    """Get activity statistics"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    async with store.async_session() as session:
        # Get process stats using subqueries to avoid cartesian product
        # Subquery for keystrokes
        keystroke_subq = (
            select(Keys.process_id, func.sum(Keys.count).label("keystroke_count"))
            .where(Keys.created_at >= start_date)
            .group_by(Keys.process_id)
            .subquery()
        )

        # Subquery for clicks
        click_subq = (
            select(Click.process_id, func.count(Click.id).label("click_count"))
            .where(Click.created_at >= start_date)
            .group_by(Click.process_id)
            .subquery()
        )

        # Main query with proper joins
        process_query = (
            select(
                Process.name,
                func.count(distinct(Window.id)).label("window_count"),
                func.coalesce(keystroke_subq.c.keystroke_count, 0).label(
                    "keystroke_count"
                ),
                func.coalesce(click_subq.c.click_count, 0).label("click_count"),
            )
            .select_from(Process)
            .join(Window, Process.id == Window.process_id)
            .outerjoin(keystroke_subq, Process.id == keystroke_subq.c.process_id)
            .outerjoin(click_subq, Process.id == click_subq.c.process_id)
            .where(Window.created_at >= start_date)
            .group_by(
                Process.name, keystroke_subq.c.keystroke_count, click_subq.c.click_count
            )
        )

        process_stats = await session.execute(process_query)

        # Get total counts using separate queries to avoid cartesian product
        keystroke_total = await session.execute(
            select(func.coalesce(func.sum(Keys.count), 0)).where(
                Keys.created_at >= start_date
            )
        )
        total_keystrokes = keystroke_total.scalar()

        click_total = await session.execute(
            select(func.count(Click.id)).where(Click.created_at >= start_date)
        )
        total_clicks = click_total.scalar()

        window_total = await session.execute(
            select(func.count(distinct(Window.id))).where(
                Window.created_at >= start_date
            )
        )
        total_windows = window_total.scalar()

        # Get daily activity breakdown
        daily_keys = await session.execute(
            select(
                func.date(Keys.created_at).label("date"),
                func.sum(Keys.count).label("count"),
            )
            .where(Keys.created_at >= start_date)
            .group_by(func.date(Keys.created_at))
            .order_by(func.date(Keys.created_at))
        )

        daily_clicks = await session.execute(
            select(
                func.date(Click.created_at).label("date"),
                func.count(Click.id).label("count"),
            )
            .where(Click.created_at >= start_date)
            .group_by(func.date(Click.created_at))
            .order_by(func.date(Click.created_at))
        )

        # Create a named tuple for consistency with the rest of the code
        from collections import namedtuple

        Totals = namedtuple(
            "Totals", ["total_keystrokes", "total_clicks", "total_windows"]
        )
        totals = Totals(total_keystrokes, total_clicks, total_windows)

        return {
            "processes": process_stats.all(),
            "totals": totals,
            "daily_keys": {str(row.date): row.count for row in daily_keys.all()},
            "daily_clicks": {str(row.date): row.count for row in daily_clicks.all()},
            "days": days,
            "start_date": start_date,
            "end_date": end_date,
        }


def _create_bar_chart(data: dict, max_width: int = 40) -> str:
    """Create a horizontal bar chart"""
    if not data:
        return ""

    max_val = max(data.values()) if data.values() else 1
    bars = []

    for date, count in sorted(data.items()):
        bar_len = int((count / max_val) * max_width) if max_val > 0 else 0
        bar = "█" * bar_len + "░" * (max_width - bar_len)
        bars.append(f"{date[-5:]}: {bar} {count:,}")

    return "\n".join(bars)


def _display_stats(stats, days):
    """Display rich statistics dashboard"""
    totals = stats["totals"]
    processes = sorted(
        stats["processes"],
        key=lambda x: x.keystroke_count + x.click_count,
        reverse=True,
    )

    # Create layout
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=1),
    )

    layout["main"].split_row(
        Layout(name="left", ratio=2), Layout(name="right", ratio=1)
    )

    layout["left"].split_column(
        Layout(name="overview", ratio=1), Layout(name="apps", ratio=2)
    )

    layout["right"].split_column(
        Layout(name="daily", ratio=1), Layout(name="insights", ratio=1)
    )

    # Header
    start = stats["start_date"].strftime("%Y-%m-%d")
    end = stats["end_date"].strftime("%Y-%m-%d")
    header_text = Text()
    header_text.append("📊 ", style="bold blue")
    header_text.append("SELFSPY STATISTICS", style="bold white")
    header_text.append(f"\n{start} to {end} ({days} days)", style="dim")
    layout["header"].update(Panel(Align.center(header_text), style="bold blue"))

    # Overview Panel
    overview_table = Table.grid(padding=(0, 2))
    overview_table.add_column(style="cyan", justify="left")
    overview_table.add_column(style="white bold", justify="right")
    overview_table.add_column(style="dim", justify="left")

    # Calculate averages
    avg_keys_per_day = int(totals.total_keystrokes / days) if days > 0 else 0
    avg_clicks_per_day = int(totals.total_clicks / days) if days > 0 else 0

    overview_table.add_row(
        "⌨  Total Keystrokes",
        f"{totals.total_keystrokes:,}",
        f"({avg_keys_per_day:,}/day)",
    )
    overview_table.add_row(
        "🖱  Total Clicks", f"{totals.total_clicks:,}", f"({avg_clicks_per_day:,}/day)"
    )
    overview_table.add_row(
        "🪟  Windows Tracked", f"{totals.total_windows:,}", f"({len(processes)} apps)"
    )
    overview_table.add_row(
        "📊  Total Events", f"{totals.total_keystrokes + totals.total_clicks:,}", ""
    )

    layout["overview"].update(
        Panel(overview_table, title="[bold]Overview[/bold]", border_style="green")
    )

    # Top Applications Panel
    if processes:
        total_activity = sum(p.keystroke_count + p.click_count for p in processes)

        apps_table = Table(show_header=True, header_style="bold cyan", box=None)
        apps_table.add_column("Rank", style="dim", width=4)
        apps_table.add_column("Application", style="white")
        apps_table.add_column("Keys", justify="right", style="green")
        apps_table.add_column("Clicks", justify="right", style="yellow")
        apps_table.add_column("Windows", justify="right", style="magenta")
        apps_table.add_column("Share", justify="right")

        for idx, proc in enumerate(processes[:15], 1):
            activity = proc.keystroke_count + proc.click_count
            percentage = (activity / total_activity * 100) if total_activity > 0 else 0

            # Medal for top 3
            rank = (
                "🥇"
                if idx == 1
                else "🥈"
                if idx == 2
                else "🥉"
                if idx == 3
                else f"{idx:2d}"
            )

            # Progress bar - limit to 15 characters max for proper alignment
            max_bar_width = 15
            bar_length = int((percentage / 100) * max_bar_width)
            bar = "█" * bar_length

            apps_table.add_row(
                rank,
                proc.name[:25],
                f"{proc.keystroke_count:,}",
                f"{proc.click_count:,}",
                str(proc.window_count),
                f"{bar} {percentage:.1f}%",
            )

        layout["apps"].update(
            Panel(
                apps_table,
                title="[bold]🏆 Top Applications[/bold]",
                border_style="blue",
            )
        )
    else:
        layout["apps"].update(
            Panel(
                Align.center("[dim]No application data available[/dim]"),
                title="[bold]Top Applications[/bold]",
                border_style="blue",
            )
        )

    # Daily Activity Panel
    if stats["daily_keys"] or stats["daily_clicks"]:
        daily_text = Text()
        daily_text.append("Keystrokes per Day\n", style="bold green")

        # Get all dates in range
        all_dates = {}
        current_date = stats["start_date"].date()
        while current_date <= stats["end_date"].date():
            date_str = str(current_date)
            keys = stats["daily_keys"].get(date_str, 0)
            all_dates[date_str] = keys
            current_date += timedelta(days=1)

        # Show last 7 days or all if fewer
        recent_dates = dict(sorted(all_dates.items())[-7:])
        max_keys = max(recent_dates.values()) if recent_dates.values() else 1

        for date, count in recent_dates.items():
            bar_len = int((count / max_keys) * 25) if max_keys > 0 else 0
            bar = "█" * bar_len + "░" * (25 - bar_len)
            daily_text.append(f"{date[-5:]}: ", style="dim")
            daily_text.append(f"{bar} ", style="green")
            daily_text.append(f"{count:,}\n", style="white")

        layout["daily"].update(
            Panel(
                daily_text,
                title="[bold]📅 Recent Activity[/bold]",
                border_style="yellow",
            )
        )
    else:
        layout["daily"].update(
            Panel(
                Align.center("[dim]No daily data available[/dim]"),
                title="[bold]Daily Activity[/bold]",
                border_style="yellow",
            )
        )

    # Insights Panel
    insights_grid = Table.grid(padding=(0, 1))
    insights_grid.add_column(style="cyan")
    insights_grid.add_column(style="white")

    if processes:
        # Most used app
        top_app = processes[0]
        insights_grid.add_row(
            "Most Active:", f"[bold green]{top_app.name}[/bold green]"
        )

        # Activity level
        if avg_keys_per_day > 10000:
            activity_level = "[bold green]Very High ⚡[/bold green]"
        elif avg_keys_per_day > 5000:
            activity_level = "[green]High 📈[/green]"
        elif avg_keys_per_day > 2000:
            activity_level = "[yellow]Moderate 📊[/yellow]"
        else:
            activity_level = "[dim]Low 📉[/dim]"

        insights_grid.add_row("Activity Level:", activity_level)

        # Key/Click ratio
        if totals.total_clicks > 0:
            ratio = totals.total_keystrokes / totals.total_clicks
            insights_grid.add_row("Keys/Click Ratio:", f"{ratio:.1f}")

        # Productivity estimate (very rough heuristic)
        productivity = min(100, int(avg_keys_per_day / 100))
        insights_grid.add_row("Productivity:", f"[bold]{productivity}/100[/bold]")

    layout["insights"].update(
        Panel(insights_grid, title="[bold]💡 Insights[/bold]", border_style="magenta")
    )

    # Footer
    footer_text = Text()
    footer_text.append(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim"
    )
    footer_text.append("  •  ", style="dim")
    footer_text.append("Selfspy", style="bold cyan")
    layout["footer"].update(Align.center(footer_text))

    console.print(layout)


if __name__ == "__main__":
    app()
