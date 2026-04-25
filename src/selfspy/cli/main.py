"""selfspy — root CLI entry point."""

import typer
from rich.traceback import install

from . import daemon, migrate, permissions, stats, terminal, tui, viz

install(show_locals=True)

app = typer.Typer(
    help="Selfspy — monitor and analyze your computer activity",
    no_args_is_help=True,
)

app.add_typer(daemon.app, name="daemon", help="Start headless tracking")
app.add_typer(tui.app, name="tui", help="Start interactive TUI")
app.add_typer(stats.app, name="stats", help="Activity statistics")
app.add_typer(viz.app, name="viz", help="Enhanced visualizations")
app.add_typer(terminal.app, name="terminal", help="Terminal command analytics")
app.add_typer(permissions.app, name="check-permissions", help="Check macOS permissions")
app.add_typer(migrate.app, name="migrate", help="Database migrations")


if __name__ == "__main__":
    app()
