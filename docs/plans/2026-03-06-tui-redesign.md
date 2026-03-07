# TUI Redesign: Textual-Based Tabbed Interface

## Overview

Replace the current Rich Live-based TUI with a Textual framework application featuring a tabbed interface for better organization and user experience.

## Problem

The current TUI crams 6 panels into one view: header, metrics, top apps, current focus, productivity, and yesterday comparison. This creates visual clutter and makes information hard to parse at a glance.

## Solution

A Textual-based TUI with three focused tabs, each serving a specific purpose.

## Tab Structure

| Tab | Purpose | Key Information |
|-----|---------|-----------------|
| Live | Real-time feedback | Keystroke/click counters, sparklines, current window, status |
| Apps | Application insights | Sorted app list with activity percentages, scrollable |
| Summary | Session overview | Totals, active/idle time, vs yesterday comparison |

Navigation: Tab bar at top, arrow keys or number keys (1/2/3), mouse clickable.

## Visual Layout

### Live Tab
```
┌─ Live ─────────────────────────────────────────────┐
│                                                     │
│   Keystrokes    1,234      ▁▂▃▅▆▄▃▂▅▇█▆▄▃    45/min │
│   Clicks          89      ▁▁▂▂▃▂▁▂▃▄▃▂▁      8/min │
│                                                     │
│   ─────────────────────────────────────────────     │
│   Current: VS Code - activity_monitor.py            │
│   Status: ACTIVE                    00:42:15        │
└─────────────────────────────────────────────────────┘
```

### Apps Tab
```
┌─ Apps ──────────────────────────────────────────────┐
│  App                Keys    Clicks   Activity       │
│  ─────────────────────────────────────────────      │
│  VS Code             892       45    ████████░░ 62% │
│  Firefox             234       32    ███░░░░░░░ 18% │
│  Terminal            156       12    ██░░░░░░░░ 11% │
│  Slack                78       23    █░░░░░░░░░  7% │
└─────────────────────────────────────────────────────┘
```

### Summary Tab
```
┌─ Summary ───────────────────────────────────────────┐
│                                                     │
│  Session Duration     02:15:30                      │
│  Active Time          01:52:00 (83%)                │
│  Idle Time            00:23:30 (17%)                │
│                                                     │
│  Total Keystrokes     4,521                         │
│  Total Clicks           342                         │
│  Windows Switched        47                         │
│                                                     │
│  vs Yesterday         ▲ 12% more active             │
└─────────────────────────────────────────────────────┘
```

## Architecture

### Current
```
ActivityMonitor.start()
  └── Rich Live display (blocking loop, mixed concerns)
```

### New
```
ActivityMonitor (data collection only)
  └── SelfspyApp (Textual app, owns display)
        └── Reads from ActivityMonitor state
        └── Updates via Textual reactive system
```

## Components

| Component | File | Responsibility |
|-----------|------|----------------|
| SelfspyApp | `src/tui/app.py` | Main Textual app, tab container |
| LiveTab | `src/tui/tabs/live.py` | Real-time metrics display |
| AppsTab | `src/tui/tabs/apps.py` | Application table |
| SummaryTab | `src/tui/tabs/summary.py` | Session statistics |
| SparklineWidget | `src/tui/widgets/sparkline.py` | Custom sparkline renderer |

## Data Flow

1. ActivityMonitor collects input events, updates internal state dictionaries
2. Textual app uses `set_interval()` to poll state every 1 second
3. Reactive widgets update automatically when bound data changes

## Dependencies

```toml
dependencies = [
    "textual>=0.50.0",
]
```

## File Structure

```
src/
  tui/
    __init__.py
    app.py
    tabs/
      __init__.py
      live.py
      apps.py
      summary.py
    widgets/
      __init__.py
      sparkline.py
  activity_monitor.py  # Stripped of display code
```

## Migration Path

1. Add Textual dependency
2. Create `src/tui/` module with new components
3. Extract display code from ActivityMonitor
4. Update CLI to launch Textual app
5. Remove old Rich display methods from ActivityMonitor
