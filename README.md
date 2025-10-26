# Selfspy Python Implementation

The original and most feature-complete implementation of Selfspy, built with modern Python practices.

## Quick Start

```bash
# Install dependencies
uv sync --group dev --extra macos

# Start monitoring
uv run selfspy start

# View statistics
uv run selfviz enhanced
```

## Features

- **Comprehensive Monitoring**: Keystrokes, mouse, windows, terminal commands
- **Rich Visualizations**: Beautiful CLI charts and graphs
- **Desktop Widgets**: Native macOS widgets for always-visible activity
- **Terminal Analytics**: Development workflow analysis with git integration
- **Privacy-First**: Local encryption, configurable exclusions

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

## License

GPL-3.0-or-later