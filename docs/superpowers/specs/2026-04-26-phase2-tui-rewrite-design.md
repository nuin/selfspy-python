# Phase 2 — TUI-First Rewrite & Analytics Consolidation

**Status:** Design (awaiting implementation plan)
**Worktree:** `../selfspy-revamp` on branch `revamp/phase-2-tui`
**Predecessor:** `docs/superpowers/specs/2026-04-21-phase1-foundation-refactor-design.md` (merged)

---

## 1. Goal & Scope

Make the Textual TUI the primary interface for selfspy. Fold every analytics view that currently lives only in CLI subcommands (heatmap, timeline, terminal commands/sessions, insights/productivity) into the TUI as proper tabs, add comparative trends and a per-app deep-dive, and introduce theming. CLI subcommands stay as-is for headless and scripted use; the TUI just stops being the second-class surface.

**In scope**

- New TUI tabs: Heatmap, Timeline, Terminal, AppDetail (modal).
- Existing tabs (Live, Apps, Summary) updated to share a global time-window control and theme.
- Time-window navigation: Today / Yesterday / Last 7 days / Last 30 days. Live tab stays today-scoped (real-time).
- Comparative trends (this period vs the previous equivalent period).
- Per-app drill-in modal (Enter on an Apps row).
- Multiple selectable themes applied uniformly across all tabs.
- Shared analytics layer (`analytics/` package) that both the TUI and CLI subcommands consume.
- TTL + write-through cache for query results.

**Out of scope**

- Database schema changes. Phase 2 reads from the Phase 1 schema unchanged. Any aggregate that needs persistence is computed on demand.
- Web UI, packaging changes, new platform support, encryption changes.
- Replacing or removing CLI subcommands.

---

## 2. Architecture

### 2.1 Module layout

New and changed modules (everything under `src/selfspy/`):

```
analytics/
    __init__.py
    windows.py        # TimeWindow enum + date_range/previous_period helpers
    queries.py        # Typed query functions returning frozen dataclasses
    cache.py          # TTLCache with optional callback-based invalidation
tui/
    app.py            # SelfspyApp (existing) — wires global state + theme
    state.py          # Reactive globals: TimeWindow, ThemeName, persistence
    runner.py         # (existing)
    themes/
        default.tcss
        dark.tcss
        solarized.tcss
        dracula.tcss
    widgets/
        sparkline.py  # (existing)
        heatmap.py    # 7×24 grid widget
        timeline.py   # daily totals bar/line widget
        delta_badge.py# "+12% vs prev" pill
    tabs/
        live.py       # (existing) — stays today-scoped
        apps.py       # (existing) — adds Enter→AppDetail drill-in
        summary.py    # (existing) — adopts global TimeWindow
        heatmap.py    # new
        timeline.py   # new
        terminal.py   # new
        app_detail.py # new (ModalScreen)
```

### 2.2 Invariants

1. **Single source of truth for analytics.** Every aggregate (counts, totals, buckets, deltas) is computed by a function in `analytics/queries.py`. CLI subcommands and TUI tabs both call those functions. No tab queries the ORM directly.
2. **TimeWindow flows through reactive state.** `tui/state.py` owns the current `TimeWindow`. Tabs subscribe; changing it via key binding (`1`/`2`/`3`/`4`) re-renders every applicable tab.
3. **Theming is pure CSS.** Switching themes calls `app.stylesheet.set_paths(...)` followed by `app.refresh_css()`. No Python-side conditionals on theme name in tabs or widgets.
4. **Live tab is today-scoped.** It always shows today's totals + the live event stream and ignores the global TimeWindow. This is intentional: "what am I doing right now" is a different question from "show me the last 7 days".
5. **No schema changes.** All Phase 2 work reads from the Phase 1 schema. If a query is too slow, optimize the query (indexes already exist) or the cache, not the schema.

---

## 3. Tab Inventory & Screens

Global chrome on every screen:

```
selfspy  [Today | Yesterday | 7d | 30d]                  theme: default   ?
```

Key bindings (app-wide):

- `1`/`2`/`3`/`4` → switch TimeWindow
- `T` → cycle theme
- `Enter` → drill-in (where applicable, e.g. Apps row → AppDetail modal)
- `q` → quit
- `?` → help overlay

### 3.1 Live (today-scoped)

Today's totals on top, live event sparkline + recent events below. Window toggle is visible but greyed/inactive on this tab.

```
┌─ Live (today) ────────────────────────────────────────────────┐
│ Keys: 12,438   Clicks: 2,107   Active: 4h12m   Apps: 14       │
│ ─── keystrokes (last 60 min) ──────────────────────────────── │
│ ▂▃▅▇█▇▅▃▂▁▂▃▅▇█▇▅▃▂▁▂▃▅▇                                     │
│ ─── recent events ─────────────────────────────────────────── │
│ 14:02:01  app=Code         window="phase2.md"                 │
│ ...                                                           │
└───────────────────────────────────────────────────────────────┘
```

### 3.2 Apps

Sortable table of app totals for the current TimeWindow with delta vs previous period.

```
┌─ Apps (last 7 days) ──────────────────────────────────────────┐
│ App           Keys     Clicks   Focus    Δ vs prev            │
│ ─────────────────────────────────────────────────────────────│
│ Code         84,210    9,322    18h04m   +12%   ▲             │
│ Slack        12,008    4,109     6h22m    -8%   ▼             │
│ ...                                                           │
│ [Enter] open detail   [↑/↓] navigate                          │
└───────────────────────────────────────────────────────────────┘
```

### 3.3 AppDetail (ModalScreen)

Pushed from Apps via `Enter`. Same TimeWindow as the rest of the app.

```
┌─ Code — last 7 days ──────────────────────────── [Esc] close ─┐
│ Keys 84,210  Clicks 9,322  Focus 18h04m   +12% vs prev ▲      │
│ ─── activity by hour ──────────────────────────────────────── │
│ ▁▁▁▂▃▅▇█▇▅▃▂▁                                                 │
│ ─── top windows ──────────────────────────────────────────── │
│ phase2.md                12,440 keys                          │
│ activity_monitor.py       9,108 keys                          │
│ ...                                                           │
└───────────────────────────────────────────────────────────────┘
```

### 3.4 Summary

Multi-metric overview for the TimeWindow. Shows totals (keys, clicks, active/idle hours, distinct apps) with delta badges vs the previous equivalent period, plus insights (productivity score, peak hour, longest focus streak). The existing Summary tab is updated rather than rewritten.

### 3.5 Heatmap

Hour-of-day × day-of-week intensity grid, scoped to the TimeWindow.

```
┌─ Heatmap (last 30 days) ──────────────────────────────────────┐
│       00 02 04 06 08 10 12 14 16 18 20 22                     │
│ Mon   ·  ·  ·  ·  ▂  ▅  ▇  █  █  ▅  ▂  ·                     │
│ Tue   ·  ·  ·  ·  ▃  ▆  ▇  █  ▇  ▅  ▂  ·                     │
│ ...                                                           │
└───────────────────────────────────────────────────────────────┘
```

### 3.6 Timeline

Daily totals (bar/line) across the TimeWindow with comparative overlay.

```
┌─ Timeline (last 30 days) ─────────────────────────────────────┐
│ Keys per day                                                  │
│ █▇▅▃▂▃▅▇█▇▅▃ ...                                              │
│ Avg 14,201/day   ↑ 9% vs prev 30d                             │
└───────────────────────────────────────────────────────────────┘
```

### 3.7 Terminal

Folds `selfterminal commands` and `selfterminal sessions` into one tab with sub-views (toggle inside the tab).

```
┌─ Terminal (last 7 days) ──────────────────────────────────────┐
│ [Commands | Sessions]                                         │
│ Command          Count   Last seen     Project                │
│ git status         412   2026-04-26    selfspy-python         │
│ pytest             198   2026-04-26    selfspy-python         │
│ ...                                                           │
└───────────────────────────────────────────────────────────────┘
```

---

## 4. Data Layer

### 4.1 `analytics/windows.py`

```python
from datetime import date, datetime, time, timedelta
from enum import Enum

class TimeWindow(str, Enum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7D = "7d"
    LAST_30D = "30d"

def date_range(window: TimeWindow, *, today: date | None = None) -> tuple[datetime, datetime]:
    """Inclusive start, exclusive end (UTC-naive, local-day boundaries)."""

def previous_period(window: TimeWindow, *, today: date | None = None) -> tuple[datetime, datetime]:
    """The equivalent prior period: yesterday for TODAY, 7d-before-7d for LAST_7D, etc."""
```

`today` is injectable for testing.

### 4.2 `analytics/queries.py`

All return values are `@dataclass(frozen=True, slots=True)`. All functions take an `AsyncSession` and explicit `start: datetime`, `end: datetime`. None of them hard-code the `TimeWindow` enum — translation from `TimeWindow` to `(start, end)` happens at the call site so caching keys are stable across callers.

Functions (final list):

1. `totals(session, start, end) -> Totals` — keys, clicks, active_seconds, idle_seconds, distinct_apps.
2. `app_rows(session, start, end) -> list[AppRow]` — per-app keys/clicks/focus_seconds.
3. `hour_buckets(session, start, end) -> list[HourBucket]` — 7×24 matrix entries (day_of_week, hour, intensity).
4. `daily_buckets(session, start, end) -> list[DailyBucket]` — date, keys, clicks, active_seconds.
5. `terminal_command_rows(session, start, end) -> list[TerminalCommandRow]` — command, count, last_seen, project.
6. `terminal_session_rows(session, start, end) -> list[TerminalSessionRow]` — session_id, started_at, duration, command_count.
7. `app_detail(session, start, end, *, bundle_id=None, name=None) -> AppDetail` — totals + per-window rows + per-hour activity for one app. At least one of `bundle_id` / `name` must be given; if both, `bundle_id` wins.
8. `comparisons(session, start, end, prev_start, prev_end) -> Comparisons` — totals/app deltas (`Delta` carries absolute and percentage).
9. `insights(session, start, end) -> Insights` — productivity score, peak hour, longest focus streak.

### 4.3 `analytics/cache.py`

```python
class TTLCache:
    def __init__(self, ttl_seconds: float = 30.0): ...
    async def get_or_compute(self, key: Hashable, factory: Callable[[], Awaitable[T]]) -> T: ...
    def invalidate(self, key: Hashable | None = None) -> None: ...  # None clears all
```

- TTL is configurable via `Settings.analytics_cache_ttl` (default `30.0`).
- The cache is exposed as a module-level singleton in `analytics/cache.py` (`get_cache() -> TTLCache`). Tabs and CLI subcommands wrap query calls via a `cached(query_name, start, end, **kwargs)` helper that builds the key and delegates to `TTLCache.get_or_compute`.
- `Store.flush()` imports `analytics.cache.get_cache()` and calls `invalidate()` after a successful flush so the next TUI tick reads fresh data. Both invalidation strategies are active: TTL bounds staleness in the worst case; flush-callback eliminates lag during active use.
- Cache keys are tuples of `(query_name, start, end, *sorted_kwargs)` — that's why query functions take explicit datetimes rather than a `TimeWindow` enum.

---

## 5. Theming

### 5.1 Mechanism

- Themes are pure Textual CSS files under `src/selfspy/tui/themes/`.
- `SelfspyApp` exposes a `theme` reactive (string). On change:
  1. `self.stylesheet.set_paths([Path(__file__).parent / "themes" / f"{theme}.tcss"])`
  2. `self.refresh_css()`
- All Python-side widgets reference CSS classes only. There is no `if theme == "dracula"` branching in Python.

### 5.2 Themes shipped

| Theme       | Use                                           |
|-------------|-----------------------------------------------|
| `default`   | Sensible neutral palette. **Default on first launch.** |
| `dark`      | High-contrast dark.                           |
| `solarized` | Solarized Dark.                               |
| `dracula`   | Dracula.                                      |

### 5.3 CSS structure

Each theme file defines variables (background, foreground, accent, muted, success, warning, error, sparkline gradient stops) and then re-declares the shared widget rules using those variables. Duplication is maintained by hand for now — there are only four files and the rules are short. If this becomes painful, factor a base `_shared.tcss` later; not in Phase 2.

### 5.4 Persistence

- Selected theme + last TimeWindow stored in `~/.selfspy/tui_state.json` (single JSON file, owned by `tui/state.py`).
- Loaded at app startup; missing/invalid file → defaults (`theme=default`, `window=today`).
- Written on change with an atomic replace (`tempfile` + `os.replace`).

---

## 6. CLI Compatibility

`selfstats`, `selfviz`, `selfterminal` keep working unchanged from the user's perspective. Internally they switch to calling the new `analytics/queries.py` functions instead of duplicating SQL. This is the natural way to prove the analytics layer is correct: both surfaces read the same thing.

The only Phase 2 CLI change is internal refactoring of those subcommands to delegate to `analytics/queries.py`. CLI flags, output formats, and exit codes are preserved.

---

## 7. Performance & Caching

- Default cache TTL: 30 seconds.
- Query batching: tabs that need multiple queries (Apps + comparisons, Summary + insights) issue them concurrently with `asyncio.gather`.
- The Heatmap query is the most expensive on 30d windows; it must use the existing index on `Click.created_at` and `Keys.created_at`. Add an explicit query plan check in M4 (no new indexes — verify existing ones are used).
- Ship-as-needed: optimize when measurement shows a problem, not pre-emptively.

---

## 8. Testing Strategy

- **Unit tests** for `analytics/windows.py` (boundary dates, DST), `analytics/queries.py` (in-memory SQLite with seeded fixtures), `analytics/cache.py` (TTL expiry, invalidation).
- **TUI snapshot/pilot tests** using `App.run_test()` for each new tab and the AppDetail modal. Pattern matches existing `tests/tui/test_summary_tab.py` and `tests/tui/test_apps_tab.py`.
- **Theme switching test** verifies `refresh_css()` is invoked and at least one CSS-derived style differs after switch.
- **Cache invalidation test** verifies `Store.flush()` clears the cache.
- CI matrix unchanged. Linux skips macOS-only tests via the `pytest.mark.macos` marker introduced in Phase 1.

---

## 9. Milestones

Each milestone ends with: tests green, ruff/mypy clean, atomic commit(s) on `revamp/phase-2-tui`, CI green.

### M1 — Foundation
- Create worktree at `../selfspy-revamp` on branch `revamp/phase-2-tui`.
- Add `tui/state.py` with reactive globals (TimeWindow, theme name) and `tui_state.json` load/save.
- Wire `SelfspyApp` to the new state without changing existing tab behavior yet.

### M2 — Query layer
- Implement `analytics/windows.py`, `analytics/queries.py` (all 9 functions), `analytics/cache.py`.
- Refactor `cli/stats.py`, `cli/viz.py`, `cli/terminal.py` to delegate to `analytics/queries.py` (no behavior change).
- Hook `Store.flush()` to `cache.invalidate()`.

### M3 — TUI shell
- Add app-wide key bindings for `1/2/3/4` (TimeWindow) and `T` (theme cycle) and `?` (help).
- Update Apps and Summary tabs to subscribe to TimeWindow; Live tab stays today-scoped.
- Add the global chrome bar.

### M4 — Heatmap, Timeline, comparisons
- Implement `widgets/heatmap.py`, `widgets/timeline.py`, `widgets/delta_badge.py`.
- Implement `tabs/heatmap.py`, `tabs/timeline.py`.
- Wire `comparisons()` into Apps + Summary (delta badges).
- Wire `insights()` into Summary.

### M5 — Terminal tab + AppDetail modal
- Implement `tabs/terminal.py` with Commands/Sessions sub-toggle.
- Implement `tabs/app_detail.py` (ModalScreen) and `Enter` binding on Apps rows.
- AppDetail uses the same TimeWindow as the parent app.

### M6 — Theming, polish, docs
- Author `themes/{default,dark,solarized,dracula}.tcss`.
- Implement `T` key cycle + persistence round-trip test.
- Update README and `docs/` to reflect TUI-first orientation.
- Run final cross-tab QA: window switch, theme switch, drill-in, drill-out.

---

## 10. Risks & Mitigations

- **Query duplication between CLI and TUI** — mitigated by mandating that both call `analytics/queries.py`. M2 deliberately migrates CLI before TUI grows new tabs.
- **Theme regressions across 4 stylesheets** — mitigated by snapshot tests on the most complex tab (Apps) for each theme.
- **Cache staleness during heavy activity** — mitigated by hooking `Store.flush()` so user-visible lag is bounded by flush cadence, not TTL.
- **Heatmap perf on 30d** — mitigated by verifying existing indexes; if insufficient, narrow the SELECT to only needed columns and bucket in SQL. No schema changes.
- **TimeWindow vs Live confusion** — mitigated by visibly disabling the window control on the Live tab and adding `?` help text.

---

## 11. Decisions Locked In

| Decision                                  | Choice                                       |
|-------------------------------------------|----------------------------------------------|
| Phase 2 scope                             | TUI rewrite + new analytics features         |
| Time-window control                       | Today / Yesterday / 7d / 30d                 |
| CLI views to fold into TUI                | Heatmap, Timeline, Terminal, Insights        |
| New analytics                             | Comparative trends + Per-app deep-dive       |
| Theming                                   | Multiple themes, applied uniformly           |
| CLI fate                                  | Keep all subcommands as-is                   |
| Drill-in UX                               | Enter on Apps row → modal screen             |
| Performance posture                       | Optimize as measured; ship what works        |
| Live tab behavior                         | Today-scoped; ignores global TimeWindow      |
| Cache TTL                                 | 30 s default (configurable)                  |
| Cache invalidation                        | TTL **and** `Store.flush()` callback         |
| `app_detail` key                          | Accepts `bundle_id` or `name`; bundle wins   |
| Default theme on first launch             | `default`                                    |
| Theme CSS duplication strategy            | Maintain by hand across 4 files              |
| State persistence file                    | `~/.selfspy/tui_state.json`                  |
| Milestone count                           | 6 (M1–M6)                                    |
| Schema changes                            | None                                         |
