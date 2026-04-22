# Phase 1: Foundation Cleanup & Architecture Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `docs/superpowers/specs/2026-04-21-phase1-foundation-refactor-design.md`

**Goal:** Migrate Selfspy from `src/`-with-multiple-entrypoints to `src/selfspy/` proper package with 6 subpackages, single `selfspy` CLI, regenerated Alembic baseline, and stricter tooling — all with no feature changes.

**Architecture:** Six subpackages (`core`, `tracking`, `storage`, `analytics`, `cli`, `tui`) with enforced layering. `analytics/` is pure functions; `cli/` is thin presentation. `core/lifecycle.py` owns asyncio entry; `core/monitor.py` orchestrates trackers + store; both `cli/daemon.py` and `cli/tui.py` call `lifecycle.run(...)`.

**Tech Stack:** Python 3.12+, uv, hatchling, SQLAlchemy 2.0 + aiosqlite, Alembic, Typer, Textual, Rich, Pydantic v2, ruff, mypy --strict, pytest + pytest-asyncio.

---

## Task 0: Create worktree and capture baseline

**Files:**
- No edits — setup only

- [ ] **Step 1: Create worktree**

```bash
cd /Users/nuin/Projects/selfspy-python
git worktree add ../selfspy-revamp -b revamp/phase-1-foundation
cd ../selfspy-revamp
```

Expected: new worktree at `../selfspy-revamp`, branch `revamp/phase-1-foundation` checked out.

- [ ] **Step 2: Verify baseline tests pass**

```bash
uv sync --group dev --extra macos
uv run pytest 2>&1 | tail -20
```

Expected: tests run (some may already fail — capture the baseline pass/fail count).

- [ ] **Step 3: Verify baseline lint state**

```bash
uv run ruff check src/ tests/ 2>&1 | tail -5 || true
uv run mypy src/ 2>&1 | tail -5 || true
```

Expected: capture any existing warnings as baseline. We won't increase counts during the refactor.

- [ ] **Step 4: Verify CLI still works**

```bash
uv run selfspy --help
uv run selfspy start --help
```

Expected: help text printed, no exceptions.

- [ ] **Step 5: No commit — baseline only**

This task creates no commits. Move to Task 1.

---

## Task 1: Delete legacy files and tighten .gitignore

**Files:**
- Delete: `poetry.lock`, `requirements.txt`, `requirements-dev.txt`, `requirements-macos.txt`, `install.py`, `MANIFEST.in`, `dist/`, `.coverage`, `pytest.ini`, `src/selfviz.py`
- Modify: `.gitignore`
- Modify: `pyproject.toml` (fold pytest.ini contents)

- [ ] **Step 1: Delete legacy files**

```bash
rm -f poetry.lock requirements.txt requirements-dev.txt requirements-macos.txt install.py MANIFEST.in .coverage pytest.ini src/selfviz.py
rm -rf dist/
```

Expected: files gone. `git status` shows them as deleted.

- [ ] **Step 2: Read existing .gitignore**

```bash
cat .gitignore
```

Already covers most. Add only the missing entries.

- [ ] **Step 3: Update .gitignore**

Append to the end of `.gitignore`:

```
# Tooling caches
.ruff_cache/
.mypy_cache/

# Coverage
htmlcov/
coverage.xml
```

- [ ] **Step 4: Read pytest.ini that we just deleted (recover content from git)**

```bash
git show HEAD:pytest.ini
```

Note its contents (likely `[pytest]` section with `asyncio_mode = auto` etc.).

- [ ] **Step 5: Fold pytest config into pyproject.toml**

The `pyproject.toml` already has `[tool.pytest.ini_options]`. Ensure it includes `asyncio_mode = "auto"`. Edit `pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-ra -q --cov=src"
asyncio_mode = "auto"
```

- [ ] **Step 6: Verify tests still run**

```bash
uv run pytest 2>&1 | tail -10
```

Expected: same pass/fail as baseline (deletions don't affect test execution).

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: remove legacy lockfiles, requirements, install scripts; fold pytest.ini"
```

---

## Task 2: Bump Python floor to 3.12

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Read current pyproject.toml**

```bash
cat pyproject.toml | grep -E "(requires-python|python_version|target-version)"
```

- [ ] **Step 2: Update Python floor in pyproject.toml**

Change `requires-python = ">=3.10"` to `requires-python = ">=3.12"`.

Update `classifiers` — remove `"Programming Language :: Python :: 3.10"` and `"Programming Language :: Python :: 3.11"`, add `"Programming Language :: Python :: 3.12"` and `"Programming Language :: Python :: 3.13"`.

- [ ] **Step 3: Update mypy and black target**

In `[tool.mypy]`: change `python_version = "3.10"` to `python_version = "3.12"`.

If `[tool.black]` exists: change `target-version = ['py310']` to `target-version = ['py312']` (we'll remove black entirely in Task 3, but consistent now).

- [ ] **Step 4: Resync uv with new floor**

```bash
uv sync --group dev --extra macos 2>&1 | tail -5
```

Expected: success. If uv complains about Python version on this machine, install Python 3.12+ first.

- [ ] **Step 5: Verify tests still pass**

```bash
uv run pytest 2>&1 | tail -5
```

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: bump python floor to 3.12"
```

---

## Task 3: Switch from black/isort to ruff format + lint

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Remove black, isort from dev deps**

In `pyproject.toml`, edit `[project.optional-dependencies] dev = [...]` AND `[dependency-groups] dev = [...]`. Remove these lines from both:

```
"black>=23.12.1",
"isort>=5.13.2",
```

- [ ] **Step 2: Delete old `[tool.black]` and `[tool.isort]` sections**

Remove both blocks from `pyproject.toml`.

- [ ] **Step 3: Add ruff configuration**

Append to `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "I",    # isort
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "RUF",  # ruff-specific
]
ignore = [
    "E501",  # line length (handled by formatter)
    "B008",  # function calls in defaults (Typer pattern)
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["B011"]  # asserts allowed in tests

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

- [ ] **Step 4: Resync**

```bash
uv sync --group dev --extra macos
```

- [ ] **Step 5: Run ruff format on entire codebase**

```bash
uv run ruff format src/ tests/
```

Expected: many files reformatted. Review the diff.

- [ ] **Step 6: Run ruff check + autofix**

```bash
uv run ruff check --fix src/ tests/
```

Expected: many auto-fixes. Review remaining warnings — leave them for now if they require code changes (we'll fix during the refactor).

- [ ] **Step 7: Verify tests pass after format**

```bash
uv run pytest 2>&1 | tail -5
```

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "chore: replace black/isort with ruff format+lint"
```

---

## Task 4: Enable mypy strict mode with PyObjC overrides

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Replace [tool.mypy] section**

Replace the existing `[tool.mypy]` block with:

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_unused_ignores = true
warn_redundant_casts = true
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = [
    "ApplicationServices.*",
    "Foundation.*",
    "AppKit.*",
    "Quartz.*",
    "AVFoundation.*",
    "objc.*",
    "pynput.*",
    "Crypto.*",
]
ignore_errors = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
disallow_incomplete_defs = false
```

- [ ] **Step 2: Run mypy and capture output**

```bash
uv run mypy src/ 2>&1 | tail -30
```

Expected: many errors (this is fine — we'll reduce them through the refactor). Record the count.

- [ ] **Step 3: Add per-file `# type: ignore` only where strictly needed for green tests**

Don't try to fix all mypy errors here. The refactor tasks below will improve types as code moves. Goal: don't make mypy strictly worse than baseline.

- [ ] **Step 4: Verify tests pass**

```bash
uv run pytest 2>&1 | tail -5
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "chore: enable mypy strict mode with PyObjC/pynput overrides"
```

---

## Task 5: Rename `src/*` → `src/selfspy/*` (package rename only)

This is the biggest mechanical change. No logic edits — just moving files and updating imports.

**Files:**
- Move all files under `src/` into `src/selfspy/`
- Modify: every `.py` file with relative imports
- Modify: `tests/conftest.py`, `tests/test_models.py`, `tests/tui/*.py`
- Modify: `pyproject.toml` (hatch packages, pytest pythonpath, coverage source)

- [ ] **Step 1: Create new package structure**

```bash
mkdir -p src/selfspy
git mv src/__init__.py src/selfspy/__init__.py
git mv src/activity_monitor.py src/selfspy/activity_monitor.py
git mv src/activity_store.py src/selfspy/activity_store.py
git mv src/check_password.py src/selfspy/check_password.py
git mv src/cli.py src/selfspy/cli.py
git mv src/config.py src/selfspy/config.py
git mv src/encryption.py src/selfspy/encryption.py
git mv src/enhanced_stats.py src/selfspy/enhanced_stats.py
git mv src/models.py src/selfspy/models.py
git mv src/password_dialog.py src/selfspy/password_dialog.py
git mv src/permissions.py src/selfspy/permissions.py
git mv src/schemas.py src/selfspy/schemas.py
git mv src/stats.py src/selfspy/stats.py
git mv src/terminal_stats.py src/selfspy/terminal_stats.py
git mv src/terminal_tracker.py src/selfspy/terminal_tracker.py
git mv src/platform src/selfspy/platform
git mv src/tui src/selfspy/tui
```

Expected: `ls src/` shows only `selfspy/` directory.

- [ ] **Step 2: Update pyproject.toml for new layout**

Edit `pyproject.toml`:

```toml
[project.scripts]
selfspy = "selfspy.cli:app"
selfstats = "selfspy.stats:app"
selfviz = "selfspy.enhanced_stats:app"
selfterminal = "selfspy.terminal_stats:app"

[tool.hatch.build.targets.wheel]
packages = ["src/selfspy"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-ra -q --cov=selfspy"
asyncio_mode = "auto"

[tool.coverage.run]
source = ["src/selfspy"]
```

- [ ] **Step 3: Update tests/conftest.py imports**

Replace contents of `tests/conftest.py` lines 14-21 (the `sys.path.append` block + imports):

```python
"""
Pytest configuration and fixtures
"""

import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from selfspy.activity_store import ActivityStore
from selfspy.config import Settings
from selfspy.models import Base
```

Remove the `sys.path` manipulation entirely. Then keep the existing fixtures unchanged.

- [ ] **Step 4: Update tests/test_models.py**

Replace lines 1-13 with:

```python
"""
Tests for database models
"""

from selfspy.models import Process, Window
```

- [ ] **Step 5: Update tests/tui/*.py imports**

For each file in `tests/tui/`, change `from src.tui...` and `from src...` imports to `from selfspy.tui...` / `from selfspy...`. Use:

```bash
grep -rln "from src\." tests/
```

Expected: list of test files needing updates. For each one:

```bash
# Verify what needs changing
grep -n "from src\." tests/tui/test_app.py
```

Then edit each to replace `from src.` with `from selfspy.` and `import src.` with `import selfspy.`.

- [ ] **Step 6: Update intra-package imports inside src/selfspy/**

The existing files use relative imports like `from .activity_store import ActivityStore` — these still work because they're now `selfspy.activity_store`. **No changes needed for relative imports.**

But check for any absolute imports of `src.X`:

```bash
grep -rn "from src\." src/
grep -rn "import src\." src/
```

Expected: no matches (the source uses relative imports throughout). If any matches appear, replace `src.` with `selfspy.`.

- [ ] **Step 7: Reinstall the package**

```bash
uv sync --group dev --extra macos
```

Expected: success. The `pip install -e .` (run by uv sync via hatch) picks up the new `src/selfspy/` layout.

- [ ] **Step 8: Smoke-test the CLI**

```bash
uv run selfspy --help
uv run selfspy start --help
uv run selfstats --help
```

Expected: all show help. If `ModuleNotFoundError: No module named 'src'`, hunt for stragglers with `grep -rn "from src\." .`.

- [ ] **Step 9: Run tests**

```bash
uv run pytest 2>&1 | tail -10
```

Expected: same pass/fail as Task 4 baseline. Any new failures are due to import paths — fix them.

- [ ] **Step 10: Run ruff + mypy**

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/ 2>&1 | tail -5
```

Expected: clean ruff, mypy at or below baseline error count.

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "refactor: rename src/* to src/selfspy/* (package rename, no logic changes)"
```

---

## Task 6: Drop alembic, regenerate baseline migration

**Files:**
- Delete: `alembic/`, `alembic.ini`
- Modify: `src/selfspy/activity_store.py` (remove embedded migration runner)
- Create: `alembic/` (regenerated), `alembic.ini` (regenerated)
- Create: `src/selfspy/migrate.py` (CLI helper)

- [ ] **Step 1: Delete existing alembic config**

```bash
rm -rf alembic/
rm -f alembic.ini
```

- [ ] **Step 2: Strip alembic logic from activity_store.py**

Edit `src/selfspy/activity_store.py`:

Delete imports (lines 15-16):
```python
from alembic import command
from alembic.config import Config
```

Delete the `_run_migrations` method entirely (lines 51-76).

Replace the `initialize` method body (lines 78-101) — replace the migration call block with direct `create_all`:

```python
async def initialize(self):
    """Initialize database and verify encryption password"""
    if self._initialized:
        return

    # Create tables if they don't exist (Alembic-managed in production via `selfspy migrate`)
    async with self.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Verify encryption password if encryption is enabled
    if self.settings.encryption_enabled:
        password_valid = await check_password(
            self.settings.data_dir, self.cipher, self.settings.read_only
        )
        if not password_valid:
            raise ValueError("Invalid encryption password")

    self._initialized = True
    logger.info("Activity store initialized successfully")
```

- [ ] **Step 3: Initialize fresh alembic**

```bash
uv run alembic init alembic
```

Expected: creates `alembic/`, `alembic.ini`. The `env.py` is generic.

- [ ] **Step 4: Wire env.py to selfspy models**

Edit `alembic/env.py`. Find the line `target_metadata = None` and replace with:

```python
from selfspy.models import Base
target_metadata = Base.metadata
```

Also update `alembic.ini` — change `sqlalchemy.url = ...` line to:

```
sqlalchemy.url = sqlite:///%(here)s/.selfspy/selfspy.db
```

(This is just a default; the real URL is overridden by the migrate CLI later.)

- [ ] **Step 5: Generate baseline migration**

```bash
uv run alembic revision --autogenerate -m "initial schema"
```

Expected: a new file at `alembic/versions/<hash>_initial_schema.py` with `upgrade()` containing `op.create_table(...)` calls for all models.

- [ ] **Step 6: Verify migration runs on empty DB**

```bash
rm -rf /tmp/selfspy-migrate-test
uv run alembic -x dburl=sqlite:////tmp/selfspy-migrate-test.db upgrade head 2>&1 | tail -5
```

If alembic env.py doesn't read `-x dburl`, edit `env.py`'s `run_migrations_offline` and `run_migrations_online` to honor `context.get_x_argument(as_dictionary=True).get("dburl")`. Add at top of `run_migrations_online`:

```python
url_override = context.get_x_argument(as_dictionary=True).get("dburl")
if url_override:
    config.set_main_option("sqlalchemy.url", url_override)
```

Same for offline mode.

- [ ] **Step 7: Verify selfspy can still start (uses create_all fallback)**

```bash
uv run pytest 2>&1 | tail -10
```

Expected: tests pass — `ActivityStore.initialize()` now does `create_all` directly.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor: regenerate alembic baseline; strip migration runner from ActivityStore"
```

---

## Task 7: Move TUI runner out of activity_monitor.py

**Files:**
- Create: `src/selfspy/tui/runner.py`
- Modify: `src/selfspy/activity_monitor.py`

- [ ] **Step 1: Create tui/runner.py**

Create `src/selfspy/tui/runner.py`:

```python
"""TUI runner — drives the SelfspyApp from a running ActivityMonitor."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog

from .app import SelfspyApp
from .tabs.apps import AppData

if TYPE_CHECKING:
    from ..activity_monitor import ActivityMonitor

logger = structlog.get_logger()


async def run_tui(monitor: "ActivityMonitor") -> None:
    """Run the Textual TUI bound to the given monitor."""
    app = SelfspyApp()

    async def update_loop() -> None:
        while monitor.running and not monitor._shutdown_event.is_set():
            try:
                await monitor._check_active_window()
                await monitor._flush_buffer()
                monitor._update_metrics()

                state = monitor.get_current_state()

                app.update_live_metrics(
                    keystrokes=state["keystrokes"],
                    clicks=state["clicks"],
                    keys_per_min=state["keys_per_min"],
                    clicks_per_min=state["clicks_per_min"],
                    current_window=state["current_window"],
                    status=state["status"],
                    session_duration=state["session_duration"],
                )

                if state["keystroke_history"]:
                    app.add_activity_samples(
                        state["keystroke_history"][-1] if state["keystroke_history"] else 0,
                        state["click_history"][-1] if state["click_history"] else 0,
                    )

                apps = [
                    AppData(
                        name=a["name"],
                        keystrokes=a["keystrokes"],
                        clicks=a["clicks"],
                        activity_percent=a["activity_percent"],
                    )
                    for a in state["apps"]
                ]
                app.update_apps(apps)

                app.update_summary(
                    session_duration=state["session_duration"],
                    active_time=state["active_time"],
                    active_percent=state["active_percent"],
                    idle_time=state["idle_time"],
                    idle_percent=state["idle_percent"],
                    total_keystrokes=state["keystrokes"],
                    total_clicks=state["clicks"],
                    windows_switched=state["windows_switched"],
                    yesterday_diff=state["yesterday_diff"],
                    more_active=state["more_active"],
                )

                await asyncio.sleep(1)
            except Exception as e:
                logger.error("TUI update error", error=str(e))
                await asyncio.sleep(1)

    update_task = asyncio.create_task(update_loop())
    try:
        await app.run_async()
    finally:
        monitor.running = False
        update_task.cancel()
        try:
            await update_task
        except asyncio.CancelledError:
            pass
```

- [ ] **Step 2: Update activity_monitor.py to delegate**

In `src/selfspy/activity_monitor.py`, replace the `_run_with_tui` method (lines 375-452) with:

```python
async def _run_with_tui(self):
    """Run with the Textual TUI (delegates to tui.runner)."""
    from .tui.runner import run_tui
    await run_tui(self)
```

- [ ] **Step 3: Verify CLI still works**

```bash
uv run pytest 2>&1 | tail -5
uv run selfspy start --help
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: move TUI runner from activity_monitor into selfspy/tui/runner.py"
```

---

## Task 8: Extract storage layer

**Files:**
- Create: `src/selfspy/storage/__init__.py`
- Move: `models.py` → `storage/models.py`
- Move: `activity_store.py` → `storage/store.py` (rename `ActivityStore` → `Store`)
- Move: `encryption.py` → `storage/encryption.py`
- Merge: `check_password.py` + `password_dialog.py` → `storage/password.py`
- Modify: all importers

- [ ] **Step 1: Create storage package**

```bash
mkdir -p src/selfspy/storage
touch src/selfspy/storage/__init__.py
```

- [ ] **Step 2: Move models.py and encryption.py**

```bash
git mv src/selfspy/models.py src/selfspy/storage/models.py
git mv src/selfspy/encryption.py src/selfspy/storage/encryption.py
```

- [ ] **Step 3: Move activity_store.py and rename class**

```bash
git mv src/selfspy/activity_store.py src/selfspy/storage/store.py
```

Edit `src/selfspy/storage/store.py`:
- Update relative imports: `from ..config import Settings`, `from .encryption import check_password, create_cipher`, `from .models import Base, Click, Keys, Process, Session, Window`
- Rename class `ActivityStore` → `Store`

- [ ] **Step 4: Merge check_password.py + password_dialog.py into storage/password.py**

Create `src/selfspy/storage/password.py` containing the unique non-duplicate logic from both files. Note: `src/selfspy/check_password.py` uses old Blowfish-based crypto and is **dead code** (not imported by `activity_store.py` which uses `encryption.check_password`). Verify with:

```bash
grep -rn "check_password" src/ tests/
grep -rn "from .check_password\|from selfspy.check_password" src/ tests/
```

If `check_password.py` is unimported, just delete it:

```bash
git rm src/selfspy/check_password.py
```

Then move `password_dialog.py`:

```bash
git mv src/selfspy/password_dialog.py src/selfspy/storage/password.py
```

- [ ] **Step 5: Add re-exports in storage/__init__.py**

```python
"""Storage layer: persistence, encryption, and password handling."""

from .encryption import check_password, create_cipher
from .models import Base, Click, Keys, Process, Session, Window
from .password import get_password, set_keyring_password
from .store import Store

__all__ = [
    "Base",
    "Click",
    "Keys",
    "Process",
    "Session",
    "Store",
    "Window",
    "check_password",
    "create_cipher",
    "get_password",
    "set_keyring_password",
]
```

- [ ] **Step 6: Update all importers**

```bash
grep -rln "from .activity_store\|from .models\|from .encryption\|from .password_dialog" src/
grep -rln "ActivityStore" src/ tests/
```

For each file shown, replace:
- `from .activity_store import ActivityStore` → `from .storage import Store`
- `from .models import X` → `from .storage import X` (or `from .storage.models import X` for inner-package use)
- `from .encryption import X` → `from .storage.encryption import X`
- `from .password_dialog import X` → `from .storage.password import X`
- `ActivityStore(` → `Store(`
- Any `import .models` references in test files → `from selfspy.storage import ...`

Specific files to edit (verified during step):
- `src/selfspy/activity_monitor.py` — uses `ActivityStore`
- `src/selfspy/cli.py` — uses `ActivityStore`, `password_dialog.get_password`
- `src/selfspy/stats.py` — uses `models`, `encryption`
- `src/selfspy/enhanced_stats.py` — uses `models`
- `src/selfspy/terminal_stats.py` — uses `models`
- `src/selfspy/terminal_tracker.py` — uses `models`
- `tests/conftest.py` — `from selfspy.activity_store import ActivityStore` → `from selfspy.storage import Store`
- `tests/test_models.py` — `from selfspy.models import Process, Window` → `from selfspy.storage import Process, Window`

- [ ] **Step 7: Reinstall and test**

```bash
uv sync --group dev --extra macos
uv run pytest 2>&1 | tail -10
uv run selfspy --help
```

Expected: tests pass, CLI shows help.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor: extract storage layer (models, store, encryption, password)"
```

---

## Task 9: Extract tracking layer

**Files:**
- Create: `src/selfspy/tracking/__init__.py`
- Move: `terminal_tracker.py` → `tracking/terminal.py`
- Move: `permissions.py` → `tracking/permissions.py`
- Move: `platform/` → `tracking/platform/`
- Modify: importers

- [ ] **Step 1: Create tracking package**

```bash
mkdir -p src/selfspy/tracking
touch src/selfspy/tracking/__init__.py
```

- [ ] **Step 2: Move files**

```bash
git mv src/selfspy/terminal_tracker.py src/selfspy/tracking/terminal.py
git mv src/selfspy/permissions.py src/selfspy/tracking/permissions.py
git mv src/selfspy/platform src/selfspy/tracking/platform
```

- [ ] **Step 3: Update imports inside moved files**

In `src/selfspy/tracking/terminal.py`: change `from .models import X` → `from ..storage.models import X` (or `from ..storage import X` for the public-API names).

In `src/selfspy/tracking/permissions.py`: no relative imports — only stdlib. No changes.

In `src/selfspy/tracking/platform/*.py`: check for cross-imports — most are self-contained. If any import from `selfspy.X`, update to relative imports `from ..` or `from ...`.

- [ ] **Step 4: Add re-exports in tracking/__init__.py**

```python
"""Tracking layer: input, window, terminal capture and permissions."""

from .permissions import (
    check_and_request_permissions,
    check_macos_permissions,
)
from .terminal import TerminalTracker

__all__ = [
    "TerminalTracker",
    "check_and_request_permissions",
    "check_macos_permissions",
]
```

- [ ] **Step 5: Update importers**

```bash
grep -rln "from .terminal_tracker\|from .permissions\|from .platform\|TerminalTracker" src/ tests/
```

For each match, replace:
- `from .terminal_tracker import TerminalTracker` → `from .tracking import TerminalTracker`
- `from .permissions import X` → `from .tracking.permissions import X`
- `from .platform.input_tracker import InputTracker` → `from .tracking.platform.input_tracker import InputTracker`
- `from .platform.darwin import X` → `from .tracking.platform.darwin import X`
- `from .platform.fallback import X` → `from .tracking.platform.fallback import X`

Specifically:
- `src/selfspy/activity_monitor.py` — multiple platform imports
- `src/selfspy/cli.py` — `from .permissions import check_and_request_permissions`

- [ ] **Step 6: Reinstall and test**

```bash
uv sync --group dev --extra macos
uv run pytest 2>&1 | tail -10
uv run selfspy --help
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: extract tracking layer (permissions, terminal, platform)"
```

---

## Task 10: Extract core layer; split monitor + lifecycle

**Files:**
- Create: `src/selfspy/core/__init__.py`
- Move: `config.py` → `core/config.py`
- Move: `schemas.py` → `core/schemas.py`
- Split: `activity_monitor.py` → `core/monitor.py` (orchestration) + `core/lifecycle.py` (asyncio entry + signals)
- Modify: importers

- [ ] **Step 1: Create core package and move config/schemas**

```bash
mkdir -p src/selfspy/core
touch src/selfspy/core/__init__.py
git mv src/selfspy/config.py src/selfspy/core/config.py
git mv src/selfspy/schemas.py src/selfspy/core/schemas.py
```

- [ ] **Step 2: Move activity_monitor.py → core/monitor.py (rename only first)**

```bash
git mv src/selfspy/activity_monitor.py src/selfspy/core/monitor.py
```

Update its imports:
- `from .activity_store import ActivityStore` → `from ..storage import Store as ActivityStore` (keep the alias for now, removed in next step)
- `from .config import Settings` → `from .config import Settings`
- `from .platform.input_tracker import InputTracker` → `from ..tracking.platform.input_tracker import InputTracker`
- `from .terminal_tracker import TerminalTracker` → `from ..tracking import TerminalTracker`
- `from .models import Session` → `from ..storage.models import Session`
- `from .tui.runner import run_tui` (already in `_run_with_tui`)

- [ ] **Step 3: Rename ActivityMonitor → Monitor**

In `core/monitor.py`, rename the class from `ActivityMonitor` to `Monitor` (Find/Replace). Drop the alias from Step 2 — change `from ..storage import Store as ActivityStore` to `from ..storage import Store` and update internal references from `"ActivityStore"` (in type hints) to `"Store"`.

- [ ] **Step 4: Create core/lifecycle.py**

Create `src/selfspy/core/lifecycle.py`:

```python
"""Lifecycle management: signal handling, asyncio entry, graceful shutdown."""

from __future__ import annotations

import asyncio
import signal
from typing import TYPE_CHECKING

import structlog
from rich.console import Console

if TYPE_CHECKING:
    from .monitor import Monitor

logger = structlog.get_logger()


def run(monitor: "Monitor", *, use_tui: bool) -> None:
    """Run a monitor to completion with signal handling.

    Owns the asyncio event loop entry point. Installs SIGINT/SIGTERM
    handlers that schedule monitor.stop() on the loop.
    """
    console = Console()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def signal_handler(signum, frame):
        console.print("\n[yellow]Received shutdown signal, cleaning up...[/yellow]")
        if monitor.running:
            loop.create_task(monitor.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, signal_handler)

    try:
        loop.run_until_complete(monitor.start(use_tui=use_tui))
    except KeyboardInterrupt:
        console.print(
            "\n[yellow]Keyboard interrupt received, shutting down gracefully...[/yellow]"
        )
        loop.run_until_complete(monitor.stop())
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
```

- [ ] **Step 5: Update core/__init__.py with public API**

```python
"""Core orchestration: config, lifecycle, and monitor."""

from .config import Settings
from .lifecycle import run as run_monitor
from .monitor import Monitor

__all__ = ["Monitor", "Settings", "run_monitor"]
```

- [ ] **Step 6: Update importers**

```bash
grep -rln "from .config\|from .schemas\|from .activity_monitor\|ActivityMonitor" src/ tests/
```

Replace:
- `from .config import Settings` → `from .core import Settings` (top-level files) or `from ..core import Settings` (sub-package files)
- `from .activity_monitor import ActivityMonitor` → `from .core import Monitor`
- `ActivityMonitor(` → `Monitor(`
- `from .schemas import X` → `from .core.schemas import X`

Specific files to edit:
- `src/selfspy/cli.py`
- `src/selfspy/stats.py`
- `src/selfspy/enhanced_stats.py`
- `src/selfspy/terminal_stats.py`
- `src/selfspy/storage/store.py` (uses `Settings`)
- `src/selfspy/storage/encryption.py` (probably no Settings)
- `src/selfspy/tracking/terminal.py` (might use Settings)
- `src/selfspy/tui/runner.py` — created in Task 7 with `from ..activity_monitor import ActivityMonitor` and `monitor: "ActivityMonitor"`. After this task: change to `from ..core.monitor import Monitor` and `monitor: "Monitor"`.
- `tests/conftest.py` — `from selfspy.config import Settings` → `from selfspy.core import Settings`

- [ ] **Step 7: Reinstall and test**

```bash
uv sync --group dev --extra macos
uv run pytest 2>&1 | tail -10
uv run selfspy --help
```

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor: extract core layer (config, schemas); split monitor + lifecycle"
```

---

## Task 11: Extract pure analytics from stats / enhanced_stats / terminal_stats

These three files mix Typer commands, Rich rendering, and pure data analysis. Extract the data-only functions into `analytics/`. The remaining Typer/Rich code stays in the original files temporarily; Task 12 moves it into `cli/`.

**Files:**
- Create: `src/selfspy/analytics/{__init__,stats,viz,terminal}.py`
- Modify: `stats.py`, `enhanced_stats.py`, `terminal_stats.py`

- [ ] **Step 1: Create analytics package**

```bash
mkdir -p src/selfspy/analytics
touch src/selfspy/analytics/__init__.py
```

- [ ] **Step 2: Read stats.py and identify pure functions**

```bash
wc -l src/selfspy/stats.py
grep -n "^def \|^async def \|@app.command" src/selfspy/stats.py
```

Pure-data functions (return data, no I/O beyond DB, no Rich/Typer): things like `generate_stats`, `_aggregate_by_hour`, `_aggregate_by_process`, etc.

Presentation functions (use `console.print`, build Rich tables): keep in `stats.py` for now.

Typer commands (`@app.command`): keep in `stats.py` for now.

- [ ] **Step 3: Move pure functions to analytics/stats.py**

Create `src/selfspy/analytics/stats.py` with the pure-data functions copied verbatim from `src/selfspy/stats.py`. Update their internal imports to use `from ..storage import ...` etc.

Then in `src/selfspy/stats.py`, replace the moved function definitions with:

```python
from .analytics.stats import generate_stats, aggregate_by_hour, aggregate_by_process  # etc.
```

(adjust names to actual functions identified)

**Pattern example** — if `stats.py` has:

```python
async def generate_stats(settings: Settings, start_date, end_date, format):
    async with Store(settings).async_session() as session:
        # pure data work
        ...
    return data
```

Move that to `analytics/stats.py`. Keep its full body. In `stats.py` replace with the import.

- [ ] **Step 4: Repeat for enhanced_stats.py → analytics/viz.py**

Same pattern: identify pure-data functions in `enhanced_stats.py`, move to `analytics/viz.py`, leave Typer commands and Plotly figure-rendering helpers in `enhanced_stats.py`.

The Plotly `go.Figure(...)` building is a gray area — it's "pure" (no side effects) but tightly coupled to presentation. **Rule:** if it returns a `go.Figure` or HTML string, keep it in the CLI/presentation layer. If it returns a dataclass / dict / list, move it to analytics.

- [ ] **Step 5: Repeat for terminal_stats.py → analytics/terminal.py**

Same pattern.

- [ ] **Step 6: Add re-exports in analytics/__init__.py**

```python
"""Pure analytics: read from Store, return dataclasses/dicts. No I/O beyond DB."""

# Re-export the public surface of each module
from . import stats, terminal, viz

__all__ = ["stats", "terminal", "viz"]
```

- [ ] **Step 7: Reinstall and test**

```bash
uv sync --group dev --extra macos
uv run pytest 2>&1 | tail -10
uv run selfstats --help
uv run selfviz --help
uv run selfterminal --help
```

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor: extract pure analytics from stats/enhanced_stats/terminal_stats"
```

---

## Task 12: Build cli/ subpackage; move all Typer apps in

**Files:**
- Create: `src/selfspy/cli/{__init__,main,daemon,tui,stats,viz,terminal,permissions,migrate}.py`
- Delete: old `src/selfspy/cli.py`, `src/selfspy/stats.py`, `src/selfspy/enhanced_stats.py`, `src/selfspy/terminal_stats.py`

- [ ] **Step 1: Create cli package**

```bash
mkdir -p src/selfspy/cli
touch src/selfspy/cli/__init__.py
```

- [ ] **Step 2: Create cli/daemon.py**

Move the `start` command from old `src/selfspy/cli.py`, renamed to `daemon`:

```python
"""selfspy daemon — start headless tracking."""

from pathlib import Path

import typer
from rich.console import Console

from ..core import Monitor, Settings, run_monitor
from ..storage import Store, get_password
from ..tracking import check_and_request_permissions

app = typer.Typer(help="Headless activity tracking")
console = Console()


@app.callback(invoke_without_command=True)
def daemon(
    data_dir: Path = typer.Option(None, "--data-dir", "-d", help="Data directory"),
    no_text: bool = typer.Option(False, "--no-text", help="Don't store text"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
    force: bool = typer.Option(False, "--force", help="Skip permission checks"),
):
    """Start monitoring computer activity (headless)."""
    if not force and not check_and_request_permissions(console):
        console.print("[yellow]Exiting - permissions required[/yellow]")
        raise typer.Exit(1)

    settings = Settings(
        data_dir=data_dir if data_dir else Settings().data_dir,
        encryption_enabled=not no_text,
        debug=debug,
    )

    password = get_password() if settings.encryption_enabled else None
    store = Store(settings, password)
    monitor = Monitor(settings, store, debug)

    console.print("[green]Starting Selfspy monitor (daemon)...[/green]")
    run_monitor(monitor, use_tui=False)
```

- [ ] **Step 3: Create cli/tui.py**

```python
"""selfspy tui — start tracking with Textual TUI."""

from pathlib import Path

import typer
from rich.console import Console

from ..core import Monitor, Settings, run_monitor
from ..storage import Store, get_password
from ..tracking import check_and_request_permissions

app = typer.Typer(help="Interactive Textual TUI")
console = Console()


@app.callback(invoke_without_command=True)
def tui(
    data_dir: Path = typer.Option(None, "--data-dir", "-d", help="Data directory"),
    no_text: bool = typer.Option(False, "--no-text", help="Don't store text"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
    force: bool = typer.Option(False, "--force", help="Skip permission checks"),
):
    """Start monitoring with Textual TUI."""
    if not force and not check_and_request_permissions(console):
        raise typer.Exit(1)

    settings = Settings(
        data_dir=data_dir if data_dir else Settings().data_dir,
        encryption_enabled=not no_text,
        debug=debug,
    )

    password = get_password() if settings.encryption_enabled else None
    store = Store(settings, password)
    monitor = Monitor(settings, store, debug)

    run_monitor(monitor, use_tui=True)
```

- [ ] **Step 4: Move stats Typer app to cli/stats.py**

Take the `app = typer.Typer(...)` and `@app.command` definitions from old `src/selfspy/stats.py` (the presentation half — Rich rendering + Typer commands), put them in `src/selfspy/cli/stats.py`. The commands now import from `selfspy.analytics.stats` for the pure data functions.

- [ ] **Step 5: Move enhanced_stats Typer app to cli/viz.py**

Same pattern. Rich/Plotly rendering stays here; data functions are imported from `selfspy.analytics.viz`.

- [ ] **Step 6: Move terminal_stats Typer app to cli/terminal.py**

Same pattern.

- [ ] **Step 7: Move check-permissions to cli/permissions.py**

```python
"""selfspy check-permissions — verify macOS permissions."""

import typer
from rich.console import Console

from ..tracking.permissions import check_macos_permissions

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def check_permissions():
    """Check required macOS permissions."""
    has_perms, msg = check_macos_permissions()
    if has_perms:
        console.print(f"[green]✓ {msg}[/green]")
    else:
        console.print(f"[yellow]✗ {msg}[/yellow]")
        raise typer.Exit(1)
```

- [ ] **Step 8: Create cli/migrate.py**

```python
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

    # Find alembic.ini at repo root
    alembic_ini = Path(__file__).parent.parent.parent.parent / "alembic.ini"
    if not alembic_ini.exists():
        console.print(f"[red]alembic.ini not found at {alembic_ini}[/red]")
        raise typer.Exit(1)

    cmd = ["alembic", "-c", str(alembic_ini), "-x", f"dburl={db_url}", "upgrade", revision]
    console.print(f"[cyan]Running: {' '.join(cmd)}[/cyan]")
    result = subprocess.run(cmd)
    raise typer.Exit(result.returncode)
```

- [ ] **Step 9: Create cli/main.py — root app**

```python
"""selfspy — root CLI entry point."""

import sys
from typing import Optional

import typer
from rich.traceback import install

from . import daemon, migrate, permissions, stats, terminal, tui, viz

install(show_locals=True)

app = typer.Typer(
    help="Selfspy — monitor and analyze your computer activity",
    no_args_is_help=False,
    invoke_without_command=True,
)

app.add_typer(daemon.app, name="daemon", help="Start headless tracking")
app.add_typer(tui.app, name="tui", help="Start interactive TUI")
app.add_typer(stats.app, name="stats", help="Activity statistics")
app.add_typer(viz.app, name="viz", help="Enhanced visualizations")
app.add_typer(terminal.app, name="terminal", help="Terminal command analytics")
app.add_typer(permissions.app, name="check-permissions", help="Check macOS permissions")
app.add_typer(migrate.app, name="migrate", help="Database migrations")


@app.callback()
def main(ctx: typer.Context):
    """If invoked with no subcommand, run the daemon."""
    if ctx.invoked_subcommand is None:
        # Forward to daemon with default args
        daemon.daemon(data_dir=None, no_text=False, debug=False, force=False)


if __name__ == "__main__":
    app()
```

- [ ] **Step 10: Delete old top-level CLI files**

```bash
git rm src/selfspy/cli.py
git rm src/selfspy/stats.py
git rm src/selfspy/enhanced_stats.py
git rm src/selfspy/terminal_stats.py
```

- [ ] **Step 11: Update entrypoint and re-test**

In `pyproject.toml [project.scripts]`:

```toml
[project.scripts]
selfspy = "selfspy.cli.main:app"
```

(Remove `selfstats`, `selfviz`, `selfterminal`. They reappear in next task — no, they're permanently gone per spec. Final state: single entrypoint.)

- [ ] **Step 12: Reinstall and test**

```bash
uv sync --group dev --extra macos
uv run selfspy --help
uv run selfspy daemon --help
uv run selfspy tui --help
uv run selfspy stats --help
uv run selfspy viz --help
uv run selfspy terminal --help
uv run selfspy migrate --help
uv run selfspy check-permissions --help
uv run pytest 2>&1 | tail -10
```

Expected: all subcommands show help, tests pass.

- [ ] **Step 13: Commit**

```bash
git add -A
git commit -m "refactor: rebuild cli/ as thin subcommands; collapse selfstats/selfviz/selfterminal entrypoints"
```

---

## Task 13: Add unit tests for new module boundaries

**Files:**
- Create: `tests/storage/test_store.py`, `tests/storage/test_encryption.py`
- Create: `tests/analytics/test_stats.py`, `tests/analytics/test_terminal.py`
- Create: `tests/core/test_lifecycle.py`
- Create: `tests/tracking/test_permissions.py`

- [ ] **Step 1: Create test directory structure**

```bash
mkdir -p tests/storage tests/analytics tests/core tests/tracking
touch tests/storage/__init__.py tests/analytics/__init__.py tests/core/__init__.py tests/tracking/__init__.py
```

- [ ] **Step 2: Write test for storage.encryption (PBKDF2 cipher)**

Create `tests/storage/test_encryption.py`:

```python
"""Tests for storage.encryption."""

from pathlib import Path

import pytest

from selfspy.storage.encryption import create_cipher, check_password


def test_create_cipher_returns_none_for_empty_password(tmp_path):
    assert create_cipher("", tmp_path) is None
    assert create_cipher(None, tmp_path) is None


def test_create_cipher_creates_salt_file(tmp_path):
    cipher = create_cipher("secret", tmp_path)
    assert cipher is not None
    assert (tmp_path / "encryption.salt").exists()


def test_create_cipher_reuses_existing_salt(tmp_path):
    cipher1 = create_cipher("secret", tmp_path)
    salt_first = (tmp_path / "encryption.salt").read_bytes()
    cipher2 = create_cipher("secret", tmp_path)
    salt_second = (tmp_path / "encryption.salt").read_bytes()
    assert salt_first == salt_second
    # Same password + same salt should produce same Fernet key
    token = cipher1.encrypt(b"hello")
    assert cipher2.decrypt(token) == b"hello"


@pytest.mark.asyncio
async def test_check_password_creates_digest_on_first_call(tmp_path):
    cipher = create_cipher("secret", tmp_path)
    result = await check_password(tmp_path, cipher, read_only=False)
    assert result is True
    assert (tmp_path / "password.digest").exists()


@pytest.mark.asyncio
async def test_check_password_validates_correct_password(tmp_path):
    cipher = create_cipher("secret", tmp_path)
    await check_password(tmp_path, cipher, read_only=False)
    # Second call with same cipher should validate
    cipher2 = create_cipher("secret", tmp_path)
    assert await check_password(tmp_path, cipher2, read_only=False) is True


@pytest.mark.asyncio
async def test_check_password_rejects_wrong_password(tmp_path):
    cipher = create_cipher("secret", tmp_path)
    await check_password(tmp_path, cipher, read_only=False)
    wrong_cipher = create_cipher("wrong", tmp_path)
    assert await check_password(tmp_path, wrong_cipher, read_only=False) is False
```

- [ ] **Step 3: Run encryption tests to verify they fail (initially) or pass**

```bash
uv run pytest tests/storage/test_encryption.py -v
```

Expected: tests pass (the encryption code already exists and is correct).

- [ ] **Step 4: Write test for storage.store (Store CRUD)**

Create `tests/storage/test_store.py`:

```python
"""Tests for storage.Store."""

import pytest

from selfspy.core import Settings
from selfspy.storage import Store


@pytest.fixture
async def store(tmp_path):
    settings = Settings(data_dir=tmp_path, encryption_enabled=False)
    store = Store(settings, password=None)
    await store.initialize()
    yield store
    await store.close()


@pytest.mark.asyncio
async def test_store_initialize_creates_schema(store):
    # initialize() ran in fixture; verify a session can be opened
    async with store.async_session() as session:
        assert session is not None


@pytest.mark.asyncio
async def test_store_start_session_returns_id(store):
    session_id = await store.start_session()
    assert isinstance(session_id, int)
    assert session_id > 0


@pytest.mark.asyncio
async def test_store_update_window_info_creates_process_and_window(store):
    await store.start_session()
    await store.update_window_info("Terminal", "bash - ~", "com.apple.Terminal")
    assert store.current_process_id is not None
    assert store.current_window_id is not None


@pytest.mark.asyncio
async def test_store_store_keys_requires_window(store):
    await store.start_session()
    # No window set yet; should silently no-op
    await store.store_keys("hello")
    # No exception raised


@pytest.mark.asyncio
async def test_store_store_keys_writes_after_window_set(store):
    from selfspy.storage import Keys
    from sqlalchemy import select

    await store.start_session()
    await store.update_window_info("Terminal", "bash - ~", "com.apple.Terminal")
    await store.store_keys("hello")

    async with store.async_session() as session:
        result = await session.execute(select(Keys))
        keys = result.scalars().all()
        assert len(keys) == 1
        assert keys[0].count == 5
```

- [ ] **Step 5: Run store tests**

```bash
uv run pytest tests/storage/test_store.py -v
```

Expected: pass.

- [ ] **Step 6: Write test for tracking.permissions**

Create `tests/tracking/test_permissions.py`:

```python
"""Tests for tracking.permissions."""

import platform

from selfspy.tracking.permissions import check_macos_permissions


def test_check_macos_permissions_on_non_macos():
    if platform.system() == "Darwin":
        # Skip on macOS — the result depends on system state
        return
    has_perms, msg = check_macos_permissions()
    assert has_perms is True
    assert "Not on macOS" in msg
```

- [ ] **Step 7: Write smoke test for analytics.stats (pure-data API)**

Create `tests/analytics/test_stats.py`:

```python
"""Tests for analytics.stats."""

import pytest

from selfspy.analytics import stats as analytics_stats
from selfspy.core import Settings
from selfspy.storage import Store


@pytest.fixture
async def populated_store(tmp_path):
    settings = Settings(data_dir=tmp_path, encryption_enabled=False)
    store = Store(settings, password=None)
    await store.initialize()
    await store.start_session()
    await store.update_window_info("Terminal", "bash - ~", "com.apple.Terminal")
    await store.store_keys("hello world")
    await store.store_click(1, 100, 200)
    yield store
    await store.close()


@pytest.mark.asyncio
async def test_generate_stats_returns_data(populated_store):
    """Whatever the analytics public API is, calling it with a populated store returns data."""
    # NOTE: adjust function name to whatever was extracted in Task 11.
    # If `analytics.stats` exposes `generate_stats(settings)`, call it.
    # If it exposes `aggregate_by_process(store)`, call that.
    # The test asserts the function exists and returns a non-empty result.
    funcs = [name for name in dir(analytics_stats) if not name.startswith("_") and callable(getattr(analytics_stats, name))]
    assert len(funcs) > 0, "analytics.stats should expose at least one function"
```

This is a deliberately minimal sanity test — extend it to call the actual public functions identified during Task 11.

- [ ] **Step 8: Run all new tests**

```bash
uv run pytest tests/storage tests/analytics tests/tracking -v
```

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "test: add unit tests for storage, analytics, and tracking modules"
```

---

## Task 14: Add monitor → DB smoke test

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_smoke.py`

- [ ] **Step 1: Create integration tests directory**

```bash
mkdir -p tests/integration
touch tests/integration/__init__.py
```

- [ ] **Step 2: Write smoke test**

Create `tests/integration/test_smoke.py`:

```python
"""Smoke test: simulate input events and verify they reach the DB."""

import asyncio
from datetime import datetime

import pytest
from sqlalchemy import select

from selfspy.core import Monitor, Settings
from selfspy.storage import Click, Keys, Store


@pytest.mark.asyncio
async def test_buffer_flushes_keys_to_db(tmp_path):
    """Pushing keys onto the monitor's buffer results in DB writes after flush."""
    settings = Settings(
        data_dir=tmp_path,
        encryption_enabled=False,
        keystroke_buffer_timeout=0,  # force immediate flush
    )
    store = Store(settings, password=None)
    await store.initialize()
    await store.start_session()
    await store.update_window_info("Test", "Test Window", "")

    monitor = Monitor(settings, store, debug=True)
    monitor._loop = asyncio.get_running_loop()

    # Inject events directly (bypass pynput thread)
    monitor.buffer.put_nowait({"type": "key", "key": "h", "time": datetime.now()})
    monitor.buffer.put_nowait({"type": "key", "key": "i", "time": datetime.now()})

    await monitor._flush_buffer(force=True)

    async with store.async_session() as session:
        result = await session.execute(select(Keys))
        keys = result.scalars().all()
        assert len(keys) >= 1
        total_count = sum(k.count for k in keys)
        assert total_count == 2

    await store.close()


@pytest.mark.asyncio
async def test_buffer_flushes_clicks_to_db(tmp_path):
    settings = Settings(
        data_dir=tmp_path,
        encryption_enabled=False,
        keystroke_buffer_timeout=0,
    )
    store = Store(settings, password=None)
    await store.initialize()
    await store.start_session()
    await store.update_window_info("Test", "Test Window", "")

    monitor = Monitor(settings, store, debug=True)
    monitor._loop = asyncio.get_running_loop()

    monitor.buffer.put_nowait({
        "type": "click", "button": 1, "x": 50, "y": 75, "time": datetime.now()
    })

    await monitor._flush_buffer(force=True)

    async with store.async_session() as session:
        result = await session.execute(select(Click))
        clicks = result.scalars().all()
        assert len(clicks) == 1
        assert clicks[0].x == 50
        assert clicks[0].y == 75

    await store.close()
```

- [ ] **Step 3: Run smoke test**

```bash
uv run pytest tests/integration/test_smoke.py -v
```

Expected: both tests pass.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "test: add monitor → DB smoke tests"
```

---

## Task 15: Update CLAUDE.md, README.md, and docs/

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `docs/architecture.md`, `docs/installation.md`, `docs/usage.md`

- [ ] **Step 1: Update CLAUDE.md package structure section**

Edit `CLAUDE.md`:
- Replace the "Package Management" commands to remove pip mentions
- Update the "Architecture > Core Components" section: replace the old src/ paths with `src/selfspy/<subpackage>/<module>.py`
- Update the CLI section: only `selfspy` exists with subcommands `daemon`, `tui`, `stats`, `viz`, `terminal`, `migrate`, `check-permissions`
- Update the testing section: tests now import from `selfspy.X` not `src.X`
- Add a "Layer rules" subsection summarizing the analytics-purity rule

- [ ] **Step 2: Update README.md install instructions**

In `README.md`, replace any `pip install -r requirements.txt` references with `uv sync --group dev --extra macos`. Replace `selfspy start` with `selfspy` (or `selfspy daemon`).

- [ ] **Step 3: Update docs/installation.md, docs/usage.md, docs/architecture.md**

```bash
grep -rln "selfstats\|selfviz\|selfterminal\|selfspy start\|requirements\.txt\|src\." docs/
```

For each match:
- `selfstats X` → `selfspy stats X`
- `selfviz X` → `selfspy viz X`
- `selfterminal X` → `selfspy terminal X`
- `selfspy start` → `selfspy daemon` (or `selfspy tui`)
- `pip install -r requirements.txt` → `uv sync --group dev --extra macos`
- `src.` Python paths → `selfspy.`

- [ ] **Step 4: Verify docs references match reality**

```bash
grep -rn "selfstats\|selfviz\|selfterminal" docs/ README.md CLAUDE.md
```

Expected: no matches.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "docs: update CLAUDE.md, README, and docs/ for new package layout and CLI"
```

---

## Task 16: Add pre-commit and CI workflow

**Files:**
- Create: `.pre-commit-config.yaml`
- Create: `.github/workflows/ci.yml`
- Modify: `.github/workflows/publish.yml` (if it references old paths)

- [ ] **Step 1: Create pre-commit config**

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

- [ ] **Step 2: Install and test pre-commit**

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Expected: hooks run, may auto-fix some files. Stage and continue.

- [ ] **Step 3: Create CI workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ["3.12", "3.13"]

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Install deps (Linux)
        if: runner.os == 'Linux'
        run: uv sync --group dev

      - name: Install deps (macOS)
        if: runner.os == 'macOS'
        run: uv sync --group dev --extra macos

      - name: Lint
        run: uv run ruff check src/ tests/

      - name: Format check
        run: uv run ruff format --check src/ tests/

      - name: Type check
        run: uv run mypy src/

      - name: Test
        run: uv run pytest -m "not macos or runner.os == 'macOS'"
```

- [ ] **Step 4: Add pytest marker for macOS-only tests**

In `pyproject.toml [tool.pytest.ini_options]` add:

```toml
markers = [
    "macos: tests that require macOS (skipped on other platforms)",
]
```

- [ ] **Step 5: Verify CI workflow syntax locally**

```bash
uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

Expected: no errors.

- [ ] **Step 6: Verify pre-commit hooks pass**

```bash
uv run pre-commit run --all-files
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: add pre-commit hooks and CI workflow"
```

---

## Task 17: Final verification and merge

**Files:**
- No edits

- [ ] **Step 1: Run full verification**

```bash
uv sync --group dev --extra macos
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest -v
```

Expected: all green.

- [ ] **Step 2: Smoke-test all CLI commands**

```bash
uv run selfspy --help
uv run selfspy daemon --help
uv run selfspy tui --help
uv run selfspy stats --help
uv run selfspy viz --help
uv run selfspy terminal --help
uv run selfspy migrate --help
uv run selfspy check-permissions --help
```

Expected: all show help cleanly.

- [ ] **Step 3: End-to-end migration test**

```bash
rm -rf /tmp/selfspy-e2e
mkdir /tmp/selfspy-e2e
uv run selfspy migrate --data-dir /tmp/selfspy-e2e
ls /tmp/selfspy-e2e/
```

Expected: `selfspy.db` created with all tables.

- [ ] **Step 4: Brief manual run of daemon (optional, requires permissions)**

On macOS with permissions granted:

```bash
timeout 10 uv run selfspy daemon --data-dir /tmp/selfspy-e2e --no-text
```

Expected: starts, captures events for 10 seconds, exits cleanly. Inspect DB:

```bash
uv run python -c "
from selfspy.core import Settings
from selfspy.storage import Store
import asyncio

async def main():
    s = Store(Settings(data_dir='/tmp/selfspy-e2e', encryption_enabled=False))
    await s.initialize()
    from sqlalchemy import select
    from selfspy.storage import Click, Keys, Session
    async with s.async_session() as sess:
        sessions = (await sess.execute(select(Session))).scalars().all()
        print(f'sessions: {len(sessions)}')

asyncio.run(main())
"
```

Expected: at least one session row.

- [ ] **Step 5: Verify desktop-app/ status**

```bash
grep -rn "from src\.\|sys.path.*src" desktop-app/
```

Expected: matches will exist (this is deferred to Phase 3). Document the breakage in `desktop-app/README.md` with a note: "Phase 3 will modernize these widgets to import from `selfspy.*`. They are temporarily broken after the Phase 1 refactor."

```bash
cat >> desktop-app/README.md <<'EOF'

## Phase 1 Refactor Note

After the Phase 1 package refactor (`src/` → `src/selfspy/`), these widgets
import paths are broken. They will be modernized in Phase 3 to import directly
from the `selfspy` package. Until then, do not run them against a Phase 1+ tree.
EOF
git add desktop-app/README.md
git commit -m "docs: flag desktop-app/ as deferred to Phase 3"
```

- [ ] **Step 6: Review the branch log**

```bash
git log main..HEAD --oneline
```

Expected: 17-18 atomic commits matching the plan tasks.

- [ ] **Step 7: Merge to main**

```bash
cd /Users/nuin/Projects/selfspy-python
git checkout main
git merge --no-ff revamp/phase-1-foundation -m "Merge phase 1: foundation cleanup + architecture refactor"
git worktree remove ../selfspy-revamp
git branch -d revamp/phase-1-foundation
```

Expected: clean merge commit on main, worktree removed, branch deleted.

- [ ] **Step 8: Final sanity check on main**

```bash
uv sync --group dev --extra macos
uv run pytest
uv run selfspy --help
```

Expected: all green. Phase 1 complete.

---

## Success Criteria Checklist

- [ ] Single lockfile: only `uv.lock` (no `poetry.lock`, no `requirements*.txt`)
- [ ] `src/selfspy/` proper package; all imports use `from selfspy.X import Y`
- [ ] Six subpackages (`core`, `tracking`, `storage`, `analytics`, `cli`, `tui`) with documented layer boundaries
- [ ] Single `selfspy` console script; `selfstats`/`selfviz`/`selfterminal` removed
- [ ] Alembic baseline regenerated; `selfspy migrate` works on empty data dir
- [ ] `pytest`, `ruff check`, `ruff format --check`, `mypy src/` all clean
- [ ] New unit tests cover storage, analytics, tracking modules
- [ ] CLAUDE.md, README.md, docs/ reflect the new layout
- [ ] CI matrix passes on macOS + Linux, Python 3.12 + 3.13
