"""
Terminal-specific statistics and visualizations
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import typer
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from sqlalchemy import and_, desc, func, select

from .activity_store import ActivityStore
from .config import Settings
from .terminal_tracker import TerminalCommand, TerminalSession

app = typer.Typer(help="Terminal Activity Statistics")
console = Console()


def create_command_frequency_chart(
    commands: List[Tuple[str, int]], title: str = "Command Frequency"
) -> Table:
    """Create a frequency chart for terminal commands"""
    if not commands:
        return Table()

    table = Table(title=title, show_header=False, box=None, padding=(0, 1))
    table.add_column("Command", style="cyan", width=20)
    table.add_column("Bar", style="blue")
    table.add_column("Count", justify="right", style="green")

    max_count = max(item[1] for item in commands) if commands else 1
    max_width = 30

    for command, count in commands[:15]:  # Top 15
        bar_length = int((count / max_count) * max_width) if max_count > 0 else 0
        bar = "█" * bar_length + "░" * (max_width - bar_length)
        percentage = (count / max_count) * 100 if max_count > 0 else 0

        # Truncate long commands
        display_cmd = command[:18] + ".." if len(command) > 20 else command

        table.add_row(
            f"{display_cmd:<20}", f"[blue]{bar}[/blue]", f"{count} ({percentage:.1f}%)"
        )

    return table


@app.command()
def commands(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze"),
    directory: Optional[str] = typer.Option(None, "--dir", help="Filter by directory"),
    command_type: Optional[str] = typer.Option(
        None, "--type", help="Filter by command type"
    ),
    data_dir: Path = typer.Option(None, "--data-dir", help="Data directory"),
    password: Optional[str] = typer.Option(
        None, "--password", "-p", help="Password for encrypted data"
    ),
):
    """Show terminal command statistics"""
    try:
        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
        store = ActivityStore(settings, password)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with console.status("[bold green]Analyzing terminal commands..."):
                stats = loop.run_until_complete(
                    _get_command_stats(store, days, directory, command_type)
                )

            _display_command_stats(stats, days, directory, command_type)
        finally:
            loop.close()

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def sessions(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze"),
    data_dir: Path = typer.Option(None, "--data-dir", help="Data directory"),
    password: Optional[str] = typer.Option(
        None, "--password", "-p", help="Password for encrypted data"
    ),
):
    """Show terminal session statistics"""
    try:
        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
        store = ActivityStore(settings, password)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with console.status("[bold green]Analyzing terminal sessions..."):
                stats = loop.run_until_complete(_get_session_stats(store, days))

            _display_session_stats(stats, days)
        finally:
            loop.close()

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def projects(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze"),
    data_dir: Path = typer.Option(None, "--data-dir", help="Data directory"),
    password: Optional[str] = typer.Option(
        None, "--password", "-p", help="Password for encrypted data"
    ),
):
    """Show project-based terminal activity"""
    try:
        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
        store = ActivityStore(settings, password)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with console.status("[bold green]Analyzing project activity..."):
                stats = loop.run_until_complete(_get_project_stats(store, days))

            _display_project_stats(stats, days)
        finally:
            loop.close()

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def workflow(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze"),
    directory: Optional[str] = typer.Option(None, "--dir", help="Filter by directory"),
    data_dir: Path = typer.Option(None, "--data-dir", help="Data directory"),
    password: Optional[str] = typer.Option(
        None, "--password", "-p", help="Password for encrypted data"
    ),
):
    """Show development workflow patterns"""
    try:
        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
        store = ActivityStore(settings, password)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with console.status("[bold green]Analyzing workflow patterns..."):
                stats = loop.run_until_complete(
                    _get_workflow_stats(store, days, directory)
                )

            _display_workflow_stats(stats, days, directory)
        finally:
            loop.close()

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


async def _get_command_stats(
    store: ActivityStore,
    days: int,
    directory: Optional[str] = None,
    command_type: Optional[str] = None,
):
    """Get terminal command statistics"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    async with store.async_session() as session:
        # Base query
        query = select(TerminalCommand).where(TerminalCommand.created_at >= start_date)

        if directory:
            query = query.where(
                TerminalCommand.working_directory.like(f"%{directory}%")
            )

        if command_type:
            query = query.where(TerminalCommand.command_type == command_type)

        # Most frequent commands
        freq_query = select(
            TerminalCommand.command, func.count(TerminalCommand.id).label("count")
        ).where(TerminalCommand.created_at >= start_date)

        if directory:
            freq_query = freq_query.where(
                TerminalCommand.working_directory.like(f"%{directory}%")
            )
        if command_type:
            freq_query = freq_query.where(TerminalCommand.command_type == command_type)

        freq_query = (
            freq_query.group_by(TerminalCommand.command)
            .order_by(desc("count"))
            .limit(20)
        )

        # Command types
        type_query = select(
            TerminalCommand.command_type, func.count(TerminalCommand.id).label("count")
        ).where(TerminalCommand.created_at >= start_date)

        if directory:
            type_query = type_query.where(
                TerminalCommand.working_directory.like(f"%{directory}%")
            )
        if command_type:
            type_query = type_query.where(TerminalCommand.command_type == command_type)

        type_query = type_query.group_by(TerminalCommand.command_type).order_by(
            desc("count")
        )

        # Directory activity
        dir_query = select(
            TerminalCommand.working_directory,
            func.count(TerminalCommand.id).label("count"),
        ).where(TerminalCommand.created_at >= start_date)

        if directory:
            dir_query = dir_query.where(
                TerminalCommand.working_directory.like(f"%{directory}%")
            )
        if command_type:
            dir_query = dir_query.where(TerminalCommand.command_type == command_type)

        dir_query = (
            dir_query.group_by(TerminalCommand.working_directory)
            .order_by(desc("count"))
            .limit(10)
        )

        # Recent commands
        recent_query = select(TerminalCommand).where(
            TerminalCommand.created_at >= start_date
        )

        if directory:
            recent_query = recent_query.where(
                TerminalCommand.working_directory.like(f"%{directory}%")
            )
        if command_type:
            recent_query = recent_query.where(
                TerminalCommand.command_type == command_type
            )

        recent_query = recent_query.order_by(desc(TerminalCommand.created_at)).limit(20)

        # Execute queries
        commands = await session.execute(query)
        frequent = await session.execute(freq_query)
        types = await session.execute(type_query)
        directories = await session.execute(dir_query)
        recent = await session.execute(recent_query)

        return {
            "total_commands": len(commands.all()),
            "frequent_commands": [(row.command, row.count) for row in frequent.all()],
            "command_types": [(row.command_type, row.count) for row in types.all()],
            "active_directories": [
                (row.working_directory, row.count) for row in directories.all()
            ],
            "recent_commands": recent.all(),
        }


async def _get_session_stats(store: ActivityStore, days: int):
    """Get terminal session statistics"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    async with store.async_session() as session:
        # Session count per day
        daily_query = (
            select(
                func.date(TerminalSession.created_at).label("date"),
                func.count(TerminalSession.id).label("sessions"),
                func.count(TerminalCommand.id).label("commands"),
            )
            .outerjoin(TerminalCommand)
            .where(TerminalSession.created_at >= start_date)
            .group_by("date")
            .order_by("date")
        )

        # Most active directories
        dir_query = (
            select(
                TerminalSession.working_directory,
                func.count(TerminalSession.id).label("session_count"),
                func.count(TerminalCommand.id).label("command_count"),
            )
            .outerjoin(TerminalCommand)
            .where(TerminalSession.created_at >= start_date)
            .group_by(TerminalSession.working_directory)
            .order_by(desc("command_count"))
            .limit(10)
        )

        # Shell types
        shell_query = (
            select(
                TerminalSession.shell_type,
                func.count(TerminalSession.id).label("count"),
            )
            .where(TerminalSession.created_at >= start_date)
            .group_by(TerminalSession.shell_type)
            .order_by(desc("count"))
        )

        daily = await session.execute(daily_query)
        directories = await session.execute(dir_query)
        shells = await session.execute(shell_query)

        return {
            "daily_activity": [
                (row.date, row.sessions, row.commands) for row in daily.all()
            ],
            "active_directories": [
                (row.working_directory, row.session_count, row.command_count)
                for row in directories.all()
            ],
            "shell_types": [(row.shell_type, row.count) for row in shells.all()],
        }


async def _get_project_stats(store: ActivityStore, days: int):
    """Get project-based statistics"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    async with store.async_session() as session:
        # Project types
        project_query = (
            select(
                TerminalCommand.project_type,
                func.count(TerminalCommand.id).label("command_count"),
                func.count(func.distinct(TerminalCommand.working_directory)).label(
                    "directory_count"
                ),
            )
            .where(
                and_(
                    TerminalCommand.created_at >= start_date,
                    TerminalCommand.project_type.isnot(None),
                )
            )
            .group_by(TerminalCommand.project_type)
            .order_by(desc("command_count"))
        )

        # Git branches
        git_query = (
            select(
                TerminalCommand.git_branch,
                func.count(TerminalCommand.id).label("count"),
            )
            .where(
                and_(
                    TerminalCommand.created_at >= start_date,
                    TerminalCommand.git_branch.isnot(None),
                )
            )
            .group_by(TerminalCommand.git_branch)
            .order_by(desc("count"))
            .limit(10)
        )

        projects = await session.execute(project_query)
        branches = await session.execute(git_query)

        return {
            "project_types": [
                (row.project_type, row.command_count, row.directory_count)
                for row in projects.all()
            ],
            "git_branches": [(row.git_branch, row.count) for row in branches.all()],
        }


async def _get_workflow_stats(
    store: ActivityStore, days: int, directory: Optional[str] = None
):
    """Get workflow pattern statistics"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    async with store.async_session() as session:
        # Command sequences (simplified)
        query = select(TerminalCommand).where(TerminalCommand.created_at >= start_date)

        if directory:
            query = query.where(
                TerminalCommand.working_directory.like(f"%{directory}%")
            )

        query = query.order_by(TerminalCommand.created_at)

        commands = await session.execute(query)
        command_list = commands.all()

        # Analyze patterns
        patterns = defaultdict(int)
        for i in range(len(command_list) - 1):
            current = command_list[i].command_type
            next_cmd = command_list[i + 1].command_type
            patterns[f"{current} → {next_cmd}"] += 1

        # Most dangerous commands
        dangerous_query = select(TerminalCommand).where(
            and_(
                TerminalCommand.created_at >= start_date,
                TerminalCommand.is_dangerous == True,
            )
        )

        if directory:
            dangerous_query = dangerous_query.where(
                TerminalCommand.working_directory.like(f"%{directory}%")
            )

        dangerous_query = dangerous_query.order_by(
            desc(TerminalCommand.created_at)
        ).limit(10)

        dangerous = await session.execute(dangerous_query)

        return {
            "command_patterns": sorted(
                patterns.items(), key=lambda x: x[1], reverse=True
            )[:15],
            "dangerous_commands": dangerous.all(),
        }


def _display_command_stats(
    stats: Dict, days: int, directory: Optional[str], command_type: Optional[str]
):
    """Display terminal command statistics"""

    # Header
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

    # Overview stats
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

    # Most frequent commands
    if stats["frequent_commands"]:
        cmd_chart = create_command_frequency_chart(
            stats["frequent_commands"], "🏆 Most Frequent Commands"
        )
        console.print(cmd_chart)
        console.print()

    # Command types
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

    # Active directories
    if stats["active_directories"]:
        dir_table = Table(title="📁 Most Active Directories")
        dir_table.add_column("Directory", style="cyan")
        dir_table.add_column("Commands", justify="right", style="green")

        for directory, count in stats["active_directories"]:
            # Shorten long paths
            display_dir = directory
            if len(display_dir) > 60:
                display_dir = "..." + display_dir[-57:]
            dir_table.add_row(display_dir, f"{count:,}")

        console.print(dir_table)


def _display_session_stats(stats: Dict, days: int):
    """Display terminal session statistics"""

    header = Panel(
        f"[bold green]🖥️  Terminal Sessions Analysis[/bold green]\n"
        f"[dim]Analysis Period: {days} day{'s' if days != 1 else ''}[/dim]",
        border_style="green",
    )
    console.print(header)
    console.print()

    # Daily activity
    if stats["daily_activity"]:
        daily_table = Table(title="📅 Daily Activity")
        daily_table.add_column("Date", style="cyan")
        daily_table.add_column("Sessions", justify="right", style="blue")
        daily_table.add_column("Commands", justify="right", style="green")

        for date, sessions, commands in stats["daily_activity"]:
            daily_table.add_row(str(date), str(sessions), str(commands))

        console.print(daily_table)
        console.print()

    # Active directories
    if stats["active_directories"]:
        dir_table = Table(title="📁 Most Active Project Directories")
        dir_table.add_column("Directory", style="cyan")
        dir_table.add_column("Sessions", justify="right", style="blue")
        dir_table.add_column("Commands", justify="right", style="green")

        for directory, sessions, commands in stats["active_directories"]:
            display_dir = directory
            if len(display_dir) > 50:
                display_dir = "..." + display_dir[-47:]
            dir_table.add_row(display_dir, str(sessions), str(commands))

        console.print(dir_table)


def _display_project_stats(stats: Dict, days: int):
    """Display project-based statistics"""

    header = Panel(
        f"[bold magenta]🚀 Project Development Analysis[/bold magenta]\n"
        f"[dim]Analysis Period: {days} day{'s' if days != 1 else ''}[/dim]",
        border_style="magenta",
    )
    console.print(header)
    console.print()

    # Project types
    if stats["project_types"]:
        project_table = Table(title="🛠️ Project Types")
        project_table.add_column("Language/Type", style="cyan")
        project_table.add_column("Commands", justify="right", style="green")
        project_table.add_column("Directories", justify="right", style="blue")

        for project_type, commands, directories in stats["project_types"]:
            project_table.add_row(project_type, f"{commands:,}", str(directories))

        console.print(project_table)
        console.print()

    # Git branches
    if stats["git_branches"]:
        git_table = Table(title="🌳 Most Active Git Branches")
        git_table.add_column("Branch", style="cyan")
        git_table.add_column("Commands", justify="right", style="green")

        for branch, count in stats["git_branches"]:
            git_table.add_row(branch, f"{count:,}")

        console.print(git_table)


def _display_workflow_stats(stats: Dict, days: int, directory: Optional[str]):
    """Display workflow pattern statistics"""

    filter_text = f" in {directory}" if directory else ""

    header = Panel(
        f"[bold yellow]⚡ Development Workflow Patterns{filter_text}[/bold yellow]\n"
        f"[dim]Analysis Period: {days} day{'s' if days != 1 else ''}[/dim]",
        border_style="yellow",
    )
    console.print(header)
    console.print()

    # Command patterns
    if stats["command_patterns"]:
        pattern_table = Table(title="🔄 Common Command Sequences")
        pattern_table.add_column("Pattern", style="cyan")
        pattern_table.add_column("Frequency", justify="right", style="green")

        for pattern, count in stats["command_patterns"]:
            pattern_table.add_row(pattern, f"{count:,}")

        console.print(pattern_table)
        console.print()

    # Dangerous commands
    if stats["dangerous_commands"]:
        danger_table = Table(title="⚠️ Recent Dangerous Commands", show_header=True)
        danger_table.add_column("When", style="dim")
        danger_table.add_column("Command", style="red")
        danger_table.add_column("Directory", style="cyan")

        for cmd in stats["dangerous_commands"]:
            when = cmd.created_at.strftime("%m/%d %H:%M")
            command = cmd.command[:60] + "..." if len(cmd.command) > 60 else cmd.command
            directory = (
                cmd.working_directory.split("/")[-1]
                if cmd.working_directory
                else "unknown"
            )

            danger_table.add_row(when, command, directory)

        console.print(danger_table)


if __name__ == "__main__":
    app()
