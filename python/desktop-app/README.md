# Selfspy Desktop Widgets

Desktop widgets for displaying Selfspy activity monitoring data on macOS.

## Available Implementations

### 1. Python/PyObjC Versions

#### Simple Widget (`simple_widget.py`)
- Standalone widget with simulated data
- Good for testing and development
- Minimal dependencies

```bash
# Run simple widget
./simple_widget.py
```

#### Advanced Widget System (`selfspy_desktop_advanced.py`)
- Multiple widget types with real data integration
- Configuration management
- Widget positioning and customization

```bash
# Run advanced widgets
./selfspy_desktop_advanced.py
```

### 2. Native Objective-C Version (`../SelfspyWidgets/`)

For optimal performance and native macOS integration:

```bash
cd ../SelfspyWidgets
./build.sh
./SelfspyWidgets
```

## Features

- **Real-time Activity Monitoring**: Live display of keystrokes, clicks, and app usage
- **Terminal Integration**: Track command history and terminal activity
- **Application Analytics**: See which apps you use most with time tracking
- **Desktop Integration**: Always-on-top widgets that don't interfere with workflow
- **Drag & Drop**: Reposition widgets anywhere on screen
- **Auto-refresh**: Data updates automatically

## Requirements

### Python Versions
- Python 3.10+
- PyObjC frameworks: `uv pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz`

### Native Objective-C Version
- macOS 10.12+
- Xcode command line tools
- See `../SelfspyWidgets/README.md` for details

## Usage

### Quick Start
```bash
# Python version (easiest to modify)
./simple_widget.py

# Advanced Python version (more features)
./selfspy_desktop_advanced.py

# Native version (best performance)
cd ../SelfspyWidgets && ./build.sh && ./SelfspyWidgets
```

### Widget Controls
- **Drag**: Click and drag to reposition widgets
- **Quit**: Cmd+Q or close from menu
- **Data**: Auto-refreshes every 5-10 seconds

## Data Sources

Widgets can display:
- **Activity Statistics**: Keystrokes, mouse clicks, active time
- **Application Usage**: Time spent in different applications
- **Terminal Activity**: Command history and shell usage (via `selfterminal`)
- **Window Tracking**: Which windows and applications are active
- **Productivity Metrics**: Calculated productivity scores

## Development

### Adding New Widgets

1. **Python**: Subclass from the widget base classes in the advanced system
2. **Objective-C**: Inherit from `SelfspyWidget` in the native version

### Customization

- Modify colors, fonts, and layouts in the drawing code
- Add new data sources by integrating with Selfspy's database
- Adjust refresh rates and positioning as needed

## Architecture

### Python/PyObjC
- Uses PyObjC bindings for native macOS window management
- Integrates with Selfspy's async SQLAlchemy data layer
- Synchronous wrappers for GUI thread safety

### Native Objective-C
- Direct Cocoa/AppKit integration for optimal performance
- MVC architecture with delegate patterns
- Automatic memory management with ARC

## Integration

All widget versions can access the same Selfspy data:
- SQLite database in `~/.selfspy/` (default)
- Real-time monitoring from the main Selfspy daemon
- Terminal command tracking from `selfterminal` integration

Choose the implementation that best fits your needs:
- **Python**: Easy to modify and extend
- **Native**: Best performance and battery life