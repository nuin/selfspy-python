#!/usr/bin/env python3
"""
Selfspy Desktop Widget Launcher

Easy launcher script for the Selfspy desktop widgets with different presets.
"""

import sys
import os
import subprocess
from pathlib import Path

def check_requirements():
    """Check if all requirements are installed"""
    try:
        import objc
        from AppKit import NSApplication, NSWindow
        from Foundation import NSObject
        print("✅ PyObjC frameworks available")
        return True
    except ImportError as e:
        print(f"❌ Missing requirements: {e}")
        print("\n🔧 Install requirements with:")
        print("   uv pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz")
        return False

def check_selfspy_connection():
    """Check if Selfspy is accessible"""
    try:
        # Add parent directory to path
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from config import Settings
        settings = Settings()
        print("✅ Selfspy configuration accessible")
        return True
    except Exception as e:
        print(f"⚠️  Selfspy connection issue: {e}")
        print("   Widgets will use mock data")
        return False

def launch_preset(preset_name):
    """Launch a specific widget preset"""
    presets = {
        'minimal': ['activity'],
        'developer': ['activity', 'terminal', 'apps'],
        'full': ['activity', 'apps', 'terminal', 'charts'],
        'charts': ['charts'],
        'terminal': ['terminal']
    }
    
    if preset_name not in presets:
        print(f"❌ Unknown preset: {preset_name}")
        print(f"Available presets: {', '.join(presets.keys())}")
        return False
    
    widgets = presets[preset_name]
    print(f"🚀 Launching '{preset_name}' preset with widgets: {', '.join(widgets)}")
    
    # Launch the first widget with the main application
    if widgets:
        cmd = [sys.executable, "selfspy_desktop_advanced.py", "--widget", widgets[0]]
        print(f"Running: {' '.join(cmd)}")
        subprocess.Popen(cmd)
        
        # Launch additional widgets if any
        for widget in widgets[1:]:
            cmd = [sys.executable, "selfspy_desktop_advanced.py", "--widget", widget]
            subprocess.Popen(cmd)
    
    return True

def main():
    """Main launcher function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Selfspy Desktop Widget Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Presets:
  minimal    - Just activity summary
  developer  - Activity, terminal, and top apps  
  full       - All widget types
  charts     - Just the activity charts
  terminal   - Just terminal activity

Examples:
  python launch_widgets.py minimal
  python launch_widgets.py developer
  python launch_widgets.py --widget activity
        """
    )
    
    parser.add_argument('preset', nargs='?', 
                       choices=['minimal', 'developer', 'full', 'charts', 'terminal'],
                       help='Widget preset to launch')
    
    parser.add_argument('--widget', '-w',
                       choices=['activity', 'apps', 'terminal', 'charts'],
                       help='Launch a single widget type')
    
    parser.add_argument('--check', '-c', action='store_true',
                       help='Check requirements and exit')
    
    parser.add_argument('--list', '-l', action='store_true',
                       help='List available presets and widgets')
    
    args = parser.parse_args()
    
    print("🎯 Selfspy Desktop Widget Launcher")
    print("==================================")
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check Selfspy connection
    check_selfspy_connection()
    
    if args.check:
        print("✅ All checks passed!")
        return
    
    if args.list:
        print("\n📋 Available presets:")
        presets = {
            'minimal': 'Just activity summary',
            'developer': 'Activity, terminal, and top apps',
            'full': 'All widget types',
            'charts': 'Just the activity charts',
            'terminal': 'Just terminal activity'
        }
        for name, desc in presets.items():
            print(f"  {name:10} - {desc}")
        
        print("\n🧩 Available widgets:")
        widgets = {
            'activity': 'Daily activity summary',
            'apps': 'Top applications',
            'terminal': 'Terminal command activity',
            'charts': 'Mini activity charts'
        }
        for name, desc in widgets.items():
            print(f"  {name:10} - {desc}")
        return
    
    # Launch single widget
    if args.widget:
        print(f"🚀 Launching single widget: {args.widget}")
        cmd = [sys.executable, "selfspy_desktop_advanced.py", "--widget", args.widget]
        subprocess.run(cmd)
        return
    
    # Launch preset
    if args.preset:
        launch_preset(args.preset)
        return
    
    # Default: show help
    parser.print_help()
    print("\n💡 Quick start:")
    print("   python launch_widgets.py developer")

if __name__ == "__main__":
    main()