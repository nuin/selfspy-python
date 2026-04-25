"""selfspy stats — basic activity statistics dashboard."""

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

from ..analytics.stats import get_stats
from ..core import Settings
from ..storage import Store

app = typer.Typer(help="Selfspy Statistics")
console = Console()


@app.callback()
def callback():
    """View statistics about your computer activity."""
    pass


@app.command()
def summary(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze"),
    data_dir: Path = typer.Option(None, "--data-dir", help="Data directory"),
    password: str | None = typer.Option(
        None, "--password", "-p", help="Password for encrypted data"
    ),
):
    """Show activity summary."""
    try:
        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
        store = Store(settings, password)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            stats = loop.run_until_complete(get_stats(store, days))
            _display_stats(stats, days)
        finally:
            loop.close()

    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1) from e


def _display_stats(stats, days):
    """Display rich statistics dashboard."""
    totals = stats["totals"]
    processes = sorted(
        stats["processes"],
        key=lambda x: x.keystroke_count + x.click_count,
        reverse=True,
    )

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

    start = stats["start_date"].strftime("%Y-%m-%d")
    end = stats["end_date"].strftime("%Y-%m-%d")
    header_text = Text()
    header_text.append("📊 ", style="bold blue")
    header_text.append("SELFSPY STATISTICS", style="bold white")
    header_text.append(f"\n{start} to {end} ({days} days)", style="dim")
    layout["header"].update(Panel(Align.center(header_text), style="bold blue"))

    overview_table = Table.grid(padding=(0, 2))
    overview_table.add_column(style="cyan", justify="left")
    overview_table.add_column(style="white bold", justify="right")
    overview_table.add_column(style="dim", justify="left")

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

            rank = (
                "🥇"
                if idx == 1
                else "🥈"
                if idx == 2
                else "🥉"
                if idx == 3
                else f"{idx:2d}"
            )

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

    if stats["daily_keys"] or stats["daily_clicks"]:
        daily_text = Text()
        daily_text.append("Keystrokes per Day\n", style="bold green")

        all_dates: dict[str, int] = {}
        current_date = stats["start_date"].date()
        while current_date <= stats["end_date"].date():
            date_str = str(current_date)
            keys = stats["daily_keys"].get(date_str, 0)
            all_dates[date_str] = keys
            current_date += timedelta(days=1)

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

    insights_grid = Table.grid(padding=(0, 1))
    insights_grid.add_column(style="cyan")
    insights_grid.add_column(style="white")

    if processes:
        top_app = processes[0]
        insights_grid.add_row(
            "Most Active:", f"[bold green]{top_app.name}[/bold green]"
        )

        if avg_keys_per_day > 10000:
            activity_level = "[bold green]Very High ⚡[/bold green]"
        elif avg_keys_per_day > 5000:
            activity_level = "[green]High 📈[/green]"
        elif avg_keys_per_day > 2000:
            activity_level = "[yellow]Moderate 📊[/yellow]"
        else:
            activity_level = "[dim]Low 📉[/dim]"

        insights_grid.add_row("Activity Level:", activity_level)

        if totals.total_clicks > 0:
            ratio = totals.total_keystrokes / totals.total_clicks
            insights_grid.add_row("Keys/Click Ratio:", f"{ratio:.1f}")

        productivity = min(100, int(avg_keys_per_day / 100))
        insights_grid.add_row("Productivity:", f"[bold]{productivity}/100[/bold]")

    layout["insights"].update(
        Panel(insights_grid, title="[bold]💡 Insights[/bold]", border_style="magenta")
    )

    footer_text = Text()
    footer_text.append(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim"
    )
    footer_text.append("  •  ", style="dim")
    footer_text.append("Selfspy", style="bold cyan")
    layout["footer"].update(Align.center(footer_text))

    console.print(layout)
