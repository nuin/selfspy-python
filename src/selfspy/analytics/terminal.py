"""Pure analytics for terminal command/session/project/workflow stats."""

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import and_, desc, func, select

from ..storage import Store
from ..tracking.terminal import TerminalCommand, TerminalSession


async def get_command_stats(
    store: Store,
    days: int,
    directory: str | None = None,
    command_type: str | None = None,
) -> dict:
    """Get terminal command statistics as plain data."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    async with store.async_session() as session:
        query = select(TerminalCommand).where(TerminalCommand.created_at >= start_date)

        if directory:
            query = query.where(
                TerminalCommand.working_directory.like(f"%{directory}%")
            )

        if command_type:
            query = query.where(TerminalCommand.command_type == command_type)

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


async def get_session_stats(store: Store, days: int) -> dict:
    """Get terminal session statistics as plain data."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    async with store.async_session() as session:
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


async def get_project_stats(store: Store, days: int) -> dict:
    """Get project-based statistics as plain data."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    async with store.async_session() as session:
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


async def get_workflow_stats(
    store: Store, days: int, directory: str | None = None
) -> dict:
    """Get workflow pattern statistics as plain data."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    async with store.async_session() as session:
        query = select(TerminalCommand).where(TerminalCommand.created_at >= start_date)

        if directory:
            query = query.where(
                TerminalCommand.working_directory.like(f"%{directory}%")
            )

        query = query.order_by(TerminalCommand.created_at)

        commands = await session.execute(query)
        command_list = commands.all()

        patterns: dict[str, int] = defaultdict(int)
        for i in range(len(command_list) - 1):
            current = command_list[i].command_type
            next_cmd = command_list[i + 1].command_type
            patterns[f"{current} → {next_cmd}"] += 1

        dangerous_query = select(TerminalCommand).where(
            and_(
                TerminalCommand.created_at >= start_date,
                TerminalCommand.is_dangerous,
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
