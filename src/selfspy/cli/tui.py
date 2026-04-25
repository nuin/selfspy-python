"""selfspy tui — start tracking with Textual TUI."""

from pathlib import Path

import typer
from rich.console import Console

from ..core import Monitor, Settings, run_monitor
from ..storage import Store, get_password
from ..tracking import check_and_request_permissions

app = typer.Typer(help="Interactive Textual TUI")
console = Console()


@app.callback(invoke_without_command=True)
def tui(
    data_dir: Path = typer.Option(None, "--data-dir", "-d", help="Data directory"),
    no_text: bool = typer.Option(False, "--no-text", help="Don't store text"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
    force: bool = typer.Option(False, "--force", help="Skip permission checks"),
):
    """Start monitoring with Textual TUI."""
    if not force and not check_and_request_permissions(console):
        raise typer.Exit(1)

    settings = Settings(
        data_dir=data_dir if data_dir else Settings().data_dir,
        encryption_enabled=not no_text,
        debug=debug,
    )

    password = get_password() if settings.encryption_enabled else None
    store = Store(settings, password)
    monitor = Monitor(settings, store, debug)

    run_monitor(monitor, use_tui=True)
