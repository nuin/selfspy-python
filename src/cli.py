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

from .activity_monitor import ActivityMonitor
from .activity_store import ActivityStore
from .config import Settings
from .password_dialog import get_password

# Initialize Typer app and Rich console
app = typer.Typer(help="Selfspy - Monitor and analyze your computer activity")
console = Console()

# Install Rich traceback handler
install(show_locals=True)

@app.command()
def start(
    data_dir: Path = typer.Option(None, "--data-dir", "-d", help="Data directory"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password"),
    no_text: bool = typer.Option(False, "--no-text", help="Don't store text"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
):
    """Start monitoring computer activity."""
    try:
        settings = Settings(
            data_dir=data_dir if data_dir else Settings().data_dir,
            encryption_enabled=not no_text,
            debug=debug
        )
        
        if settings.encryption_enabled and not password:
            password = get_password()
            
        store = ActivityStore(settings, password)
        monitor = ActivityMonitor(settings, store, debug)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        def signal_handler(signum, frame):
            if monitor.running:
                loop.create_task(monitor.stop())
                loop.stop()
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal_handler)
        
        console.print("[green]Starting Selfspy monitor...[/green]")
        loop.run_until_complete(monitor.start())
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down gracefully...[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
    finally:
        if 'loop' in locals():
            loop.close()

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
        # Import required frameworks
        import objc
        from ApplicationServices import AXIsProcessTrusted
        
        # Direct check for accessibility permissions
        has_accessibility = AXIsProcessTrusted()
        
        # Check screen recording permissions only if explicitly enabled
        settings = Settings()
        has_screen = True  # Default to True if screen recording is not enabled
        if settings.enable_screen_recording:
            has_screen = check_screen_recording_permission()
        
        if has_accessibility and has_screen:
            console.print("[green]All required permissions granted![/green]")
        else:
            # Prepare specific permission messages
            missing_permissions = []
            if not has_accessibility:
                missing_permissions.append("Accessibility")
            if settings.enable_screen_recording and not has_screen:
                missing_permissions.append("Screen Recording")
            
            console.print(
                f"[yellow]Missing permissions: {', '.join(missing_permissions)}[/yellow]\n"
                "Please check System Settings > Privacy & Security > Privacy"
            )
            
            # Try to open System Settings
            try:
                import Foundation
                url_str = Foundation.NSString.stringWithString_("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")
                url = Foundation.NSURL.URLWithString_(url_str)
                Foundation.NSWorkspace.sharedWorkspace().openURL_(url)
            except Exception as e:
                console.print("[red]Could not open System Settings automatically[/red]")
            
        # Print detailed status
        console.print("\nPermission Status:")
        console.print(f"Accessibility: {'✓' if has_accessibility else '✗'}")
        if settings.enable_screen_recording:
            console.print(f"Screen Recording: {'✓' if has_screen else '✗'}")
            
    except ImportError as e:
        console.print(f"[red]Error importing macOS frameworks. Make sure you have PyObjC installed: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error checking permissions: {e}[/red]")
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