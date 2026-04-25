# Troubleshooting Guide

## Common Issues

### Permission Issues (macOS)

#### Problem: "Accessibility permission required" error

**Symptoms:**
```
[yellow]Missing permissions: Accessibility[/yellow]
Monitoring may not work correctly without proper permissions
```

**Solution:**
1. Open **System Settings** → **Privacy & Security** → **Privacy**
2. Select **Accessibility** from the left sidebar
3. Find your terminal application (Terminal.app, iTerm2, etc.)
4. If present, toggle it off and back on
5. If not present, click the `+` button and add it
6. **Important:** Completely quit and restart your terminal application
7. Run `uv run selfspy check-permissions` to verify

**Still not working?**
```bash
# Try running with debug mode to see detailed errors
uv run selfspy daemon --debug

# Check if Python has permissions instead
# Add Python executable to Accessibility in System Settings
which python
# Then add that Python to Accessibility permissions
```

#### Problem: Screen recording permission required

**Symptoms:**
```
[yellow]Screen Recording permission required[/yellow]
```

**Solution (only if screenshots are enabled):**
1. Open **System Settings** → **Privacy & Security** → **Privacy**
2. Select **Screen Recording**
3. Add your terminal application
4. Restart terminal and selfspy

**Don't need screenshots?**
```bash
export SELFSPY_ENABLE_SCREENSHOTS=false
uv run selfspy daemon
```

### Installation Issues

#### Problem: PyObjC import errors on macOS

**Symptoms:**
```python
ImportError: No module named 'Quartz'
ModuleNotFoundError: No module named 'ApplicationServices'
```

**Solution:**
```bash
# Reinstall macOS extras
uv sync --extra macos --reinstall

# Or with pip
pip install pyobjc-framework-Quartz pyobjc-framework-ApplicationServices

# Verify installation
python -c "import Quartz; print('Success')"
```

#### Problem: uv not found

**Symptoms:**
```bash
uv: command not found
```

**Solution:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use pip
pip install selfspy

# Then run with python -m
python -m selfspy daemon
```

### Database Issues

#### Problem: "Database is locked" error

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Solution:**
```bash
# Check if another instance is running
ps aux | grep selfspy

# Kill any running instances
pkill -f selfspy

# If still locked, close all applications accessing the database
lsof ~/.selfspy/selfspy.db

# Last resort: backup and recreate
cp ~/.selfspy/selfspy.db ~/.selfspy/selfspy.db.backup
rm ~/.selfspy/selfspy.db
uv run selfspy daemon
```

#### Problem: Database corruption

**Symptoms:**
```
sqlite3.DatabaseError: database disk image is malformed
```

**Solution:**
```bash
# Try to recover
sqlite3 ~/.selfspy/selfspy.db "PRAGMA integrity_check;"

# If recoverable
sqlite3 ~/.selfspy/selfspy.db ".recover" | sqlite3 recovered.db
mv recovered.db ~/.selfspy/selfspy.db

# If not recoverable, start fresh (after backup)
cp ~/.selfspy/selfspy.db ~/.selfspy/selfspy.db.broken
rm ~/.selfspy/selfspy.db
uv run selfspy daemon
```

#### Problem: Database too large

**Symptoms:**
```
Database size: 5.2 GB
Performance degraded
```

**Solution:**
```bash
# Connect to database
sqlite3 ~/.selfspy/selfspy.db

# Check sizes
SELECT
    'keys' as table_name, COUNT(*) as rows FROM keys
UNION ALL
SELECT 'click', COUNT(*) FROM click
UNION ALL
SELECT 'window', COUNT(*) FROM window;

# Delete old data (e.g., older than 90 days)
DELETE FROM keys WHERE created_at < datetime('now', '-90 days');
DELETE FROM click WHERE created_at < datetime('now', '-90 days');
DELETE FROM window WHERE created_at < datetime('now', '-90 days');

# Clean up orphaned records
DELETE FROM window WHERE process_id NOT IN (SELECT id FROM process);

# Reclaim space
VACUUM;
```

### Encryption Issues

#### Problem: Forgot password

**Symptoms:**
```
[red]Invalid password[/red]
Unable to decrypt database
```

**Solution:**
```bash
# Unfortunately, encrypted data cannot be recovered
# You'll need to start fresh

# Backup existing database
mv ~/.selfspy/selfspy.db ~/.selfspy/selfspy.db.old

# Remove password digest
rm ~/.selfspy/password.digest

# Start with new password
uv run selfspy daemon
```

**Prevention:**
```bash
# Store password in a password manager
# Or disable encryption (not recommended)
export SELFSPY_ENCRYPTION_ENABLED=false
```

#### Problem: Keyring access denied

**Symptoms:**
```
keyring.errors.KeyringLocked: Keyring is locked
```

**Solution (macOS):**
```bash
# Unlock keychain
security unlock-keychain ~/Library/Keychains/login.keychain-db

# Or provide password via environment
export SELFSPY_PASSWORD="your-password"
uv run selfspy daemon
```

### Monitoring Issues

#### Problem: No keyboard events captured

**Symptoms:**
- Statistics show 0 keystrokes
- Window tracking works but no text captured

**Debug Steps:**
```bash
# 1. Check permissions
uv run selfspy check-permissions

# 2. Run with debug mode
uv run selfspy daemon --debug

# 3. Check excluded applications
echo $SELFSPY_PRIVACY_EXCLUDED_APPS

# 4. Try fallback mode
export SELFSPY_PLATFORM_MODULE="fallback"
uv run selfspy daemon
```

#### Problem: High CPU usage

**Symptoms:**
```
selfspy using >50% CPU
System becoming slow
```

**Solution:**
```bash
# 1. Increase polling interval
export SELFSPY_ACTIVE_WINDOW_CHECK_INTERVAL=0.5  # Default: 0.1

# 2. Disable detailed tracking
export SELFSPY_DETAILED_WINDOW_INFO=false
export SELFSPY_TRACK_WINDOW_GEOMETRY=false

# 3. Disable mouse tracking
export SELFSPY_MOUSE_TRACKING_ENABLED=false
export SELFSPY_SCROLL_TRACKING_ENABLED=false

# 4. Check for database issues
du -h ~/.selfspy/selfspy.db
# If large, clean up old data
```

#### Problem: Mouse clicks not tracked

**Symptoms:**
- Click count stays at 0
- Other monitoring works

**Solution:**
```bash
# Check if mouse tracking is enabled
export SELFSPY_MOUSE_TRACKING_ENABLED=true

# Run with debug
uv run selfspy daemon --debug

# Check for permission issues
uv run selfspy check-permissions
```

### Widget Issues

#### Problem: Widgets not displaying data

**Symptoms:**
- Widget shows "No data" or 0s
- Selfspy is running

**Solution:**
```bash
# 1. Verify selfspy is running
ps aux | grep selfspy

# 2. Check database location
ls -la ~/.selfspy/selfspy.db

# 3. Verify widget can access database
cd desktop-app
python -c "from data_integration import get_activity_stats; print(get_activity_stats())"

# 4. Run widget with debug
python simple_widget.py --debug
```

#### Problem: Widget crashes on startup

**Symptoms:**
```
objc.error: NSInternalInconsistencyException
```

**Solution:**
```bash
# Reinstall PyObjC
pip install --force-reinstall pyobjc-framework-Cocoa

# Try simple widget first
cd desktop-app
./simple_widget.py

# If that works, try advanced
./selfspy_desktop_advanced.py
```

### Terminal Integration Issues

#### Problem: Terminal commands not tracked

**Symptoms:**
- `selfspy terminal stats` shows no data
- Regular monitoring works

**Solution:**
```bash
# Terminal tracking requires explicit integration
# Currently only tracks when selfspy is active

# Check if terminal tracker is running
ps aux | grep terminal_tracker

# Run selfspy with debug to see terminal detection
uv run selfspy daemon --debug
```

### Platform-Specific Issues

#### Linux: X11 errors

**Symptoms:**
```
Xlib.error.DisplayError: Cannot connect to X server
```

**Solution:**
```bash
# Ensure X11 is running
echo $DISPLAY

# Install X11 dependencies
sudo apt-get install python3-xlib xdotool

# Set DISPLAY if needed
export DISPLAY=:0
```

#### Windows: Limited functionality

**Symptoms:**
- Basic tracking works but limited features
- No bundle ID tracking

**Expected Behavior:**
- Windows support uses fallback mode
- Bundle IDs not available (Windows doesn't use them)
- Some features like window geometry may be limited

## Performance Optimization

### Reduce Database Growth

```bash
# Enable auto-cleanup
export SELFSPY_AUTO_CLEANUP_THRESHOLD=0.8
export SELFSPY_MAX_DATABASE_SIZE=1073741824  # 1GB

# Schedule periodic cleanup
# Add to crontab:
0 0 * * 0 sqlite3 ~/.selfspy/selfspy.db "DELETE FROM keys WHERE created_at < datetime('now', '-60 days'); VACUUM;"
```

### Reduce Resource Usage

```bash
# Minimal monitoring configuration
export SELFSPY_ACTIVE_WINDOW_CHECK_INTERVAL=0.5
export SELFSPY_MOUSE_TRACKING_ENABLED=false
export SELFSPY_SCROLL_TRACKING_ENABLED=false
export SELFSPY_DETAILED_WINDOW_INFO=false
export SELFSPY_TRACK_WINDOW_GEOMETRY=false
```

### Optimize Statistics Queries

```bash
# Use date ranges
uv run selfspy stats --start 2024-01-01 --end 2024-01-31

# Limit to specific apps
uv run selfspy viz apps --filter "Code|Terminal"

# Use JSON format for processing (faster than text)
uv run selfspy stats --format json
```

## Getting Help

### Enable Debug Logging

```bash
# Run with maximum verbosity
export SELFSPY_DEBUG=true
export SELFSPY_DEBUG_LOGGING_ENABLED=true
uv run selfspy daemon --debug 2>&1 | tee selfspy-debug.log
```

### Check System Information

```bash
# Python version
python --version  # Requires 3.10+

# OS information
uname -a

# Disk space
df -h ~/.selfspy/

# Database info
sqlite3 ~/.selfspy/selfspy.db "SELECT sqlite_version();"
sqlite3 ~/.selfspy/selfspy.db ".schema"
```

### Collect Diagnostic Information

```bash
# Create diagnostic report
cat > diagnostic.txt <<EOF
Python Version: $(python --version)
OS: $(uname -a)
Selfspy Location: $(which selfspy)
Database Size: $(du -h ~/.selfspy/selfspy.db)
Permissions: $(uv run selfspy check-permissions)
Recent Logs: $(tail -50 /tmp/selfspy.log)
EOF
```

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `AXIsProcessTrusted() returned False` | No Accessibility permission | Grant permission in System Settings |
| `No module named 'Quartz'` | PyObjC not installed | `uv sync --extra macos` |
| `database is locked` | Multiple instances running | Kill other instances |
| `Invalid password` | Wrong encryption password | Reset database or recover password |
| `Permission denied` | File permissions | `chmod 600 ~/.selfspy/selfspy.db` |

## Still Having Issues?

1. Search existing issues: [GitHub Issues](https://github.com/yourusername/selfspy-python/issues)
2. Create a new issue with:
   - Error message
   - Debug logs
   - System information
   - Steps to reproduce

## Next Steps

- [Installation Guide](installation.md) - Reinstall or repair
- [Configuration](configuration.md) - Adjust settings
- [Usage Guide](usage.md) - Learn proper usage
- [Architecture](architecture.md) - Understand internals
