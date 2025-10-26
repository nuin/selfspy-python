# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Selfspy is a comprehensive activity monitoring and analytics tool for tracking keyboard, mouse, window, and terminal activity. Built with modern Python (3.10+), async/await patterns, SQLAlchemy 2.0, and platform-specific integrations for macOS.

## Development Commands

### Package Management
```bash
# Install all dependencies (including dev dependencies and macOS extras)
uv sync --group dev --extra macos

# Install without macOS-specific dependencies
uv sync --group dev
```

### Running the Application
```bash
# Start monitoring
uv run selfspy start

# Start with debug logging
uv run selfspy start --debug

# Check macOS permissions (required on macOS)
uv run selfspy check-permissions

# View basic statistics
uv run selfstats

# View enhanced visualizations
uv run selfviz enhanced

# View terminal command analytics
uv run selfterminal stats
```

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_models.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src --cov-report=html
```

### Code Quality
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Run linter
ruff check src/ tests/

# Type checking
mypy src/
```

## Architecture

### Core Components

1. **ActivityMonitor** (`src/activity_monitor.py`): Main orchestrator that coordinates platform-specific trackers, manages the event loop, and displays live statistics.

2. **ActivityStore** (`src/activity_store.py`): Async SQLAlchemy-based data layer handling all database operations. Uses aiosqlite for non-blocking I/O.

3. **Platform Abstraction** (`src/platform/`):
   - `base.py`: Abstract base classes for window/input tracking
   - `darwin.py`: macOS-specific window tracking using PyObjC
   - `darwin_input.py`: macOS input monitoring with Quartz event taps
   - `fallback.py`: Cross-platform fallback using pynput
   - Platform detection happens at runtime in ActivityMonitor

4. **Data Models** (`src/models.py`): SQLAlchemy 2.0 models using modern mapped_column syntax:
   - `Process`: Application processes with bundle IDs
   - `Window`: Window information with geometry and screen data
   - `Keys`: Encrypted keystroke data
   - `Click`: Mouse clicks with movement tracking

5. **Encryption** (`src/encryption.py`): Optional AES encryption for keystroke data using cryptography library and keyring for password storage.

### Desktop Widgets (`desktop-app/`)

Python/PyObjC implementations for macOS desktop widgets:
- `simple_widget.py`: Standalone widget with simulated data
- `selfspy_desktop_advanced.py`: Multi-widget system with real data integration
- Uses native Cocoa APIs via PyObjC for always-on-top, draggable windows

### CLI Structure

The project uses Typer for CLI with multiple command groups:
- `selfspy`: Main app with `start`, `check-permissions` commands
- `selfstats`: Basic statistics viewer
- `selfviz`: Enhanced visualizations with Plotly
- `selfterminal`: Terminal command analytics

All CLI apps are defined in `[project.scripts]` in `pyproject.toml`.

## Key Technical Details

### Async Patterns
- ActivityStore uses `AsyncSession` for non-blocking database operations
- ActivityMonitor runs in an asyncio event loop
- Platform trackers use callback-based APIs wrapped for async compatibility

### macOS Integration
- Requires Accessibility permissions (checked via `AXIsProcessTrusted()`)
- Optional Screen Recording permissions for screen capture features
- PyObjC frameworks (`pyobjc-framework-Quartz`, `pyobjc-framework-ApplicationServices`) for native macOS APIs
- Bundle ID tracking for app identification

### Database Schema
- SQLite database stored in user's data directory (default: `~/.selfspy/`)
- Comprehensive indexes for common queries (process name, window title, click coordinates, timestamps)
- Foreign key relationships: Process → Window → Keys/Clicks
- TimestampMixin provides `created_at`/`updated_at` on all models

### Configuration
- `src/config.py` uses pydantic-settings for configuration management
- Settings can be overridden via CLI flags or environment variables
- Data directory, encryption settings, debug mode configurable

## Testing

Tests use pytest with async support (`pytest-asyncio`). Test database is created in-memory or temp directory. Mock PyObjC dependencies when running on non-macOS platforms.

Key test file: `tests/test_models.py` - model relationships and database operations.

## Platform Support

- **Primary**: macOS with full feature support (window tracking, input monitoring, bundle IDs)
- **Fallback**: Other platforms use pynput-based tracking with reduced functionality
- Platform detection at runtime allows same codebase across platforms
