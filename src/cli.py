# src/cli.py
"""
Modern CLI interface for Selfspy using Typer
"""
import asyncio
import signal
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.traceback import install

from .config import Settings
from .activity_store import ActivityStore
from .monitor import ActivityMonitor
from .password_dialog import get_password

# Initialize Typer app and Rich console
app = typer.Typer(help="Selfspy - Monitor and analyze your computer activity")
console = Console()

# Install Rich traceback handler
install(show_locals=True)

@app.command()
def start(
    data_dir: Path = typer.Option(
        None,
        "--data-dir", "-d",
        help="Data directory for storing the database"
    ),
    password: Optional[str] = typer.Option(
        None,
        "--password", "-p",
        help="Encryption password for sensitive data"
    ),
    no_text: bool = typer.Option(
        False,
        "--no-text",
        help="Do not store text data (keystrokes)"
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug logging"
    ),
):
    """Start monitoring computer activity."""
    try:
        # Initialize settings
        settings = Settings(
            data_dir=data_dir if data_dir else Settings().data_dir,
            encryption_enabled=not no_text,
            debug=debug
        )
        
        # Get password if needed
        if settings.encryption_enabled and not password:
            password = get_password()
            
        # Set up async monitor
        store = ActivityStore(settings, password)
        monitor = ActivityMonitor(settings, store, debug)
        
        # Handle shutdown signals
        def signal_handler():
            monitor.stop()
            
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal_handler)
        
        # Start monitoring
        console.print("[green]Starting Selfspy monitor...[/green]")
        asyncio.run(monitor.start())
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down gracefully...[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command()
def stats(
    data_dir: Path = typer.Option(
        None,
        "--data-dir", "-d",
        help="Data directory containing the database"
    ),
    start_date: str = typer.Option(
        None,
        "--start", "-s",
        help="Start date (YYYY-MM-DD)"
    ),
    end_date: str = typer.Option(
        None,
        "--end", "-e",
        help="End date (YYYY-MM-DD)"
    ),
    format: str = typer.Option(
        "text",
        "--format", "-f",
        help="Output format (text/json/csv)"
    )
):
    """Display activity statistics."""
    try:
        from .stats import generate_stats
        
        settings = Settings(
            data_dir=data_dir if data_dir else Settings().data_dir
        )
        
        stats = generate_stats(
            settings,
            start_date,
            end_date,
            format
        )
        
        if format == "text":
            console.print(stats)
        else:
            typer.echo(stats)
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command()
def check_permissions():
    """Check required macOS permissions."""
    try:
        import AppKit
        
        # Check accessibility permissions
        options = {AppKit.kAXTrustedCheckOptionPrompt: True}
        has_accessibility = AppKit.AXIsProcessTrustedWithOptions(options)
        
        # Check screen recording permissions (if enabled)
        settings = Settings()
        if settings.enable_screen_recording:
            has_screen = check_screen_recording_permission()
        else:
            has_screen = True
        
        if has_accessibility and has_screen:
            console.print("[green]All required permissions granted![/green]")
        else:
            console.print(
                "[yellow]Missing required permissions. "
                "Please check System Preferences > Security & Privacy > Privacy[/yellow]"
            )
            
        console.print("\nPermission Status:")
        console.print(f"Accessibility: {'✓' if has_accessibility else '✗'}")
        if settings.enable_screen_recording:
            console.print(f"Screen Recording: {'✓' if has_screen else '✗'}")
            
    except ImportError:
        console.print("[red]This command only works on macOS[/red]")
        raise typer.Exit(1)

def check_screen_recording_permission() -> bool:
    """Check screen recording permission status"""
    try:
        import AVFoundation
        
        session = AVFoundation.AVCaptureSession.alloc().init()
        screen_input = AVFoundation.AVCaptureScreenInput.alloc().init()
        
        if session.canAddInput_(screen_input):
            session.addInput_(screen_input)
            return True
        return False
        
    except Exception:
        return False



def main():
    """Main entry point."""
    app()

if __name__ == "__main__":
    main()