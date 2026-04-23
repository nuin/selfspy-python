# src/cli.py
"""
Modern CLI interface for Selfspy using Typer
"""

import asyncio
import signal
from pathlib import Path

import typer
from rich.console import Console
from rich.traceback import install

from .activity_monitor import ActivityMonitor
from .config import Settings
from .enhanced_stats import app as enhanced_stats_app
from .permissions import check_and_request_permissions
from .stats import app as stats_app
from .storage import Store, get_password
from .terminal_stats import app as terminal_stats_app

# Initialize Typer app and Rich console
app = typer.Typer(help="Selfspy - Monitor and analyze your computer activity")
console = Console()

# Install Rich traceback handler
install(show_locals=True)

app.add_typer(stats_app, name="stats", help="View activity statistics")
app.add_typer(
    enhanced_stats_app, name="viz", help="Enhanced visualizations and analytics"
)
app.add_typer(terminal_stats_app, name="terminal", help="Terminal command analytics")


@app.command()
def start(
    data_dir: Path = typer.Option(None, "--data-dir", "-d", help="Data directory"),
    no_text: bool = typer.Option(False, "--no-text", help="Don't store text"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
    force: bool = typer.Option(
        False, "--force", help="Skip permission checks (may fail)"
    ),
):
    """Start monitoring computer activity."""
    try:
        # Check permissions first (unless forced)
        if not force and not check_and_request_permissions(console):
            console.print("[yellow]Exiting - permissions required[/yellow]")
            raise typer.Exit(1)

        settings = Settings(
            data_dir=data_dir if data_dir else Settings().data_dir,
            encryption_enabled=not no_text,
            debug=debug,
        )

        # Always use secure password dialog (never accept password via CLI args)
        password = None
        if settings.encryption_enabled:
            password = get_password()

        store = Store(settings, password)
        monitor = ActivityMonitor(settings, store, debug)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Graceful shutdown handler
        def signal_handler(signum, frame):
            console.print("\n[yellow]Received shutdown signal, cleaning up...[/yellow]")
            if monitor.running:
                # Schedule stop and wait for it to complete
                loop.create_task(monitor.stop())

        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal_handler)

        console.print("[green]Starting Selfspy monitor...[/green]")
        try:
            loop.run_until_complete(monitor.start())
        except KeyboardInterrupt:
            console.print(
                "\n[yellow]Keyboard interrupt received, shutting down gracefully...[/yellow]"
            )
            loop.run_until_complete(monitor.stop())

    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down gracefully...[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1)
    finally:
        if "loop" in locals():
            # Give tasks time to complete before closing loop
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()


@app.command()
def stats(
    data_dir: Path = typer.Option(
        None, "--data-dir", "-d", help="Data directory containing the database"
    ),
    start_date: str = typer.Option(
        None, "--start", "-s", help="Start date (YYYY-MM-DD)"
    ),
    end_date: str = typer.Option(None, "--end", "-e", help="End date (YYYY-MM-DD)"),
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format (text/json/csv)"
    ),
):
    """Display activity statistics."""
    try:
        from .stats import generate_stats

        settings = Settings(data_dir=data_dir if data_dir else Settings().data_dir)

        stats = generate_stats(settings, start_date, end_date, format)

        if format == "text":
            console.print(stats)
        else:
            typer.echo(stats)

    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1)


@app.command()
def check_permissions():
    """Check required macOS permissions."""
    try:
        # Import required frameworks
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

                url_str = Foundation.NSString.stringWithString_(
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
                )
                url = Foundation.NSURL.URLWithString_(url_str)
                Foundation.NSWorkspace.sharedWorkspace().openURL_(url)
            except Exception:
                console.print("[red]Could not open System Settings automatically[/red]")

        # Print detailed status
        console.print("\nPermission Status:")
        console.print(f"Accessibility: {'✓' if has_accessibility else '✗'}")
        if settings.enable_screen_recording:
            console.print(f"Screen Recording: {'✓' if has_screen else '✗'}")

    except ImportError as e:
        console.print(
            f"[red]Error importing macOS frameworks. Make sure you have PyObjC installed: {e}[/red]"
        )
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
