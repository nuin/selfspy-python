"""Lifecycle management: signal handling, asyncio entry, graceful shutdown."""

from __future__ import annotations

import asyncio
import signal
from typing import TYPE_CHECKING

import structlog
from rich.console import Console

if TYPE_CHECKING:
    from .monitor import Monitor

logger = structlog.get_logger()


def run(monitor: Monitor, *, use_tui: bool = True) -> None:
    """Run a monitor to completion with signal handling.

    Owns the asyncio event loop entry point. Installs SIGINT/SIGTERM
    handlers that schedule monitor.stop() on the loop.
    """
    console = Console()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def signal_handler(signum, frame):
        console.print("\n[yellow]Received shutdown signal, cleaning up...[/yellow]")
        if monitor.running:
            loop.create_task(monitor.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, signal_handler)

    try:
        loop.run_until_complete(monitor.start(use_tui=use_tui))
    except KeyboardInterrupt:
        console.print(
            "\n[yellow]Keyboard interrupt received, shutting down gracefully...[/yellow]"
        )
        loop.run_until_complete(monitor.stop())
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
