#!/usr/bin/env python3
"""
Installation script for Selfspy

This script handles the installation of Selfspy with proper dependency management
and platform-specific requirements. Supports both uv and pip installation methods.
"""

import platform
import subprocess
import sys
from pathlib import Path

def run_command(command, check=True):
    """Run a command and handle errors"""
    print(f"Running: {' '.join(command)}")
    try:
        result = subprocess.run(command, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def has_uv():
    """Check if uv is available"""
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 10):
        print("Error: Python 3.10 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✓ Python version {sys.version} is compatible")

def install_selfspy():
    """Install Selfspy with appropriate dependencies"""
    print("🚀 Installing Selfspy...")
    
    check_python_version()
    
    # Check if uv is available
    use_uv = has_uv()
    
    # Determine platform-specific requirements
    is_macos = platform.system() == "Darwin"
    
    if use_uv:
        print("📦 Detected uv - using uv for installation")
        if is_macos:
            print("📱 Detected macOS - installing with macOS support")
            run_command(["uv", "sync", "--extra", "macos"])
        else:
            print(f"🖥️  Detected {platform.system()} - installing with basic support")
            run_command(["uv", "sync"])
    else:
        print("📦 Using pip for installation")
        if is_macos:
            print("📱 Detected macOS - installing with macOS support")
            requirements_file = "requirements-macos.txt"
        else:
            print(f"🖥️  Detected {platform.system()} - installing with basic support")
            requirements_file = "requirements.txt"
        
        # Install dependencies
        print("📦 Installing dependencies...")
        run_command([sys.executable, "-m", "pip", "install", "-r", requirements_file])
        
        # Install the package in development mode
        print("🔧 Installing Selfspy in development mode...")
        run_command([sys.executable, "-m", "pip", "install", "-e", "."])
    
    print("\n✅ Installation complete!")
    print("\nQuick start:")
    if use_uv:
        print("  uv run selfspy --help             # Show help")
        print("  uv run selfspy check-permissions  # Check macOS permissions (macOS only)")
        print("  uv run selfspy start              # Start monitoring")
        print("  uv run selfviz enhanced           # View enhanced statistics")
        print("  uv run selfterminal commands      # View terminal command analytics")
    else:
        print("  selfspy --help                    # Show help")
        print("  selfspy check-permissions         # Check macOS permissions (macOS only)")
        print("  selfspy start                     # Start monitoring")
        print("  selfviz enhanced                  # View enhanced statistics")
        print("  selfterminal commands             # View terminal command analytics")
    
    if is_macos:
        print("\n🍎 macOS Setup:")
        print("  Make sure to grant Accessibility permissions when prompted.")
        cmd_prefix = "uv run " if use_uv else ""
        print(f"  {cmd_prefix}selfspy check-permissions   # Verify setup")

def install_dev():
    """Install development dependencies"""
    print("🛠️  Installing development dependencies...")
    
    check_python_version()
    use_uv = has_uv()
    is_macos = platform.system() == "Darwin"
    
    if use_uv:
        print("📦 Using uv for development installation")
        if is_macos:
            run_command(["uv", "sync", "--group", "dev", "--extra", "macos"])
        else:
            run_command(["uv", "sync", "--group", "dev"])
    else:
        print("📦 Using pip for development installation")
        run_command([sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"])
        run_command([sys.executable, "-m", "pip", "install", "-e", "."])
    
    # Install pre-commit hooks
    print("🪝 Setting up pre-commit hooks...")
    if use_uv:
        run_command(["uv", "run", "pre-commit", "install"], check=False)
    else:
        run_command([sys.executable, "-m", "pre_commit", "install"], check=False)
    
    print("\n✅ Development setup complete!")
    print("\nDevelopment commands:")
    if use_uv:
        print("  uv run pytest                   # Run tests")
        print("  uv run black src/ tests/        # Format code")
        print("  uv run ruff check src/ tests/   # Lint code")
        print("  uv run mypy src/                # Type check")
    else:
        print("  pytest                           # Run tests")
        print("  black src/ tests/                # Format code")
        print("  ruff check src/ tests/           # Lint code")
        print("  mypy src/                        # Type check")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Install Selfspy")
    parser.add_argument("--dev", action="store_true", help="Install development dependencies")
    
    args = parser.parse_args()
    
    if args.dev:
        install_dev()
    else:
        install_selfspy()