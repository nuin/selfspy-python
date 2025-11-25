# Installation Guide

Selfspy can be installed in multiple ways depending on your needs and preferences.

## Quick Install (Recommended)

### From PyPI (when published)

```bash
# Install with pip
pip install selfspy

# Install with pipx (isolated environment)
pipx install selfspy

# Install with uv (fastest)
uv tool install selfspy
```

### macOS-specific Installation

On macOS, you'll need additional dependencies for native window tracking:

```bash
# With pip
pip install selfspy[macos]

# With pipx
pipx install selfspy[macos]

# With uv
uv tool install selfspy --with selfspy[macos]
```

## From Source

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/nuin/selfspy-python.git
cd selfspy-python

# Install with uv (recommended)
uv sync --extra macos  # On macOS
uv sync                # On Linux

# Or install with pip
pip install -e .[macos]  # On macOS
pip install -e .         # On Linux
```

### Development Installation

If you want to contribute or modify the code:

```bash
# Clone the repository
git clone https://github.com/nuin/selfspy-python.git
cd selfspy-python

# Install with development dependencies
uv sync --group dev --extra macos

# Or with pip
pip install -e .[dev,macos]
```

## Platform-Specific Requirements

### macOS

**Required Permissions:**
- **Accessibility**: Required for keyboard/mouse monitoring
- **Screen Recording**: Optional, for screen capture features

Grant permissions:
```bash
# Check permissions
selfspy check-permissions

# Follow the prompts to grant permissions in System Settings
```

### Linux

Most distributions work with the default installation. May require additional permissions for input monitoring:

```bash
# Add user to input group (may be required)
sudo usermod -a -G input $USER

# Log out and back in for group changes to take effect
```

## Verification

Test your installation:

```bash
# Check version
selfspy --version

# Check permissions (macOS)
selfspy check-permissions

# Run a test session
selfspy start --debug
```

## Upgrading

### From PyPI

```bash
# With pip
pip install --upgrade selfspy

# With pipx
pipx upgrade selfspy

# With uv
uv tool upgrade selfspy
```

### From Source

```bash
cd selfspy-python
git pull
uv sync  # or pip install -e .
```

## Uninstallation

```bash
# With pip
pip uninstall selfspy

# With pipx
pipx uninstall selfspy

# With uv
uv tool uninstall selfspy

# Remove data directory (optional)
rm -rf ~/.selfspy
```

## Troubleshooting

### macOS: "Accessibility permissions missing"

1. Go to **System Settings → Privacy & Security → Accessibility**
2. Add your terminal app (Terminal.app, iTerm2, etc.)
3. Restart your terminal
4. Run `selfspy check-permissions` to verify

### Linux: "Permission denied" errors

```bash
# Ensure you're in the input group
groups | grep input

# If not, add yourself
sudo usermod -a -G input $USER

# Log out and back in
```

### Import errors

Make sure all dependencies are installed:

```bash
# Reinstall with all dependencies
pip install --force-reinstall selfspy[macos]
```

## Docker Installation (Advanced)

Create a `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install -e .

CMD ["selfspy", "start"]
```

Build and run:

```bash
docker build -t selfspy .
docker run -v ~/.selfspy:/root/.selfspy selfspy
```

## Next Steps

- See [USAGE.md](USAGE.md) for usage instructions
- See [CONFIGURATION.md](CONFIGURATION.md) for configuration options
- See [ARCHITECTURE.md](ARCHITECTURE.md) for system design
