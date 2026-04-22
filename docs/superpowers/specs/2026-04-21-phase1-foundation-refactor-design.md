# Phase 1: Foundation Cleanup & Architecture Refactor

**Date:** 2026-04-21
**Status:** Approved (pending user review of this written spec)
**Phase:** 1 of 3 (Phase 2 = TUI-first rewrite, Phase 3 = desktop widgets modernization)

## Goal

Combine repo cleanup, uv migration completion, Python version bump, and a full architecture refactor into a single phase. Establish clean module boundaries that the Phase 2 TUI rewrite can build on. No feature changes — same surface, better structure.

## Non-Goals

- TUI redesign (Phase 2)
- New analytics features (Phase 2)
- Desktop widget modernization (Phase 3)
- Backwards compatibility for old CLI entrypoints, old DB schemas in place, or old config keys (user explicitly chose "break freely")

## Constraints / Decisions

| Decision | Choice |
|---|---|
| Python floor | 3.12 |
| Layout | `src/selfspy/` (proper package) |
| Subpackages | 6: `core`, `tracking`, `storage`, `analytics`, `cli`, `tui` |
| CLI | Single `selfspy` console script with subcommands |
| Bare `selfspy` | Launches daemon (matches old `selfspy start`) |
| Old entrypoints (`selfstats`, `selfviz`, `selfterminal`) | Deleted entirely |
| Alembic | Drop, regenerate baseline migration from current models |
| Tests | Refactor + write unit tests for each new module |
| Tooling | `ruff` (lint+format), `mypy --strict`, `uv` only — no black/isort/pip |
| Workflow | Git worktree, small atomic commits |
| `desktop-app/` | Leave at repo root for this phase, defer modernization to Phase 3 |

## Section A — Cleanup

**Delete:**
- `poetry.lock` (uv only)
- `requirements.txt`, `requirements-dev.txt`, `requirements-macos.txt`
- `install.py`, `MANIFEST.in` (hatchling handles packaging)
- `dist/` (build artifacts)
- `.coverage` (gitignore)
- `pytest.ini` (folded into `pyproject.toml`)
- `src/selfviz.py` (9-line dead stub)
- `alembic/` directory (regenerated)

**`.gitignore` additions:**
- `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.coverage`, `htmlcov/`, `dist/`, `build/`, `*.egg-info/`

**`pyproject.toml` consolidation:**
- Remove `black`, `isort` from dev deps
- Use `ruff` for both lint and format
- `mypy` strict mode with per-module overrides for PyObjC/pynput
- `pytest-asyncio` mode = `auto`
- `[tool.coverage.run] source = ["src/selfspy"]`
- All config inline — no separate `.cfg`/`.ini` files

## Section B — Package Layout

```
src/selfspy/
├── __init__.py                  # version, public API
│
├── core/                        # orchestration, config, lifecycle
│   ├── __init__.py
│   ├── config.py                # ← src/config.py
│   ├── schemas.py               # ← src/schemas.py
│   ├── monitor.py               # ← orchestration half of activity_monitor.py
│   └── lifecycle.py             # ← signal/start/stop half of activity_monitor.py
│
├── tracking/                    # capturing input/window/terminal events
│   ├── __init__.py
│   ├── permissions.py           # ← src/permissions.py
│   ├── terminal.py              # ← src/terminal_tracker.py
│   └── platform/
│       ├── __init__.py
│       ├── base.py
│       ├── darwin.py
│       ├── fallback.py
│       ├── input_tracker.py
│       └── screen_capture.py
│
├── storage/                     # persistence, encryption, secrets
│   ├── __init__.py
│   ├── models.py                # ← src/models.py
│   ├── store.py                 # ← src/activity_store.py (ActivityStore → Store)
│   ├── encryption.py            # ← src/encryption.py
│   └── password.py              # ← merge of check_password.py + password_dialog.py
│
├── analytics/                   # PURE functions: take Store, return dataclasses/dicts
│   ├── __init__.py              # No Rich, no Plotly, no Typer in here
│   ├── stats.py                 # ← analysis funcs from src/stats.py
│   ├── viz.py                   # ← analysis funcs from src/enhanced_stats.py
│   └── terminal.py              # ← analysis funcs from src/terminal_stats.py
│
├── cli/                         # Typer subcommands — thin presentation layer
│   ├── __init__.py
│   ├── main.py                  # `selfspy` root, registers subcommands, default→daemon
│   ├── daemon.py                # `selfspy daemon`
│   ├── tui.py                   # `selfspy tui`
│   ├── stats.py                 # `selfspy stats`
│   ├── viz.py                   # `selfspy viz`
│   ├── terminal.py              # `selfspy terminal`
│   ├── permissions.py           # `selfspy check-permissions`
│   └── migrate.py               # `selfspy migrate`
│
├── tui/                         # Textual UI (already isolated)
│   ├── __init__.py
│   ├── app.py
│   ├── runner.py                # ← _run_with_tui logic moved out of monitor.py
│   ├── tabs/{live,apps,summary}.py
│   └── widgets/sparkline.py
│
└── alembic/                     # regenerated baseline + env
    ├── env.py
    ├── script.py.mako
    └── versions/
        └── <baseline>_initial_schema.py
```

**Layer rules (enforced by review, not tooling):**

1. `analytics/` is pure — takes a `Store` instance, returns dataclasses/dicts. No I/O beyond what `Store` does. No `rich.print`, no `plotly`, no `typer`.
2. `cli/` modules are thin: parse args → call `analytics/` → render with Rich/Plotly. This is the seam Phase 2 uses to call the same `analytics/` functions from the TUI.
3. `core/monitor.py` orchestrates `tracking/` + `storage/`: constructs the Store, instantiates platform trackers, owns the input event queue and the buffer-flush logic. It exposes async methods (`start`, `stop`, `flush`) but does **not** own the asyncio loop entry. `core/lifecycle.py` owns the asyncio entry point: it constructs a `Monitor`, installs signal handlers (SIGINT/SIGTERM → graceful shutdown), runs `asyncio.run(...)`, and is the function `cli/daemon.py` and `cli/tui.py` both call.
4. `tui/runner.py` contains the `_run_with_tui` logic currently embedded in `activity_monitor.py:375-450`. `cli/tui.py` is the entrypoint that constructs a `Monitor` + calls `runner.run(monitor)`.
5. `desktop-app/` stays at repo root **for this phase only**. Its `sys.path.append` will need updating once `src/` becomes `src/selfspy/`. We document this break and defer the proper fix to Phase 3.

## Section C — CLI Surface

Single console script `selfspy` in `[project.scripts]`:

```
selfspy                          → launches daemon (default action)
selfspy daemon [--debug]         → headless tracking
selfspy tui                      → Textual TUI (tracks + interactive view)
selfspy check-permissions        → macOS permissions check
selfspy stats [--days N]         → basic stats (was: selfstats)
selfspy stats keys
selfspy stats clicks
selfspy viz                      → Plotly HTML output (was: selfviz enhanced)
selfspy terminal stats           → terminal command analytics (was: selfterminal stats)
selfspy terminal commands
selfspy migrate                  → alembic upgrade head
selfspy migrate --revision <id>
selfspy version
```

**Removed entrypoints:**
- `selfstats`, `selfviz`, `selfterminal` deleted from `pyproject.toml [project.scripts]`
- `selfspy start` → `selfspy daemon`

## Section D — Tooling

**`pyproject.toml`:**
- `requires-python = ">=3.12"`
- Drop `black`, `isort` from dev deps
- `[tool.ruff]` with sensible rule sets: `E`, `F`, `I`, `UP`, `B`, `SIM`, `RUF`
- `[tool.mypy] strict = true` with per-module `ignore_errors` overrides for PyObjC/pynput
- `[tool.pytest.ini_options]` absorbs `pytest.ini`; `asyncio_mode = "auto"`
- `[tool.coverage.run] source = ["src/selfspy"]`

**Dev commands (post-refactor):**
```
uv sync --group dev --extra macos
uv run selfspy daemon
uv run pytest
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run mypy src/
```

**Pre-commit (`.pre-commit-config.yaml`):**
- `ruff` (lint + format)
- `mypy` (optional)
- standard hooks: `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`

**CI (`.github/workflows/`):**
- Matrix: Python 3.12 + 3.13, macOS + Linux
- Steps: `uv sync` → `ruff check` → `ruff format --check` → `mypy` → `pytest`
- Cache uv deps via `actions/cache`

## Section E — Migration Approach

**Worktree:**
```
git worktree add ../selfspy-revamp -b revamp/phase-1-foundation
cd ../selfspy-revamp
```

**Commit sequence** (each leaves project in working state — tests + ruff + mypy green):

1. `chore: delete poetry.lock, requirements*.txt, install.py, MANIFEST.in, dist/`
2. `chore: tighten .gitignore`
3. `chore: fold pytest.ini into pyproject.toml`
4. `chore: bump python floor to 3.12`
5. `chore: switch from black/isort to ruff format, configure ruff rules`
6. `chore: enable mypy strict mode with PyObjC/pynput overrides`
7. `refactor: move src/* into src/selfspy/* (rename only, no logic changes)`
   - Update all imports
   - `[tool.hatch.build.targets.wheel] packages = ["src/selfspy"]`
   - Update `pythonpath` and coverage source
   - Verify: tests pass, `uv run selfspy start` still works
8. `refactor: drop alembic/, regenerate baseline migration`
9. `refactor: split storage layer (models, store, encryption, password)` → `selfspy/storage/`
10. `refactor: extract tracking layer (permissions, terminal, platform/)` → `selfspy/tracking/`
11. `refactor: extract core layer (config, schemas), split monitor → monitor + lifecycle` → `selfspy/core/`
12. `refactor: extract pure analytics from stats/enhanced_stats/terminal_stats` → `selfspy/analytics/`
13. `refactor: rebuild cli/ as thin subcommands calling analytics + core` → `selfspy/cli/`
14. `refactor: move TUI runner from monitor.py into selfspy/tui/runner.py`
15. `chore: collapse selfstats/selfviz/selfterminal entrypoints into single selfspy CLI`
16. `test: add unit tests for new module boundaries (analytics/, storage/, tracking/)`
17. `chore: update CLAUDE.md, README.md, docs/ for new layout`
18. `chore: update pre-commit and CI for new structure`

**Test gates per commit:**
- `uv run pytest` passes
- `uv run ruff check` clean
- `uv run mypy src/` clean (or warnings strictly decreasing)

**Verification before merge:**
- Smoke: `selfspy daemon` runs, captures events, writes to DB
- Smoke: `selfspy stats` reads them back
- Smoke: `selfspy tui` launches and shows live data
- Smoke: `selfspy check-permissions` works on macOS
- Migration: empty data dir → `selfspy migrate` creates schema cleanly
- `desktop-app/` widgets either still launch with updated `sys.path` or have a documented breakage flagged for Phase 3

**Risks & mitigations:**

| Risk | Mitigation |
|---|---|
| Stdlib `platform` shadowed by `selfspy.tracking.platform` | Safe within the package (qualified imports). Revisit `desktop-app/sys.path` in commit 7. |
| Alembic regeneration breaks existing user DBs | Documented break. Ship `selfspy migrate --bootstrap` for fresh-init. Tell users to export with `selfspy stats --export` before upgrading. |
| PyObjC import failures in Linux CI | Keep `extra = "macos"` gated. Mark macOS-only tests with `@pytest.mark.macos`, skip on Linux. |
| Subtle TUI integration regressions during refactor | Smoke characterization test: spawn `selfspy daemon` with a fake input source, assert N events land in DB. Run before merge. |
| Worktree drift from `main` if Phase 1 takes weeks | Rebase the branch periodically. Phase 1 should land within a few sittings. |

**Merge:** Once all commits land in `revamp/phase-1-foundation` and verification passes, merge to `main` (squash or merge commit — author's choice) and delete the worktree.

## Out of Scope (Future Phases)

- **Phase 2 — TUI-first rewrite:** new tab structure, richer widgets, theming, fold all analytics views into TUI tabs. CLI subcommands remain for scripting/headless use.
- **Phase 3 — Desktop widgets modernization:** consolidate `desktop-app/` variants, move under `src/selfspy/desktop/`, import from new package layout properly.

## Success Criteria

1. Single lockfile (`uv.lock`), no `requirements*.txt`, no `poetry.lock`.
2. `src/selfspy/` proper package; all imports use `from selfspy.X import Y`.
3. Six subpackages with documented layer boundaries.
4. Single `selfspy` console script; old entrypoints removed.
5. Alembic baseline regenerated; `selfspy migrate` works on empty data dir.
6. `pytest`, `ruff check`, `ruff format --check`, `mypy src/` all clean.
7. New unit tests cover each new analytics/storage/tracking module.
8. CLAUDE.md, README.md, docs/ reflect new layout.
9. CI matrix passes on macOS + Linux, Python 3.12 + 3.13.
