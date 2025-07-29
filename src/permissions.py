"""
Permission checking and setup for macOS
"""
import platform
from typing import Tuple

from rich.console import Console
from rich.prompt import Confirm


def check_macos_permissions() -> Tuple[bool, str]:
    """
    Check macOS permissions and return (has_permissions, message)
    """
    if platform.system() != "Darwin":
        return True, "Not on macOS - no special permissions needed"
    
    try:
        from ApplicationServices import AXIsProcessTrusted
        
        has_accessibility = AXIsProcessTrusted()
        
        if has_accessibility:
            return True, "All required permissions granted"
        else:
            return False, "Accessibility permission required"
            
    except ImportError:
        return False, "PyObjC frameworks not available - install with 'uv sync --extra macos'"


def prompt_for_permissions(console: Console) -> bool:
    """
    Interactive permission setup flow
    Returns True if user wants to continue setup, False to exit
    """
    console.print("\n[yellow]⚠️  Selfspy needs macOS Accessibility permissions to monitor activity[/yellow]")
    console.print("\n[cyan]What Selfspy monitors:[/cyan]")
    console.print("  • Window titles and application names")
    console.print("  • Keyboard activity (encrypted)")
    console.print("  • Mouse clicks and movements")
    console.print("  • All data stays on your computer")
    
    console.print("\n[cyan]To grant permissions:[/cyan]")
    console.print("  1. System Settings → Privacy & Security → Privacy → Accessibility")
    console.print("  2. Click the [+] button")
    console.print("  3. Add your terminal app (Terminal, iTerm2, etc.)")
    console.print("  4. Make sure the checkbox is checked")
    
    try_open = Confirm.ask("\n[green]Open System Settings automatically?[/green]", default=True)
    
    if try_open:
        try:
            import Foundation
            
            url_str = Foundation.NSString.stringWithString_(
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
            )
            url = Foundation.NSURL.URLWithString_(url_str)
            Foundation.NSWorkspace.sharedWorkspace().openURL_(url)
            console.print("[green]✓ Opened System Settings[/green]")
        except Exception:
            console.print("[yellow]Could not open System Settings automatically[/yellow]")
            console.print("Please open System Settings manually")
    
    console.print("\n[yellow]After granting permissions:[/yellow]")
    console.print("  • Restart your terminal")
    console.print("  • Run 'uv run selfspy start' again")
    
    return Confirm.ask("\n[cyan]Continue anyway? (will likely fail)[/cyan]", default=False)


def check_and_request_permissions(console: Console) -> bool:
    """
    Check permissions and handle the interactive flow
    Returns True if we should continue, False if we should exit
    """
    has_perms, msg = check_macos_permissions()
    
    if has_perms:
        return True
    
    # Show the permission setup flow
    return prompt_for_permissions(console)