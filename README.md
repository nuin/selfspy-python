# Selfspy

[![PyPI](https://img.shields.io/pypi/v/selfspy)](https://pypi.org/project/selfspy/)
[![Python](https://img.shields.io/pypi/pyversions/selfspy)](https://pypi.org/project/selfspy/)
[![License](https://img.shields.io/github/license/nuin/selfspy-python)](LICENSE)

A comprehensive activity monitoring and analytics tool with real-time TUI, session tracking, and productivity insights. Built with modern Python for macOS and Linux.

## Features

- **Real-time TUI Dashboard** - Beautiful terminal UI with sparklines, metrics, and live updates
- **Session Tracking** - Track activity across multiple sessions with start/end times
- **Idle Detection** - Distinguish between active work and idle time (3-minute threshold)
- **Historical Comparison** - Compare today's activity vs yesterday with visual indicators
- **Focus Time Tracking** - See actual time spent in each application
- **Privacy-First** - Optional encryption, local storage, configurable exclusions
- **Rich Visualizations** - Enhanced statistics with charts, graphs, and insights
- **macOS Native** - Full window tracking with PyObjC integration
- **Linux Support** - Cross-platform with fallback tracking

## Quick Start

### Installation

```bash
# From PyPI (when published)
pip install selfspy

# On macOS (recommended for full features)
pip install selfspy[macos]

# With pipx (isolated environment)
pipx install selfspy[macos]

# With uv (fastest)
uv tool install selfspy --with selfspy[macos]
```

### Usage

```bash
# Start monitoring with live TUI
selfspy daemon

# View enhanced statistics
selfspy stats summary --days 7

# View visualizations
selfspy viz enhanced

# Check terminal activity
selfspy terminal stats
```

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[Installation Guide](docs/installation.md)** - Setup and dependencies
- **[Usage Guide](docs/usage.md)** - Commands and workflows
- **[Configuration](docs/configuration.md)** - Settings and customization
- **[Architecture](docs/architecture.md)** - System design and internals
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

## Requirements

- Python 3.10+
- macOS 10.12+ (for full features)
- Accessibility permissions (macOS)

For detailed installation instructions, see the [Installation Guide](docs/installation.md).

## Credits

This project is inspired by and based on the original [Selfspy](https://github.com/selfspy/selfspy) by Bjarte Johansen and David Fendrich. The original Selfspy pioneered the concept of comprehensive activity monitoring with privacy-first local storage and encryption.

This modern Python implementation builds upon that foundation with:
- Modern async/await patterns with SQLAlchemy 2.0
- Real-time TUI dashboard with Rich
- Session tracking and historical analytics
- Enhanced security and stability
- macOS native integration with PyObjC
- Comprehensive testing and documentation

We're grateful to the original authors for creating such an innovative tool and releasing it as open source.

## License

GPL-3.0-or-later

This project maintains compatibility with the original Selfspy's GPL-3.0 license.