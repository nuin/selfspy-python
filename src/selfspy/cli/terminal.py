"""selfspy terminal — terminal command analytics."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..analytics.terminal import (
    get_command_stats,
    get_project_stats,
    get_session_stats,
    get_workflow_stats,
)
from ..core import Settings
from ..storage import Store

app = typer.Typer(help="Terminal Activity Statistics")
console = Console()


def create_command_frequency_chart(
    commands: list[tuple[str, int]], title: str = "Command Frequency"
) -> Table:
    """Create a frequency chart for terminal commands."""
    if not commands:
        return Table()

    table = Table(title=title, show_header=False, box=None, padding=(0, 1))
    table.add_column("Command", style="cyan", width=20)
    table.add_column("Bar", style="blue")
    table.add_column("Count", justify="right", style="green")

    max_count = max(item[1] for item in commands) if commands else 1
    max_width = 30

    for command, count in commands[:15]:
        bar_length = int((count / max_count) * max_width) if max_count > 0 else 0
        bar = "█" * bar_length + "░" * (max_width - bar_length)
        percentage = (count / max_count) * 100 if max_count > 0 else 0

        display_cmd = command[:18] + ".." if len(command) > 20 else command

        table.add_row(
            f"{display_cmd:<20}", f"[blue]{bar}[/blue]", f"{count} ({percentage:.1f}%)"
        )

    return table


@app.command()
def commands(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze"),
    directory: str | None = typer.Option(None, "--dir", help="Filter by directory"),
    command_type: str | None = typer.Option(
        None, "--type", help="Filter by command type"
    ),
    data_dir: Path = typer.Option(None, "--data-dir", help="Data directory"),
    password: str | None = typer.Option(
        None, "--password", "-p", help="Password for encrypted data"
    ),
):
    """Show terminal command statistics."""
    try:
        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
        store = Store(settings, password)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with console.status("[bold green]Analyzing terminal commands..."):
                stats = loop.run_until_complete(
                    get_command_stats(store, days, directory, command_type)
                )

            _display_command_stats(stats, days, directory, command_type)
        finally:
            loop.close()

    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1) from e


@app.command()
def sessions(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze"),
    data_dir: Path = typer.Option(None, "--data-dir", help="Data directory"),
    password: str | None = typer.Option(
        None, "--password", "-p", help="Password for encrypted data"
    ),
):
    """Show terminal session statistics."""
    try:
        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
        store = Store(settings, password)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with console.status("[bold green]Analyzing terminal sessions..."):
                stats = loop.run_until_complete(get_session_stats(store, days))

            _display_session_stats(stats, days)
        finally:
            loop.close()

    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1) from e


@app.command()
def projects(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze"),
    data_dir: Path = typer.Option(None, "--data-dir", help="Data directory"),
    password: str | None = typer.Option(
        None, "--password", "-p", help="Password for encrypted data"
    ),
):
    """Show project-based terminal activity."""
    try:
        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
        store = Store(settings, password)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with console.status("[bold green]Analyzing project activity..."):
                stats = loop.run_until_complete(get_project_stats(store, days))

            _display_project_stats(stats, days)
        finally:
            loop.close()

    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1) from e


@app.command()
def workflow(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze"),
    directory: str | None = typer.Option(None, "--dir", help="Filter by directory"),
    data_dir: Path = typer.Option(None, "--data-dir", help="Data directory"),
    password: str | None = typer.Option(
        None, "--password", "-p", help="Password for encrypted data"
    ),
):
    """Show development workflow patterns."""
    try:
        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
        store = Store(settings, password)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with console.status("[bold green]Analyzing workflow patterns..."):
                stats = loop.run_until_complete(
                    get_workflow_stats(store, days, directory)
                )

            _display_workflow_stats(stats, days, directory)
        finally:
            loop.close()

    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1) from e


def _display_command_stats(
    stats: dict, days: int, directory: str | None, command_type: str | None
):
    """Display terminal command statistics."""
    filters = []
    if directory:
        filters.append(f"Directory: {directory}")
    if command_type:
        filters.append(f"Type: {command_type}")

    filter_text = f" ({', '.join(filters)})" if filters else ""

    header = Panel(
        f"[bold blue]💻 Terminal Command Analysis{filter_text}[/bold blue]\n"
        f"[dim]Analysis Period: {days} day{'s' if days != 1 else ''}[/dim]",
        border_style="blue",
    )
    console.print(header)
    console.print()

    overview_table = Table(title="📊 Overview", box=None)
    overview_table.add_column("Metric", style="cyan")
    overview_table.add_column("Value", style="green", justify="right")

    overview_table.add_row("🔢 Total Commands", f"{stats['total_commands']:,}")
    overview_table.add_row(
        "📈 Avg per Day", f"{stats['total_commands'] // max(days, 1):,}"
    )
    overview_table.add_row("🎯 Command Types", f"{len(stats['command_types'])}")
    overview_table.add_row(
        "📁 Active Directories", f"{len(stats['active_directories'])}"
    )

    console.print(overview_table)
    console.print()

    if stats["frequent_commands"]:
        cmd_chart = create_command_frequency_chart(
            stats["frequent_commands"], "🏆 Most Frequent Commands"
        )
        console.print(cmd_chart)
        console.print()

    if stats["command_types"]:
        type_table = Table(title="🔧 Command Types")
        type_table.add_column("Type", style="cyan")
        type_table.add_column("Count", justify="right", style="green")
        type_table.add_column("Percentage", justify="right", style="yellow")

        total = sum(count for _, count in stats["command_types"])
        for cmd_type, count in stats["command_types"]:
            percentage = (count / total) * 100 if total > 0 else 0
            type_table.add_row(cmd_type, f"{count:,}", f"{percentage:.1f}%")

        console.print(type_table)
        console.print()

    if stats["active_directories"]:
        dir_table = Table(title="📁 Most Active Directories")
        dir_table.add_column("Directory", style="cyan")
        dir_table.add_column("Commands", justify="right", style="green")

        for directory_name, count in stats["active_directories"]:
            display_dir = directory_name
            if len(display_dir) > 60:
                display_dir = "..." + display_dir[-57:]
            dir_table.add_row(display_dir, f"{count:,}")

        console.print(dir_table)


def _display_session_stats(stats: dict, days: int):
    """Display terminal session statistics."""
    header = Panel(
        f"[bold green]🖥️  Terminal Sessions Analysis[/bold green]\n"
        f"[dim]Analysis Period: {days} day{'s' if days != 1 else ''}[/dim]",
        border_style="green",
    )
    console.print(header)
    console.print()

    if stats["daily_activity"]:
        daily_table = Table(title="📅 Daily Activity")
        daily_table.add_column("Date", style="cyan")
        daily_table.add_column("Sessions", justify="right", style="blue")
        daily_table.add_column("Commands", justify="right", style="green")

        for date, sessions_count, commands_count in stats["daily_activity"]:
            daily_table.add_row(str(date), str(sessions_count), str(commands_count))

        console.print(daily_table)
        console.print()

    if stats["active_directories"]:
        dir_table = Table(title="📁 Most Active Project Directories")
        dir_table.add_column("Directory", style="cyan")
        dir_table.add_column("Sessions", justify="right", style="blue")
        dir_table.add_column("Commands", justify="right", style="green")

        for directory, sessions_count, commands_count in stats["active_directories"]:
            display_dir = directory
            if len(display_dir) > 50:
                display_dir = "..." + display_dir[-47:]
            dir_table.add_row(display_dir, str(sessions_count), str(commands_count))

        console.print(dir_table)


def _display_project_stats(stats: dict, days: int):
    """Display project-based statistics."""
    header = Panel(
        f"[bold magenta]🚀 Project Development Analysis[/bold magenta]\n"
        f"[dim]Analysis Period: {days} day{'s' if days != 1 else ''}[/dim]",
        border_style="magenta",
    )
    console.print(header)
    console.print()

    if stats["project_types"]:
        project_table = Table(title="🛠️ Project Types")
        project_table.add_column("Language/Type", style="cyan")
        project_table.add_column("Commands", justify="right", style="green")
        project_table.add_column("Directories", justify="right", style="blue")

        for project_type, commands_count, directories_count in stats["project_types"]:
            project_table.add_row(
                project_type, f"{commands_count:,}", str(directories_count)
            )

        console.print(project_table)
        console.print()

    if stats["git_branches"]:
        git_table = Table(title="🌳 Most Active Git Branches")
        git_table.add_column("Branch", style="cyan")
        git_table.add_column("Commands", justify="right", style="green")

        for branch, count in stats["git_branches"]:
            git_table.add_row(branch, f"{count:,}")

        console.print(git_table)


def _display_workflow_stats(stats: dict, days: int, directory: str | None):
    """Display workflow pattern statistics."""
    filter_text = f" in {directory}" if directory else ""

    header = Panel(
        f"[bold yellow]⚡ Development Workflow Patterns{filter_text}[/bold yellow]\n"
        f"[dim]Analysis Period: {days} day{'s' if days != 1 else ''}[/dim]",
        border_style="yellow",
    )
    console.print(header)
    console.print()

    if stats["command_patterns"]:
        pattern_table = Table(title="🔄 Common Command Sequences")
        pattern_table.add_column("Pattern", style="cyan")
        pattern_table.add_column("Frequency", justify="right", style="green")

        for pattern, count in stats["command_patterns"]:
            pattern_table.add_row(pattern, f"{count:,}")

        console.print(pattern_table)
        console.print()

    if stats["dangerous_commands"]:
        danger_table = Table(title="⚠️ Recent Dangerous Commands", show_header=True)
        danger_table.add_column("When", style="dim")
        danger_table.add_column("Command", style="red")
        danger_table.add_column("Directory", style="cyan")

        for cmd in stats["dangerous_commands"]:
            when = cmd.created_at.strftime("%m/%d %H:%M")
            command = cmd.command[:60] + "..." if len(cmd.command) > 60 else cmd.command
            directory_name = (
                cmd.working_directory.split("/")[-1]
                if cmd.working_directory
                else "unknown"
            )

            danger_table.add_row(when, command, directory_name)

        console.print(danger_table)
