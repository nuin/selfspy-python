"""
Configuration settings for Selfspy using Pydantic
"""
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, validator
from pydantic.types import DirectoryPath

class Settings(BaseSettings):
    """Settings management using Pydantic"""
    
    # Base settings
    data_dir: DirectoryPath = Path.home() / ".selfspy"
    database_name: str = "selfspy.db"
    debug: bool = False
    read_only: bool = False
    
    # Activity settings
    active_window_check_interval: float = 0.1
    keystroke_buffer_timeout: int = 1
    active_threshold: int = 180  # seconds
    
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
    def create_data_dir(cls, v: Path) -> Path:
        """Ensure data directory exists"""
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    class Config:
        env_prefix = "SELFSPY_"