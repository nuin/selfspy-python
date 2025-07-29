# Desktop Widget Usage Guide 🪟

## Quick Start

1. **Install PyObjC dependencies**:
   ```bash
   uv pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz
   ```

2. **Launch widgets**:
   ```bash
   python3 launch_widgets.py developer
   ```

3. **Customize widgets**:
   - Right-click any widget for options
   - Drag widgets to reposition
   - Toggle always-on-top and click-through modes

## Widget Types

### 📊 Activity Summary
- Today's keystrokes and clicks
- Active time calculation
- Productivity score
- Most active hour

### 🏆 Top Applications  
- Applications by usage time
- Percentage breakdown
- Visual progress bars
- Real-time updates

### 🔧 Terminal Activity
- Commands executed today
- Most used command type
- Current project detection
- Recent command history

### 📈 Activity Charts
- Hourly activity bars
- Peak activity identification
- Current activity streak
- Visual activity patterns

## Presets

- **minimal** - Just activity summary
- **developer** - Activity + Terminal + Top Apps
- **full** - All widget types
- **charts** - Just activity charts
- **terminal** - Just terminal activity

## Customization

### Right-click Menu Options:
- **Widget Type** - Change widget display
- **Always on Top** - Keep above other windows
- **Click Through** - Make widget non-interactive
- **Close Widget** - Remove widget

### Configuration Files:
- Config stored in: `~/Library/Preferences/SelfspyWidgets/`
- Positions and settings auto-saved
- Export/import configurations

## Tips & Tricks

1. **Multiple Instances**: Run different widgets from separate terminals
2. **Positioning**: Widgets remember their positions
3. **Performance**: Widgets update every 10 seconds by default
4. **Privacy**: All data stays local, uses existing Selfspy database

## Troubleshooting

### Widget Not Updating?
- Check if Selfspy is running: `selfspy start`
- Verify database connection: `python3 launch_widgets.py --check`

### Permission Issues?
- Grant Accessibility permissions in System Settings
- Run: `selfspy check-permissions`

### Visual Issues?
- Ensure you're running on macOS 10.15+
- Try different widget preset: `python3 launch_widgets.py minimal`

## Advanced Usage

### Custom Widget Development
1. Create new widget class in `widget_types.py`
2. Implement `update_data()` and `draw()` methods
3. Add to `WIDGET_TYPES` registry
4. Test with `python3 selfspy_desktop_advanced.py --widget your_widget`

### Data Integration
- Widgets use `data_integration.py` for Selfspy data access
- Add new data sources by extending `SelfspyDataProvider`
- Synchronous wrappers available for GUI thread safety

## Examples

```bash
# Launch single widget
python3 selfspy_desktop_advanced.py --widget activity

# Launch developer preset
python3 launch_widgets.py developer

# Check system requirements
python3 launch_widgets.py --check

# List all options
python3 launch_widgets.py --list
```

Enjoy your beautiful desktop activity widgets! 🎯