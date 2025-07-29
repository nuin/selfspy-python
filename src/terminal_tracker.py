"""
Terminal session tracking for Selfspy
Tracks commands executed in terminal sessions with folder context
"""

import asyncio
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    select,
)
from sqlalchemy.orm import relationship

from .activity_store import ActivityStore
from .models import Base, TimestampMixin

logger = structlog.get_logger()


class TerminalSession(TimestampMixin, Base):
    """Terminal session information"""

    __tablename__ = "terminal_session"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), index=True)  # Hash of terminal PID + start time
    working_directory = Column(String(500), index=True)
    shell_type = Column(String(50))  # bash, zsh, fish, etc.
    terminal_app = Column(String(100))  # iTerm2, Terminal, etc.
    window_title = Column(String(200))

    # Relationships
    commands = relationship(
        "TerminalCommand", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TerminalSession {self.session_id} in {self.working_directory}>"


class TerminalCommand(TimestampMixin, Base):
    """Individual terminal command execution"""

    __tablename__ = "terminal_command"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("terminal_session.id"), index=True)

    command = Column(Text)  # The actual command
    command_hash = Column(String(64), index=True)  # Hash for deduplication
    working_directory = Column(String(500), index=True)

    # Execution results
    exit_code = Column(Integer)  # 0 = success, non-zero = error
    execution_time_ms = Column(Integer)  # How long it took to run

    # Command categorization
    command_type = Column(String(50), index=True)  # git, npm, python, etc.
    is_dangerous = Column(Boolean, default=False)  # rm, sudo, etc.

    # Context
    git_branch = Column(String(100))  # Current git branch if in git repo
    project_type = Column(String(50))  # python, node, rust, etc. based on files

    # Relationships
    session = relationship("TerminalSession", back_populates="commands")

    def __repr__(self) -> str:
        status = "✓" if self.exit_code == 0 else "✗"
        return f"<TerminalCommand {status} {self.command[:50]}...>"


class TerminalTracker:
    """Track terminal sessions and command execution"""

    def __init__(self, store: ActivityStore):
        self.store = store
        self.current_session: Optional[Dict[str, Any]] = None
        self.shell_history_files = {
            "bash": [".bash_history"],
            "zsh": [".zsh_history", ".zhistory"],
            "fish": [".config/fish/fish_history"],
        }
        self.last_command_count = {}

    async def start_tracking(self):
        """Start tracking terminal sessions"""
        logger.info("Starting terminal session tracking")

        # Create database tables if they don't exist
        async with self.store.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Start monitoring loop
        while True:
            try:
                await self._check_for_new_commands()
                await asyncio.sleep(2)  # Check every 2 seconds
            except Exception as e:
                logger.error("Terminal tracking error", error=str(e))
                await asyncio.sleep(5)

    def _get_current_session_info(self) -> Dict[str, Any]:
        """Get information about the current terminal session"""
        try:
            # Get current working directory
            cwd = os.getcwd()

            # Detect shell type
            shell = os.environ.get("SHELL", "/bin/bash").split("/")[-1]

            # Get terminal app (macOS specific)
            terminal_app = os.environ.get("TERM_PROGRAM", "unknown")

            # Generate session ID based on terminal PID and start time
            pid = os.getppid()  # Parent process (terminal)
            session_id = hashlib.md5(f"{pid}_{cwd}".encode()).hexdigest()

            # Get git branch if in git repo
            git_branch = self._get_git_branch(cwd)

            # Detect project type
            project_type = self._detect_project_type(cwd)

            return {
                "session_id": session_id,
                "working_directory": cwd,
                "shell_type": shell,
                "terminal_app": terminal_app,
                "git_branch": git_branch,
                "project_type": project_type,
                "window_title": os.environ.get("PWD", cwd).split("/")[-1],
            }
        except Exception as e:
            logger.error("Failed to get session info", error=str(e))
            return {}

    def _get_git_branch(self, directory: str) -> Optional[str]:
        """Get current git branch for directory"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=2,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    def _detect_project_type(self, directory: str) -> Optional[str]:
        """Detect project type based on files in directory"""
        path = Path(directory)

        # Check for various project indicators
        if (path / "package.json").exists():
            return "node"
        elif (path / "pyproject.toml").exists() or (path / "requirements.txt").exists():
            return "python"
        elif (path / "Cargo.toml").exists():
            return "rust"
        elif (path / "go.mod").exists():
            return "go"
        elif (path / "pom.xml").exists():
            return "java"
        elif (path / "Makefile").exists():
            return "c/cpp"
        elif (path / ".git").exists():
            return "git"

        return None

    def _categorize_command(self, command: str) -> Dict[str, Any]:
        """Categorize and analyze a command"""
        command = command.strip()

        # Extract first word (the actual command)
        first_word = command.split()[0] if command.split() else ""

        # Command type categorization
        command_types = {
            "git": ["git"],
            "npm": ["npm", "yarn", "pnpm"],
            "python": [
                "python",
                "python3",
                "pip",
                "pip3",
                "pytest",
                "black",
                "isort",
                "mypy",
            ],
            "uv": ["uv"],
            "build": ["make", "cmake", "cargo", "mvn", "gradle"],
            "editor": ["vim", "nvim", "nano", "emacs", "code"],
            "file": [
                "ls",
                "cd",
                "mkdir",
                "rm",
                "cp",
                "mv",
                "find",
                "grep",
                "cat",
                "less",
                "head",
                "tail",
            ],
            "system": ["sudo", "chmod", "chown", "ps", "kill", "top", "htop"],
            "network": ["curl", "wget", "ssh", "scp", "ping"],
        }

        command_type = "other"
        for category, commands in command_types.items():
            if first_word in commands:
                command_type = category
                break

        # Check for dangerous commands
        dangerous_commands = ["rm", "sudo", "chmod", "chown", "kill", "dd", "fdisk"]
        is_dangerous = first_word in dangerous_commands or "rm -rf" in command

        return {
            "command_type": command_type,
            "is_dangerous": is_dangerous,
            "command_hash": hashlib.md5(command.encode()).hexdigest(),
        }

    async def _check_for_new_commands(self):
        """Check shell history files for new commands"""
        session_info = self._get_current_session_info()
        if not session_info:
            return

        shell_type = session_info.get("shell_type", "bash")
        history_files = self.shell_history_files.get(shell_type, [".bash_history"])

        home = Path.home()

        for history_file in history_files:
            history_path = home / history_file
            if not history_path.exists():
                continue

            try:
                await self._process_history_file(history_path, session_info)
            except Exception as e:
                logger.error(f"Error processing {history_path}", error=str(e))

    async def _process_history_file(
        self, history_path: Path, session_info: Dict[str, Any]
    ):
        """Process a shell history file for new commands"""
        try:
            with open(history_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # Track how many lines we've processed for this file
            file_key = str(history_path)
            last_count = self.last_command_count.get(file_key, 0)

            if len(lines) <= last_count:
                return  # No new commands

            # Process new commands
            new_lines = lines[last_count:]

            for line in new_lines:
                await self._process_command_line(line.strip(), session_info)

            # Update our tracking
            self.last_command_count[file_key] = len(lines)

        except Exception as e:
            logger.error(f"Error reading history file {history_path}", error=str(e))

    async def _process_command_line(self, line: str, session_info: Dict[str, Any]):
        """Process a single command line from history"""
        if not line or line.startswith("#"):
            return

        # Parse different history formats
        command = self._parse_history_line(line, session_info["shell_type"])
        if not command:
            return

        # Skip very common/uninteresting commands
        skip_commands = ["ls", "cd", "pwd", "clear", "exit", "history"]
        first_word = command.split()[0] if command.split() else ""
        if first_word in skip_commands:
            return

        # Categorize the command
        command_info = self._categorize_command(command)

        # Store the command
        await self._store_command(command, command_info, session_info)

    def _parse_history_line(self, line: str, shell_type: str) -> Optional[str]:
        """Parse a history line based on shell type"""
        if shell_type == "zsh":
            # Zsh format: ": 1640995200:0;command"
            match = re.match(r"^:\s*\d+:\d+;(.+)$", line)
            if match:
                return match.group(1)

        # Default: assume the line is the command
        return line.strip()

    async def _store_command(
        self, command: str, command_info: Dict[str, Any], session_info: Dict[str, Any]
    ):
        """Store a command in the database"""
        async with self.store.async_session() as session:
            async with session.begin():
                # Get or create terminal session
                terminal_session = await session.get(
                    TerminalSession, session_info["session_id"]
                )
                if not terminal_session:
                    terminal_session = TerminalSession(
                        session_id=session_info["session_id"],
                        working_directory=session_info["working_directory"],
                        shell_type=session_info.get("shell_type"),
                        terminal_app=session_info.get("terminal_app"),
                        window_title=session_info.get("window_title"),
                    )
                    session.add(terminal_session)
                    await session.flush()

                # Check if command already exists (deduplication)
                existing_command = await session.execute(
                    select(TerminalCommand).where(
                        TerminalCommand.command_hash == command_info["command_hash"],
                        TerminalCommand.session_id == terminal_session.id,
                    )
                )
                if existing_command.first():
                    return  # Command already tracked

                # Create new command record
                terminal_command = TerminalCommand(
                    session_id=terminal_session.id,
                    command=command,
                    command_hash=command_info["command_hash"],
                    working_directory=session_info["working_directory"],
                    command_type=command_info["command_type"],
                    is_dangerous=command_info["is_dangerous"],
                    git_branch=session_info.get("git_branch"),
                    project_type=session_info.get("project_type"),
                    exit_code=0,  # We don't have this info from history
                )

                session.add(terminal_command)

                logger.debug(
                    "Stored terminal command",
                    command=command[:50],
                    type=command_info["command_type"],
                    directory=session_info["working_directory"],
                )


async def start_terminal_tracking(store: ActivityStore):
    """Start terminal tracking in background"""
    tracker = TerminalTracker(store)
    await tracker.start_tracking()


if __name__ == "__main__":
    # Test the terminal tracker
    from .config import Settings

    async def test_tracker():
        settings = Settings()
        store = ActivityStore(settings)
        await start_terminal_tracking(store)

    asyncio.run(test_tracker())
