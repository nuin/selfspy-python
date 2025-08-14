"""
Configuration and preferences for Selfspy Desktop Widgets
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class WidgetPosition:
    """Widget position and size configuration"""
    x: float
    y: float
    width: float
    height: float


@dataclass
class WidgetSettings:
    """Individual widget settings"""
    type: str
    title: str
    position: WidgetPosition
    always_on_top: bool = True
    click_through: bool = False
    opacity: float = 0.9
    update_interval: int = 10  # seconds
    enabled: bool = True


@dataclass
class GlobalSettings:
    """Global widget manager settings"""
    auto_start: bool = False
    hide_from_dock: bool = True
    show_in_menu_bar: bool = True
    theme: str = "dark"  # dark, light, auto
    animation_enabled: bool = True
    notification_enabled: bool = True


class WidgetConfig:
    """Widget configuration manager"""
    
    def __init__(self):
        self.config_dir = Path.home() / "Library" / "Preferences" / "SelfspyWidgets"
        self.config_file = self.config_dir / "config.json"
        self.widgets: Dict[str, WidgetSettings] = {}
        self.global_settings = GlobalSettings()
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing configuration
        self.load()
    
    def load(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                # Load global settings
                if 'global' in data:
                    global_data = data['global']
                    self.global_settings = GlobalSettings(**global_data)
                
                # Load widget settings
                if 'widgets' in data:
                    for widget_id, widget_data in data['widgets'].items():
                        position_data = widget_data['position']
                        position = WidgetPosition(**position_data)
                        
                        widget_settings = WidgetSettings(
                            type=widget_data['type'],
                            title=widget_data['title'],
                            position=position,
                            always_on_top=widget_data.get('always_on_top', True),
                            click_through=widget_data.get('click_through', False),
                            opacity=widget_data.get('opacity', 0.9),
                            update_interval=widget_data.get('update_interval', 10),
                            enabled=widget_data.get('enabled', True)
                        )
                        
                        self.widgets[widget_id] = widget_settings
                
                print(f"✅ Loaded configuration for {len(self.widgets)} widgets")
                
            except Exception as e:
                print(f"⚠️  Error loading config: {e}")
                self._create_default_config()
        else:
            self._create_default_config()
    
    def save(self):
        """Save configuration to file"""
        try:
            config_data = {
                'global': asdict(self.global_settings),
                'widgets': {}
            }
            
            # Convert widget settings to dict
            for widget_id, widget_settings in self.widgets.items():
                config_data['widgets'][widget_id] = asdict(widget_settings)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            print(f"💾 Saved configuration to {self.config_file}")
            
        except Exception as e:
            print(f"❌ Error saving config: {e}")
    
    def _create_default_config(self):
        """Create default configuration"""
        print("🔧 Creating default widget configuration")
        
        # Default widget positions
        screen_width = 1440  # Assume standard resolution
        screen_height = 900
        
        # Activity summary widget (top right)
        self.widgets['activity'] = WidgetSettings(
            type='activity',
            title='📊 Today\'s Activity',
            position=WidgetPosition(
                x=screen_width - 320,
                y=screen_height - 200,
                width=300,
                height=180
            )
        )
        
        # Top apps widget (middle right)
        self.widgets['apps'] = WidgetSettings(
            type='apps',
            title='🏆 Top Applications',
            position=WidgetPosition(
                x=screen_width - 340,
                y=screen_height - 420,
                width=320,
                height=220
            ),
            enabled=False  # Disabled by default
        )
        
        # Terminal widget (bottom right)
        self.widgets['terminal'] = WidgetSettings(
            type='terminal',
            title='🔧 Terminal Activity',
            position=WidgetPosition(
                x=screen_width - 370,
                y=screen_height - 680,
                width=350,
                height=200
            ),
            enabled=False  # Disabled by default
        )
        
        # Charts widget (top left)
        self.widgets['charts'] = WidgetSettings(
            type='charts',
            title='📈 Activity Charts',
            position=WidgetPosition(
                x=20,
                y=screen_height - 180,
                width=280,
                height=160
            ),
            enabled=False  # Disabled by default
        )
        
        self.save()
    
    def get_widget_settings(self, widget_id: str) -> Optional[WidgetSettings]:
        """Get settings for a specific widget"""
        return self.widgets.get(widget_id)
    
    def update_widget_position(self, widget_id: str, x: float, y: float, width: float, height: float):
        """Update widget position"""
        if widget_id in self.widgets:
            self.widgets[widget_id].position = WidgetPosition(x, y, width, height)
            self.save()
    
    def set_widget_enabled(self, widget_id: str, enabled: bool):
        """Enable or disable a widget"""
        if widget_id in self.widgets:
            self.widgets[widget_id].enabled = enabled
            self.save()
    
    def get_enabled_widgets(self) -> Dict[str, WidgetSettings]:
        """Get all enabled widgets"""
        return {k: v for k, v in self.widgets.items() if v.enabled}
    
    def update_global_setting(self, key: str, value: Any):
        """Update a global setting"""
        if hasattr(self.global_settings, key):
            setattr(self.global_settings, key, value)
            self.save()
    
    def export_config(self, file_path: str):
        """Export configuration to a file"""
        try:
            config_data = {
                'global': asdict(self.global_settings),
                'widgets': {k: asdict(v) for k, v in self.widgets.items()}
            }
            
            with open(file_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            print(f"📤 Configuration exported to {file_path}")
            
        except Exception as e:
            print(f"❌ Error exporting config: {e}")
    
    def import_config(self, file_path: str):
        """Import configuration from a file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Backup current config
            backup_file = self.config_file.with_suffix('.backup.json')
            self.export_config(str(backup_file))
            
            # Clear current config
            self.widgets.clear()
            
            # Load new config
            if 'global' in data:
                self.global_settings = GlobalSettings(**data['global'])
            
            if 'widgets' in data:
                for widget_id, widget_data in data['widgets'].items():
                    position = WidgetPosition(**widget_data['position'])
                    widget_settings = WidgetSettings(
                        type=widget_data['type'],
                        title=widget_data['title'],
                        position=position,
                        always_on_top=widget_data.get('always_on_top', True),
                        click_through=widget_data.get('click_through', False),
                        opacity=widget_data.get('opacity', 0.9),
                        update_interval=widget_data.get('update_interval', 10),
                        enabled=widget_data.get('enabled', True)
                    )
                    self.widgets[widget_id] = widget_settings
            
            self.save()
            print(f"📥 Configuration imported from {file_path}")
            
        except Exception as e:
            print(f"❌ Error importing config: {e}")


# Global configuration instance
_config = None

def get_config() -> WidgetConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = WidgetConfig()
    return _config


# Convenience functions
def save_widget_position(widget_id: str, x: float, y: float, width: float, height: float):
    """Save widget position"""
    config = get_config()
    config.update_widget_position(widget_id, x, y, width, height)

def get_widget_position(widget_id: str) -> Optional[WidgetPosition]:
    """Get widget position"""
    config = get_config()
    settings = config.get_widget_settings(widget_id)
    return settings.position if settings else None

def is_widget_enabled(widget_id: str) -> bool:
    """Check if widget is enabled"""
    config = get_config()
    settings = config.get_widget_settings(widget_id)
    return settings.enabled if settings else False