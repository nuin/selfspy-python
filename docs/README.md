# Selfspy Documentation

Comprehensive documentation for the Selfspy Python implementation - a privacy-focused activity monitoring and analytics tool.

## Quick Links

- [Installation Guide](installation.md) - Get started with Selfspy
- [Usage Guide](usage.md) - Learn how to use all features
- [Configuration](configuration.md) - Customize your setup
- [Architecture](architecture.md) - Understand the internals
- [Troubleshooting](troubleshooting.md) - Solve common issues

## What is Selfspy?

Selfspy is a comprehensive activity monitoring tool that tracks:
- **Keyboard Activity**: Keystroke counts and encrypted text
- **Mouse Activity**: Clicks, movement, and scroll events
- **Window Activity**: Active applications and windows
- **Terminal Activity**: Command history and shell usage
- **Time Analytics**: Detailed productivity metrics

All data is stored locally with optional encryption for privacy.

## Documentation Overview

### For New Users

1. **[Installation Guide](installation.md)**
   - System requirements
   - Installation steps for macOS/Linux/Windows
   - Setting up permissions
   - Verifying installation

2. **[Usage Guide](usage.md)**
   - Starting monitoring
   - Viewing statistics
   - Using desktop widgets
   - Running as a service
   - Common workflows

### For Configuration

3. **[Configuration Guide](configuration.md)**
   - Environment variables
   - Settings reference
   - Privacy settings
   - Screenshot configuration
   - Storage management

### For Developers

4. **[Architecture Documentation](architecture.md)**
   - System architecture
   - Core components
   - Data flow
   - Platform abstraction
   - Extension points

### For Troubleshooting

5. **[Troubleshooting Guide](troubleshooting.md)**
   - Common issues
   - Permission problems
   - Database issues
   - Performance optimization
   - Getting help

## Quick Start

```bash
# Install
uv sync --group dev --extra macos

# Check permissions (macOS)
uv run selfspy check-permissions

# Start monitoring
uv run selfspy daemon

# View statistics
uv run selfspy viz enhanced
```

## Key Features

### Privacy-First Design
- Local data storage (no cloud sync)
- Optional AES-256 encryption for keystrokes
- Application exclusion lists
- Privacy mode for sensitive environments

### Rich Visualizations
- Terminal-based statistics with Rich
- Interactive charts with Plotly
- Desktop widgets for macOS
- Multiple export formats (JSON, CSV)

### Platform Support
- **macOS**: Full support with native APIs
- **Linux**: Support via fallback mode
- **Windows**: Basic support

### Terminal Analytics
- Command frequency analysis
- Git workflow tracking
- Productivity metrics
- Development pattern analysis

### Desktop Widgets
- Real-time activity display
- Always-on-top, draggable windows
- Multiple widget types
- Configurable layouts

## Architecture Highlights

### Modern Python Stack
- **Python 3.10+**: Modern language features
- **async/await**: Non-blocking I/O
- **SQLAlchemy 2.0**: Modern ORM patterns
- **Typer + Rich**: Beautiful CLI

### Platform Integration
- **macOS**: PyObjC for native API access
- **Cross-platform**: pynput fallback
- **Async I/O**: aiosqlite for database

### Data Model
```
Process → Window → Keys/Clicks
```
Clean relational model with comprehensive indexing

## Common Use Cases

### Personal Productivity
- Track time spent in different applications
- Identify productivity patterns
- Review daily/weekly activity
- Optimize workflows

### Development Analysis
- Terminal command analytics
- IDE usage patterns
- Git workflow analysis
- Context switching tracking

### Time Tracking
- Automatic activity logging
- Detailed time breakdowns
- Client project tracking
- Billable hours analysis

### Privacy Monitoring
- See what you're actually typing
- Identify sensitive data exposure
- Audit application behavior
- Personal data awareness

## System Requirements

### Minimum Requirements
- Python 3.10 or higher
- 100 MB disk space (more for data)
- SQLite 3.8+

### Recommended Setup
- macOS 10.12+ for full features
- 1 GB disk space for database
- SSD for better performance
- 4 GB RAM

### macOS Permissions
- **Accessibility** (Required): For input monitoring
- **Screen Recording** (Optional): For screenshots

## Getting Help

### Documentation
- Read through guides in order
- Check troubleshooting for common issues
- Review architecture for deep understanding

### Community
- GitHub Issues: Bug reports and feature requests
- Discussions: Questions and community support

### Debugging
```bash
# Enable debug output
uv run selfspy daemon --debug

# Check permissions
uv run selfspy check-permissions

# View logs
tail -f /tmp/selfspy.log
```

## Contributing

### Documentation Improvements
- Suggest corrections via GitHub issues
- Submit PRs for documentation updates
- Add examples and use cases

### Code Contributions
- See [Architecture](architecture.md) for codebase overview
- Follow existing patterns
- Add tests for new features

## License

GPL-3.0-or-later - See LICENSE file for details

## Project Structure

```
selfspy-python/
├── docs/               # This documentation
├── src/                # Main source code
│   ├── cli.py         # CLI interface
│   ├── activity_monitor.py
│   ├── activity_store.py
│   ├── models.py      # Database models
│   ├── config.py      # Configuration
│   ├── encryption.py  # Encryption utilities
│   └── platform/      # Platform-specific code
├── desktop-app/       # Desktop widgets
├── tests/            # Test suite
└── pyproject.toml    # Project metadata
```

## Version History

- **1.0.0**: Initial Python implementation
  - Modern async architecture
  - macOS native support
  - Desktop widgets
  - Terminal analytics

## Roadmap

Future features under consideration:
- Web dashboard
- Multi-device sync (optional)
- Plugin system
- Advanced analytics
- Machine learning insights

---

**Need help?** Start with the [Installation Guide](installation.md) or check [Troubleshooting](troubleshooting.md) for common issues.
