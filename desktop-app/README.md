# Selfspy Desktop Widget 🖥️

A beautiful macOS desktop application that displays Selfspy activity statistics in real-time as an always-on-top widget.

## Features ✨

- **Live Activity Dashboard** - Real-time statistics on your desktop
- **Beautiful Visualizations** - Charts, graphs, and metrics
- **Customizable Widgets** - Multiple display modes and sizes
- **Always on Top** - Stay informed without switching apps
- **Transparency Support** - Blend with your desktop
- **Click-through Mode** - Non-intrusive overlay option

## Screenshots

[Widget screenshots will be added here]

## Installation

```bash
# From the main selfspy3 directory
cd desktop-app

# Install macOS app dependencies
pip install -r requirements.txt

# Run the desktop app
python selfspy_desktop.py
```

## Usage

1. **Start Selfspy monitoring** (in main project):
   ```bash
   selfspy start
   ```

2. **Launch the desktop widget**:
   ```bash
   python selfspy_desktop.py
   ```

3. **Customize your widget**:
   - Right-click for options menu
   - Drag to reposition
   - Resize by dragging corners
   - Toggle transparency and click-through modes

## Widget Types

- **Activity Summary** - Keystrokes, clicks, active time
- **Top Applications** - Most used apps today
- **Terminal Commands** - Recent command activity
- **Productivity Score** - Real-time productivity metrics
- **Mini Charts** - Compact activity graphs

## Configuration

The app saves preferences in `~/Library/Preferences/selfspy-desktop.plist`:
- Widget position and size
- Display preferences
- Update intervals
- Theme settings

## Development

Built with:
- **PyObjC** - Native macOS integration
- **Quartz** - Advanced graphics and transparency
- **Core Animation** - Smooth transitions
- **WebKit** - Rich HTML/CSS/JS visualizations (optional)

## Requirements

- macOS 10.15+
- Python 3.10+
- Selfspy running in background
- PyObjC frameworks