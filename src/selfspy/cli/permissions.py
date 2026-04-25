"""selfspy check-permissions — verify macOS permissions."""

import typer
from rich.console import Console

from ..tracking.permissions import check_macos_permissions

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def check_permissions():
    """Check required macOS permissions."""
    has_perms, msg = check_macos_permissions()
    if has_perms:
        console.print(f"[green]✓ {msg}[/green]")
    else:
        console.print(f"[yellow]✗ {msg}[/yellow]")
        raise typer.Exit(1)
