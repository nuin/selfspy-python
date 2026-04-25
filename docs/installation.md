# Installation Guide

## Prerequisites

- Python 3.10 or higher
- macOS 10.12+ (for full feature support)
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

## Quick Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/selfspy-python.git
cd selfspy-python

# Install with all dependencies
uv sync --group dev --extra macos

# Or install without development dependencies
uv sync --extra macos
```

### Using pip

```bash
# Install from source
pip install -e .

# Install with macOS support
pip install -e ".[macos]"

# Install with development dependencies
pip install -e ".[dev]"
```

## Platform-Specific Setup

### macOS

#### Required Permissions

Selfspy requires special permissions on macOS to monitor system activity:

1. **Accessibility Access** (Required)
   - Monitors keyboard and mouse activity
   - Tracks active windows and applications

2. **Screen Recording** (Optional)
   - Only needed if screen capture features are enabled
   - Not required for basic monitoring

#### Granting Permissions

```bash
# Check current permission status
uv run selfspy check-permissions
```

This command will:
- Check which permissions are granted
- Open System Settings to the correct panel
- Guide you through the permission process

**Manual Steps:**
1. Open **System Settings** → **Privacy & Security** → **Privacy**
2. Select **Accessibility**
3. Add your terminal application (Terminal.app, iTerm2, etc.)
4. Enable the checkbox next to it

#### Installing PyObjC Dependencies

macOS support requires PyObjC frameworks:

```bash
# Included with --extra macos
uv sync --extra macos

# Or install separately
pip install pyobjc-framework-Quartz pyobjc-framework-ApplicationServices
```

### Linux

Limited support using fallback pynput-based tracking:

```bash
# Install without macOS extras
uv sync --group dev

# Additional X11 dependencies may be required
sudo apt-get install python3-xlib  # Debian/Ubuntu
```

### Windows

Basic support using pynput:

```bash
# Install without macOS extras
uv sync --group dev
```

## Verify Installation

```bash
# Check that selfspy command is available
uv run selfspy --help

# Test monitoring (will request permissions on macOS)
uv run selfspy daemon --debug

# Stop with Ctrl+C
```

## Desktop Widgets (Optional)

For macOS desktop widgets:

```bash
# Python widgets (included with main install)
cd desktop-app
./simple_widget.py

# Or the advanced multi-widget system
./selfspy_desktop_advanced.py
```

## Database Location

By default, Selfspy stores data in:
- macOS: `~/.selfspy/selfspy.db`
- Linux: `~/.local/share/selfspy/selfspy.db`
- Windows: `%APPDATA%\selfspy\selfspy.db`

You can override this with the `--data-dir` flag.

## Encryption Setup

If you want encrypted keystroke storage:

1. First run will prompt for password:
```bash
uv run selfspy daemon
```

2. Or provide password via command line:
```bash
uv run selfspy daemon --password "your-password"
```

Passwords are stored securely in your system keychain.

## Troubleshooting

### Permission Issues on macOS

If monitoring doesn't work after granting permissions:
1. Completely quit and restart your terminal application
2. Re-run permission check: `uv run selfspy check-permissions`
3. Try with `--debug` flag to see detailed error messages

### Import Errors

If you see PyObjC import errors on macOS:
```bash
# Reinstall macOS extras
uv sync --extra macos --reinstall
```

### Database Errors

If you encounter database issues:
```bash
# Remove existing database (WARNING: deletes all data)
rm -rf ~/.selfspy/

# Start fresh
uv run selfspy daemon
```

## Next Steps

- [Usage Guide](usage.md) - Learn how to use Selfspy
- [Configuration](configuration.md) - Customize your setup
- [Desktop Widgets](desktop-widgets.md) - Setup always-visible activity widgets
