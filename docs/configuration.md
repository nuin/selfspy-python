# Configuration Guide

Selfspy uses Pydantic Settings for configuration management, supporting both environment variables and `.env` files.

## Configuration Methods

### 1. Command-Line Options

Most common settings can be set via CLI flags:

```bash
# Custom data directory
uv run selfspy daemon --data-dir ~/my-selfspy-data

# Enable debug logging
uv run selfspy daemon --debug

# Disable text encryption
uv run selfspy daemon --no-text

# Provide password
uv run selfspy daemon --password "mypassword"
```

### 2. Environment Variables

All settings can be configured via environment variables with the `SELFSPY_` prefix:

```bash
# Set data directory
export SELFSPY_DATA_DIR=~/my-selfspy-data

# Enable debug mode
export SELFSPY_DEBUG=true

# Enable privacy mode
export SELFSPY_PRIVACY_MODE=true

# Configure screenshot settings
export SELFSPY_ENABLE_SCREENSHOTS=true
export SELFSPY_SCREENSHOT_INTERVAL=600
export SELFSPY_MAX_DAILY_SCREENSHOTS=50

# Run selfspy
uv run selfspy daemon
```

### 3. .env File

Create a `.env` file in your project root or data directory:

```bash
# .env
SELFSPY_DATA_DIR=/Users/username/selfspy-data
SELFSPY_DEBUG=false
SELFSPY_PRIVACY_MODE=true
SELFSPY_ENABLE_SCREENSHOTS=false
SELFSPY_ENCRYPTION_ENABLED=true
```

## Configuration Settings

### Basic Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `data_dir` | `~/.selfspy` | Directory for database and logs |
| `database_name` | `selfspy.db` | SQLite database filename |
| `debug` | `false` | Enable debug logging |
| `read_only` | `false` | Open database in read-only mode |

**Example:**
```bash
export SELFSPY_DATA_DIR=~/Documents/selfspy-data
export SELFSPY_DEBUG=true
```

### Activity Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `active_window_check_interval` | `0.1` | Seconds between window checks |
| `keystroke_buffer_timeout` | `1` | Seconds to buffer keystrokes |
| `active_threshold` | `180` | Seconds before marking inactive |
| `track_window_geometry` | `true` | Store window position/size |
| `check_accessibility` | `true` | Verify macOS permissions |
| `monitor_suppress_errors` | `false` | Suppress monitoring errors |

**Example:**
```bash
export SELFSPY_ACTIVE_THRESHOLD=300  # 5 minutes
export SELFSPY_TRACK_WINDOW_GEOMETRY=false
```

### Encryption Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `encryption_enabled` | `true` | Encrypt keystroke data |
| `encryption_digest_name` | `password.digest` | Password verification file |

**Example:**
```bash
export SELFSPY_ENCRYPTION_ENABLED=true
```

### Privacy Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `privacy_mode` | `false` | Enhanced privacy restrictions |
| `privacy_excluded_apps` | See below | Apps to exclude in privacy mode |
| `excluded_bundles` | See below | macOS bundle IDs to exclude |

**Default Privacy Excluded Apps:**
- 1Password
- Keychain Access
- System Settings

**Default Excluded Bundles:**
- `com.apple.SecurityAgent` (Password dialogs)
- `com.apple.systempreferences` (System Settings)
- `com.apple.finder` (Finder)
- `com.apple.dock` (Dock)

**Example:**
```bash
# Enable privacy mode
export SELFSPY_PRIVACY_MODE=true

# Customize excluded apps (comma-separated)
export SELFSPY_PRIVACY_EXCLUDED_APPS="1Password,Keychain Access,Password Manager"
```

### Screenshot Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `enable_screenshots` | `false` | Enable screenshot capture |
| `screenshot_interval` | `300` | Seconds between screenshots |
| `max_daily_screenshots` | `100` | Maximum screenshots per day |
| `min_window_duration` | `10` | Minimum window duration (seconds) |
| `screenshot_cleanup_days` | `30` | Auto-delete screenshots after N days |
| `screenshot_excluded_apps` | See below | Apps to exclude from screenshots |

**Default Screenshot Excluded Apps:**
- System Settings
- 1Password
- Terminal
- Activity Monitor
- Calculator
- Calendar
- Keychain Access
- Notes

**Example:**
```bash
export SELFSPY_ENABLE_SCREENSHOTS=true
export SELFSPY_SCREENSHOT_INTERVAL=600  # 10 minutes
export SELFSPY_MAX_DAILY_SCREENSHOTS=50
```

**Note:** Screenshot functionality requires Screen Recording permissions on macOS.

### Storage Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `max_database_size` | `1073741824` | Max DB size in bytes (1GB) |
| `auto_cleanup_threshold` | `0.9` | Cleanup at 90% of max size |
| `backup_enabled` | `true` | Enable automatic backups |
| `backup_interval_days` | `7` | Days between backups |
| `max_backups` | `5` | Maximum backup files to keep |

**Example:**
```bash
export SELFSPY_MAX_DATABASE_SIZE=2147483648  # 2GB
export SELFSPY_BACKUP_ENABLED=true
export SELFSPY_BACKUP_INTERVAL_DAYS=3
```

### Mouse and Input Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `mouse_tracking_enabled` | `true` | Track mouse clicks |
| `scroll_tracking_enabled` | `true` | Track scroll events |
| `detailed_window_info` | `true` | Track window metadata |

**Example:**
```bash
export SELFSPY_MOUSE_TRACKING_ENABLED=false
export SELFSPY_SCROLL_TRACKING_ENABLED=false
```

### Platform-Specific Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `platform_module` | `default` | Platform tracker to use |
| `enable_screen_recording` | `false` | Enable screen recording features |

**Example:**
```bash
export SELFSPY_ENABLE_SCREEN_RECORDING=true
```

### Advanced Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `aggregate_stats_enabled` | `true` | Enable statistical aggregation |
| `debug_logging_enabled` | `false` | Detailed debug logs |

## Configuration Examples

### Minimal Privacy-Focused Setup

```bash
# .env
SELFSPY_PRIVACY_MODE=true
SELFSPY_ENCRYPTION_ENABLED=true
SELFSPY_ENABLE_SCREENSHOTS=false
SELFSPY_MOUSE_TRACKING_ENABLED=false
SELFSPY_SCROLL_TRACKING_ENABLED=false
```

### High-Detail Monitoring

```bash
# .env
SELFSPY_ENABLE_SCREENSHOTS=true
SELFSPY_SCREENSHOT_INTERVAL=300
SELFSPY_MAX_DAILY_SCREENSHOTS=200
SELFSPY_TRACK_WINDOW_GEOMETRY=true
SELFSPY_DETAILED_WINDOW_INFO=true
SELFSPY_MOUSE_TRACKING_ENABLED=true
```

### Development/Debugging Setup

```bash
# .env
SELFSPY_DEBUG=true
SELFSPY_DEBUG_LOGGING_ENABLED=true
SELFSPY_MONITOR_SUPPRESS_ERRORS=false
SELFSPY_DATA_DIR=./dev-data
```

### Production Service Setup

```bash
# .env
SELFSPY_DATA_DIR=/var/lib/selfspy
SELFSPY_ENCRYPTION_ENABLED=true
SELFSPY_BACKUP_ENABLED=true
SELFSPY_BACKUP_INTERVAL_DAYS=1
SELFSPY_MAX_DATABASE_SIZE=5368709120  # 5GB
SELFSPY_AUTO_CLEANUP_THRESHOLD=0.85
```

## Custom Exclusion Lists

### Excluding Specific Applications

Add to your `.env` file:

```bash
# Comma-separated list of apps to exclude
SELFSPY_PRIVACY_EXCLUDED_APPS="1Password,LastPass,Bitwarden,KeePassXC"
```

### Excluding macOS Bundle IDs

For more precise control:

```python
# Create a custom config file: selfspy_config.py
from src.config import Settings

settings = Settings(
    excluded_bundles=[
        "com.apple.SecurityAgent",
        "com.apple.systempreferences",
        "com.agilebits.onepassword7",
        "com.lastpass.lastpass",
    ]
)
```

## Accessing Configuration in Code

```python
from src.config import Settings

# Load settings (reads .env automatically)
settings = Settings()

# Access settings
print(settings.data_dir)
print(settings.encryption_enabled)

# Override programmatically
settings = Settings(
    data_dir="/custom/path",
    debug=True
)
```

## Configuration Precedence

Settings are applied in this order (later overrides earlier):

1. Default values in `Settings` class
2. `.env` file
3. Environment variables
4. Command-line arguments

## Validation

Selfspy validates configuration on startup:

- `data_dir`: Created if it doesn't exist
- `screenshot_interval`: Must be ≥ 60 seconds
- `max_daily_screenshots`: Between 1 and 1000
- `min_window_duration`: Must be ≥ 1 second

Invalid configurations will raise errors on startup.

## Tips

1. **Use .env for persistent settings**: Environment variables for temporary changes
2. **Enable privacy mode**: For sensitive work environments
3. **Regular backups**: Enable automatic backups for important data
4. **Monitor database size**: Set appropriate limits for your use case
5. **Exclude sensitive apps**: Always exclude password managers and banking apps

## Next Steps

- [Usage Guide](usage.md) - Learn how to use Selfspy
- [Architecture](architecture.md) - Understand the internals
- [Troubleshooting](troubleshooting.md) - Solve common issues
