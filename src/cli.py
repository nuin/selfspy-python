"""
Command Line Interface for Selfspy
"""

import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.traceback import install

from .config import DATA_DIR
from .activity_store import ActivityStore
from .monitor import ActivityMonitor
from .password_dialog import get_password

# Install rich traceback handler
install()
console = Console()

@click.group()
@click.version_option()
def cli():
    """Selfspy - Monitor and analyze your computer activity."""
    pass

@cli.command()
@click.option(
    '-d', '--data-dir',
    type=click.Path(),
    default=DATA_DIR,
    help='Data directory for storing the database'
)
@click.option(
    '-p', '--password',
    help='Encryption password for sensitive data'
)
@click.option(
    '--no-text',
    is_flag=True,
    help='Do not store text data (keystrokes)'
)
@click.option(
    '--debug',
    is_flag=True,
    help='Enable debug logging'
)
def start(
    data_dir: str,
    password: Optional[str],
    no_text: bool,
    debug: bool
) -> None:
    """Start monitoring computer activity."""
    try:
        # Ensure data directory exists
        data_dir = os.path.expanduser(data_dir)
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        
        if not no_text and not password:
            password = get_password()
            
        store = ActivityStore(
            os.path.join(data_dir, 'selfspy.sqlite'),
            password if not no_text else None
        )
        
        monitor = ActivityMonitor(store, debug=debug)
        
        console.print("[green]Starting Selfspy monitor...[/green]")
        monitor.start()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down gracefully...[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

def main():
    """Main entry point."""
    cli()

if __name__ == '__main__':
    main()