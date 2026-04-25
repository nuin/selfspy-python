"""selfspy migrate — run alembic migrations."""

import subprocess
from pathlib import Path

import typer
from rich.console import Console

from ..core import Settings

app = typer.Typer(help="Database migrations")
console = Console()


@app.callback(invoke_without_command=True)
def migrate(
    revision: str = typer.Option("head", "--revision", "-r", help="Target revision"),
    data_dir: Path = typer.Option(None, "--data-dir", "-d"),
):
    """Run database migrations to the given revision (default: head)."""
    settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)
    db_url = f"sqlite:///{settings.database_path}"

    alembic_ini = Path(__file__).parent.parent.parent.parent / "alembic.ini"
    if not alembic_ini.exists():
        console.print(f"[red]alembic.ini not found at {alembic_ini}[/red]")
        raise typer.Exit(1)

    cmd = [
        "alembic",
        "-c",
        str(alembic_ini),
        "-x",
        f"dburl={db_url}",
        "upgrade",
        revision,
    ]
    console.print(f"[cyan]Running: {' '.join(cmd)}[/cyan]")
    result = subprocess.run(cmd, check=False)
    raise typer.Exit(result.returncode)
