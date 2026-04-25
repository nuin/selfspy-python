# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Selfspy is a comprehensive activity monitoring and analytics tool for tracking keyboard, mouse, window, and terminal activity. Built with modern Python (3.12+), async/await patterns, SQLAlchemy 2.0, and platform-specific integrations for macOS.

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
# Start headless monitoring (no TUI)
uv run selfspy daemon

# Start interactive TUI
uv run selfspy tui

# With debug logging
uv run selfspy daemon --debug

# Check macOS permissions (required on macOS)
uv run selfspy check-permissions

# View basic statistics
uv run selfspy stats

# View enhanced visualizations
uv run selfspy viz enhanced

# View terminal command analytics
uv run selfspy terminal commands

# Run database migrations
uv run selfspy migrate
```

### Testing
```bash
# Run all tests with coverage
uv run pytest

# Run specific test file
uv run pytest tests/test_models.py

# Run with verbose output
uv run pytest -v

# Run with coverage report
uv run pytest --cov=selfspy --cov-report=html
```

### Code Quality
```bash
# Format code
uv run ruff format src/ tests/

# Check formatting without modifying
uv run ruff format --check src/ tests/

# Run linter (also handles import sorting)
uv run ruff check src/ tests/

# Type checking
uv run mypy src/
```

## Architecture

### Package Layout

The project lives under `src/selfspy/` and is split into layered subpackages:

```
src/selfspy/
├── core/         # Settings, Monitor, lifecycle (orchestration)
├── storage/     # SQLAlchemy models, Store, encryption, password
├── tracking/   # Platform trackers, terminal tracker, permissions
├── analytics/  # Pure read-only data aggregation (no I/O outside DB)
├── tui/         # Textual-based terminal UI
└── cli/         # Thin Typer wrappers around the above
```

### Layer Rules

- `cli/` may import from any other layer (it is the presentation glue).
- `analytics/` is pure: it reads from `Store` and returns plain dicts/dataclasses. **No Rich, no Typer, no console output.**
- `core/` orchestrates `tracking/` and `storage/` but does not depend on `cli/` or `tui/`.
- `tracking/` and `storage/` are self-contained and may depend only on `core.config`.
- `tui/` reads state from `core.Monitor` but does not write to the DB directly.

### Core Components

1. **Monitor** (`src/selfspy/core/monitor.py`): Coordinates platform-specific trackers, manages the event loop, and exposes live stats for the TUI.
2. **lifecycle.run** (`src/selfspy/core/lifecycle.py`): Top-level entrypoint that wires Settings, Store, and Monitor together; exported as `run_monitor` from `selfspy.core`.
3. **Store** (`src/selfspy/storage/store.py`): Async SQLAlchemy data layer using `aiosqlite` for non-blocking I/O.
4. **Platform Abstraction** (`src/selfspy/tracking/platform/`):
   - `base.py`: Abstract base classes for window/input tracking
   - `darwin.py`: macOS-specific window and input tracking using PyObjC
   - `fallback.py`: Cross-platform fallback using pynput
   - `input_tracker.py`: Generic pynput-based input tracker
5. **Data Models** (`src/selfspy/storage/models.py`): SQLAlchemy 2.0 models using modern `mapped_column` syntax: `Session`, `Process`, `Window`, `Keys`, `Click`.
6. **Encryption** (`src/selfspy/storage/encryption.py`): Optional Fernet encryption for keystroke data with PBKDF2 key derivation.
7. **TUI** (`src/selfspy/tui/`): Textual-based tabbed interface (Live, Apps, Summary). `runner.run_tui(monitor)` launches the app.
8. **Analytics** (`src/selfspy/analytics/`): Pure aggregation — `stats`, `viz`, `terminal` modules. CLI wrappers in `cli/` add Rich rendering on top.

### Desktop Widgets (`desktop-app/`)

Python/PyObjC implementations for macOS desktop widgets. **Currently broken after the Phase 1 package refactor** — these will be modernized in Phase 3 to import from `selfspy.*` instead of `src.*`.

### CLI Structure

The project uses Typer with a single entrypoint and seven subcommands, each defined in its own module under `src/selfspy/cli/`:

- `selfspy daemon` — start headless tracking (`cli/daemon.py`)
- `selfspy tui` — start interactive TUI (`cli/tui.py`)
- `selfspy stats` — basic activity stats (`cli/stats.py`)
- `selfspy viz` — enhanced visualizations (`cli/viz.py`)
- `selfspy terminal` — terminal command analytics (`cli/terminal.py`)
- `selfspy migrate` — alembic migrations (`cli/migrate.py`)
- `selfspy check-permissions` — verify macOS permissions (`cli/permissions.py`)

`cli/main.py` mounts each as a sub-app via `app.add_typer(...)`. Only one entrypoint (`selfspy = "selfspy.cli.main:app"`) is declared in `pyproject.toml`.

## Key Technical Details

### Event Flow and Threading
- Input events arrive from pynput callbacks on a separate thread
- Events are added to an `asyncio.Queue` via `loop.call_soon_threadsafe()` (thread-safe)
- The main async loop periodically flushes the queue to the database
- Buffer flush triggers: timeout (1 second), buffer size >50, or explicit flush
- This pattern prevents blocking the pynput thread while ensuring async DB writes

### Async Patterns
- `Store` uses `AsyncSession` for non-blocking DB operations
- `Monitor` runs in an asyncio event loop
- Platform trackers use callback-based APIs wrapped for async compatibility
- Schema creation falls back to `Base.metadata.create_all` if Alembic is unavailable

### macOS Integration
- Requires Accessibility permissions (checked via `AXIsProcessTrusted()`)
- Optional Screen Recording permissions for screen capture features
- PyObjC frameworks (`pyobjc-framework-Quartz`, `pyobjc-framework-ApplicationServices`) for native APIs
- Bundle ID tracking for app identification

### Database Schema
- SQLite database stored in user's data directory (default: `~/.selfspy/`)
- Comprehensive indexes for common queries (process name, window title, click coordinates, timestamps)
- Foreign key relationships: Session ← Window, Process → Window → Keys/Clicks
- `TimestampMixin` provides `created_at`/`updated_at` on all models
- Alembic migrations in `alembic/`; falls back to `create_all` if unavailable

### Session and Idle Tracking
- Sessions track aggregate metrics: `total_keystrokes`, `total_clicks`, `active_seconds`, `idle_seconds`
- Idle detection threshold: 3 minutes without input activity
- `Store.update_session_metrics()` updates atomically via SQL arithmetic
- Windows track `focus_seconds` for time spent with activity in each window

### Configuration
- `src/selfspy/core/config.py` uses pydantic-settings for configuration
- Settings can be overridden via CLI flags or `SELFSPY_*` environment variables
- Data directory, encryption settings, debug mode all configurable

## Testing

Tests use pytest with async support (`pytest-asyncio`, asyncio_mode = "auto"). Test database lives in `tmp_path`.

```bash
# Run single test
uv run pytest tests/storage/test_store.py::test_store_start_session_returns_id -v

# Run with specific marker
uv run pytest -m "not slow"
```

Test layout mirrors `src/selfspy/`:

```
tests/
├── analytics/   # Pure-data aggregation
├── core/         # Settings, lifecycle
├── storage/     # Store, encryption
├── tracking/   # Permissions
├── integration/ # Monitor → DB smoke tests
└── tui/         # Textual app + tabs
```

All test imports use the `selfspy.*` package path (not `src.*`).

## Platform Support

- **Primary**: macOS with full feature support (window tracking, input monitoring, bundle IDs)
- **Fallback**: Other platforms use pynput-based tracking with reduced functionality
- Platform detection at runtime via `platform.system()` in `Monitor._init_platform_trackers()`
