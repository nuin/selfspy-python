"""
Configuration settings for Selfspy using Pydantic
"""
from pathlib import Path
from typing import Optional

from pydantic import validator
from pydantic_settings import BaseSettings
from pydantic.types import DirectoryPath

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
    excluded_bundles: list[str] = []
    
    # Permission settings
    enable_screen_recording: bool = False  # Added this setting
    
    # Encryption settings
    encryption_enabled: bool = True
    encryption_digest_name: str = "password.digest"
    
    # Platform-specific settings
    platform_module: str = "default"
    
    @property
    def database_path(self) -> Path:
        """Get the full database path"""
        return self.data_dir / self.database_name
        
    @validator("data_dir")
    def validate_data_dir(cls, v: Path) -> Path:
        """Ensure data directory exists"""
        if not v.exists():
            v.mkdir(parents=True, exist_ok=True)
        elif not v.is_dir():
            raise ValueError(f"{v} exists but is not a directory")
        return v
    
    class Config:
        env_prefix = "SELFSPY_"