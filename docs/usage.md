# Usage Guide

## Starting Selfspy

### Basic Monitoring

Start monitoring with default settings:

```bash
uv run selfspy start
```

This will:
- Begin tracking keyboard, mouse, and window activity
- Store data in the default location (`~/.selfspy/`)
- Prompt for encryption password (first run)
- Display live statistics in the terminal

### Command Options

```bash
# Start with debug logging
uv run selfspy start --debug

# Use custom data directory
uv run selfspy start --data-dir ~/my-activity-data

# Disable text encryption (not recommended)
uv run selfspy start --no-text

# Skip permission checks (may fail on macOS)
uv run selfspy start --force

# Provide password directly
uv run selfspy start --password "mypassword"
```

### Stopping Monitoring

Press `Ctrl+C` to stop monitoring gracefully.

## Viewing Statistics

### Basic Statistics

View activity statistics with `selfstats`:

```bash
# View overall statistics
uv run selfstats

# Statistics for specific date range
uv run selfstats --start 2024-01-01 --end 2024-01-31

# Different output formats
uv run selfstats --format json
uv run selfstats --format csv
```

### Enhanced Visualizations

Use `selfviz` for rich visualizations:

```bash
# Enhanced statistics view
uv run selfviz enhanced

# Interactive web dashboard
uv run selfviz dashboard

# Application usage breakdown
uv run selfviz apps

# Time-based activity heatmap
uv run selfviz heatmap

# Productivity analysis
uv run selfviz productivity
```

### Terminal Analytics

Track terminal command usage:

```bash
# View terminal command statistics
uv run selfterminal stats

# Most used commands
uv run selfterminal top

# Command history with timing
uv run selfterminal history

# Git workflow analysis
uv run selfterminal git
```

## Desktop Widgets

### Python Widgets

#### Simple Widget
Standalone widget with basic statistics:

```bash
cd desktop-app
./simple_widget.py
```

Features:
- Real-time keystroke counter
- Click tracking
- Active window display
- Draggable, always-on-top

#### Advanced Widget System
Multiple widgets with comprehensive data:

```bash
cd desktop-app
./selfspy_desktop_advanced.py
```

Widgets include:
- Activity summary (keystrokes, clicks, active time)
- Application usage breakdown
- Terminal command tracker
- Productivity metrics

**Widget Controls:**
- **Drag**: Click and drag to reposition
- **Quit**: Cmd+Q or close window
- **Refresh**: Updates every 5-10 seconds automatically

## Data Management

### Database Location

Default database locations:
- macOS: `~/.selfspy/selfspy.db`
- Linux: `~/.local/share/selfspy/selfspy.db`
- Windows: `%APPDATA%\selfspy\selfspy.db`

### Backup Your Data

```bash
# Stop selfspy first
# Then copy database
cp ~/.selfspy/selfspy.db ~/backups/selfspy-backup-$(date +%Y%m%d).db
```

### Export Data

```bash
# Export to JSON
uv run selfstats --format json > activity-export.json

# Export to CSV
uv run selfstats --format csv > activity-export.csv
```

### Clear Old Data

To manually clean old data, use SQLite:

```bash
sqlite3 ~/.selfspy/selfspy.db

# Delete data older than 90 days
DELETE FROM keys WHERE created_at < datetime('now', '-90 days');
DELETE FROM click WHERE created_at < datetime('now', '-90 days');

# Vacuum to reclaim space
VACUUM;
```

## Privacy Features

### Encryption

Keystroke data is encrypted by default using AES-256:

```bash
# First run prompts for password
uv run selfspy start

# Password stored securely in system keychain
# Future runs use stored password automatically
```

### Disabling Text Storage

If you don't want to store keystroke text:

```bash
uv run selfspy start --no-text
```

This still tracks:
- Keystroke counts
- Mouse clicks and movements
- Window and application activity
- Terminal commands (if enabled)

### Application Exclusions

Configure exclusions in your settings (see [Configuration Guide](configuration.md)):

```python
# Exclude specific applications
excluded_apps = ["1Password", "KeychainAccess"]

# Exclude window titles matching patterns
excluded_titles = ["*password*", "*credit card*"]
```

## Running as a Service

### macOS LaunchAgent

Create `~/Library/LaunchAgents/org.selfspy.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>org.selfspy</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/uv</string>
        <string>run</string>
        <string>selfspy</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/selfspy.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/selfspy.err</string>
</dict>
</plist>
```

Load the service:
```bash
launchctl load ~/Library/LaunchAgents/org.selfspy.plist
```

### Linux systemd

Create `~/.config/systemd/user/selfspy.service`:

```ini
[Unit]
Description=Selfspy Activity Monitor
After=graphical-session.target

[Service]
Type=simple
ExecStart=/path/to/uv run selfspy start
Restart=always

[Install]
WantedBy=default.target
```

Enable and start:
```bash
systemctl --user enable selfspy
systemctl --user start selfspy
```

## Common Workflows

### Daily Review

```bash
# View today's activity
uv run selfviz enhanced --start $(date +%Y-%m-%d)

# Check productivity metrics
uv run selfviz productivity --start $(date +%Y-%m-%d)

# Review terminal commands
uv run selfterminal stats --start $(date +%Y-%m-%d)
```

### Weekly Reports

```bash
# Last 7 days
uv run selfstats --start $(date -v-7d +%Y-%m-%d) --format json > weekly-report.json

# Application time breakdown
uv run selfviz apps --start $(date -v-7d +%Y-%m-%d)
```

### Development Workflow Analysis

```bash
# Git command analysis
uv run selfterminal git

# IDE/editor usage
uv run selfviz apps | grep -E "(VS Code|PyCharm|vim)"
```

## Tips and Best Practices

1. **Regular Monitoring**: Run selfspy continuously for accurate tracking
2. **Backup Regularly**: Database grows over time, back it up periodically
3. **Use Widgets**: Desktop widgets provide passive awareness of activity
4. **Review Weekly**: Use weekly reports to identify productivity patterns
5. **Respect Privacy**: Use exclusions for sensitive applications
6. **Encrypt Data**: Always use encryption for keystroke data

## Next Steps

- [Configuration Guide](configuration.md) - Customize your setup
- [Architecture Documentation](architecture.md) - Understand how it works
- [Troubleshooting](troubleshooting.md) - Solve common issues
