"""
Configuration settings for Selfspy using Pydantic
"""

from pathlib import Path
from typing import List

from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings management using Pydantic"""

    # Base settings
    data_dir: Path = Path.home() / ".selfspy"
    database_name: str = "selfspy.db"
    debug: bool = False
    read_only: bool = False

    # Activity settings
    active_window_check_interval: float = 0.1
    keystroke_buffer_timeout: int = 1
    active_threshold: int = 180  # seconds
    track_window_geometry: bool = True
    check_accessibility: bool = True
    monitor_suppress_errors: bool = False

    # Process monitoring
    excluded_bundles: list[str] = [
        "com.apple.SecurityAgent",  # Password dialogs
        "com.apple.systempreferences",  # System Settings
        "com.apple.finder",  # Finder
        "com.apple.dock",  # Dock
    ]

    # Screenshot settings
    enable_screenshots: bool = False
    screenshot_interval: int = 300  # 5 minutes
    max_daily_screenshots: int = 100
    min_window_duration: int = 10  # seconds
    screenshot_cleanup_days: int = 30  # Auto-cleanup after 30 days
    screenshot_excluded_apps: List[str] = [
        "System Settings",
        "System Preferences",
        "1Password",
        "Terminal",
        "Activity Monitor",
        "Calculator",
        "Calendar",
        "Keychain Access",
        "Notes",  # Add any default apps you want to exclude
    ]

    # Encryption settings
    encryption_enabled: bool = True
    encryption_digest_name: str = "password.digest"

    # Platform-specific settings
    platform_module: str = "default"
    enable_screen_recording: bool = False

    # Privacy settings
    privacy_mode: bool = False  # When enabled, restricts certain types of logging
    privacy_excluded_apps: List[str] = [
        "1Password",
        "Keychain Access",
        "System Settings",
    ]

    # Storage settings
    max_database_size: int = 1024 * 1024 * 1024  # 1GB
    auto_cleanup_threshold: float = 0.9  # Cleanup when DB reaches 90% of max size
    backup_enabled: bool = True
    backup_interval_days: int = 7
    max_backups: int = 5

    # Advanced settings
    mouse_tracking_enabled: bool = True
    scroll_tracking_enabled: bool = True
    detailed_window_info: bool = True  # Track additional window metadata
    aggregate_stats_enabled: bool = True  # Enable statistical aggregation
    debug_logging_enabled: bool = False

    @property
    def database_path(self) -> Path:
        """Get the full database path"""
        return self.data_dir / self.database_name

    @field_validator("data_dir")
    @classmethod
    def validate_data_dir(cls, v: Path) -> Path:
        """Ensure data directory exists"""
        if not v.exists():
            v.mkdir(parents=True, exist_ok=True)
        elif not v.is_dir():
            raise ValueError(f"{v} exists but is not a directory")
        return v

    @field_validator("screenshot_interval")
    @classmethod
    def validate_screenshot_interval(cls, v: int) -> int:
        """Validate screenshot interval"""
        if v < 60:  # Minimum 1 minute
            raise ValueError("Screenshot interval must be at least 60 seconds")
        return v

    @field_validator("max_daily_screenshots")
    @classmethod
    def validate_max_screenshots(cls, v: int) -> int:
        """Validate maximum daily screenshots"""
        if v < 1:
            raise ValueError("Max daily screenshots must be at least 1")
        if v > 1000:
            raise ValueError("Max daily screenshots cannot exceed 1000")
        return v

    @field_validator("min_window_duration")
    @classmethod
    def validate_window_duration(cls, v: int) -> int:
        """Validate minimum window duration"""
        if v < 1:
            raise ValueError("Minimum window duration must be at least 1 second")
        return v

    def excluded_bundle_patterns(self) -> List[str]:
        """Get list of excluded bundle patterns"""
        patterns = self.excluded_bundles.copy()
        if self.privacy_mode:
            patterns.extend(
                [b for b in self.privacy_excluded_apps if b not in patterns]
            )
        return patterns

    model_config = ConfigDict(
        env_prefix="SELFSPY_", env_file=".env", env_file_encoding="utf-8"
    )

    # Example environment variables:
    # SELFSPY_DATA_DIR=/path/to/data
    # SELFSPY_DEBUG=true
    # SELFSPY_ENABLE_SCREENSHOTS=true
    # SELFSPY_SCREENSHOT_INTERVAL=300
    # SELFSPY_MAX_DAILY_SCREENSHOTS=100
    # SELFSPY_PRIVACY_MODE=true
