# Credits and Acknowledgments

## Original Selfspy

This project is a modern reimplementation inspired by the original [Selfspy](https://github.com/selfspy/selfspy) project.

**Original Authors:**
- Bjarte Johansen ([@ljos](https://github.com/ljos))
- David Fendrich ([@dfendrich](https://github.com/dfendrich))

**Original Project:** https://github.com/selfspy/selfspy

The original Selfspy (circa 2012-2016) was groundbreaking in several ways:
- First comprehensive activity monitoring tool focused on privacy
- Local-only data storage with optional encryption
- Cross-platform support (Linux, macOS, Windows)
- Simple yet powerful SQLite-based storage
- Command-line interface for querying activity data

## What This Implementation Adds

While maintaining the spirit and core concepts of the original Selfspy, this modern Python implementation adds:

### Architecture Improvements
- **Modern Python 3.10+** with type hints and async/await patterns
- **SQLAlchemy 2.0** with async support for non-blocking I/O
- **Alembic migrations** for schema evolution
- **Thread-safe operations** with asyncio.Queue
- **Graceful shutdown** with proper resource cleanup

### Security Enhancements
- **Per-installation encryption salt** (vs. hardcoded salt)
- **Rate limiting** for password attempts
- **Path validation** and sanitization
- **Secure file permissions** (0o600)

### User Experience
- **Real-time TUI dashboard** with Rich library (inspired by bottom/btop)
- **Sparkline charts** for activity visualization
- **Session tracking** with idle detection
- **Historical comparison** (today vs yesterday)
- **Productivity insights** and scoring
- **Multiple statistics commands** (selfstats, selfviz, selfterminal)

### Platform Integration
- **macOS native** window tracking with PyObjC
- **Bundle ID tracking** for better app identification
- **Screen information** (multi-monitor support)
- **Terminal command tracking** with git integration

### Developer Experience
- **Modern packaging** with pyproject.toml and hatchling
- **Comprehensive testing** with pytest and pytest-asyncio
- **Code quality tools** (black, ruff, mypy)
- **Detailed documentation** (installation, usage, architecture)
- **GitHub Actions** for CI/CD and PyPI publishing

## Technology Stack

This implementation wouldn't be possible without these excellent open source projects:

### Core Dependencies
- **SQLAlchemy** - The Python SQL toolkit and ORM
- **Rich** - Beautiful terminal formatting
- **Typer** - Modern CLI framework
- **pynput** - Cross-platform input monitoring
- **cryptography** - Encryption and security primitives
- **structlog** - Structured logging

### macOS Integration
- **PyObjC** - Python bridge to Objective-C (Quartz, ApplicationServices)

### Data & Visualization
- **Plotly** - Interactive visualizations
- **pandas** - Data analysis and manipulation

### Development Tools
- **uv** - Fast Python package installer
- **pytest** - Testing framework
- **black** - Code formatter
- **ruff** - Fast Python linter

## Community

Thanks to everyone who has contributed to making activity monitoring tools better and more accessible:

- The original Selfspy community for pioneering the concept
- The Python packaging community for modern tooling
- The Rich library maintainers for beautiful terminal UIs
- The SQLAlchemy team for the best Python ORM
- All contributors to the open source ecosystem

## Philosophy

Like the original Selfspy, this implementation is built on the principles of:

1. **Privacy First** - All data stays local, encryption is optional
2. **User Control** - You own your data, you control what's tracked
3. **Transparency** - Open source, auditable code
4. **Simplicity** - Easy to install, configure, and use
5. **Extensibility** - Built to be extended and customized

## Contributing

If you'd like to contribute to this project, we welcome:
- Bug reports and feature requests
- Code contributions (follow existing patterns)
- Documentation improvements
- Testing on different platforms
- Sharing your use cases and workflows

This project stands on the shoulders of giants. Thank you to everyone who has contributed to the open source community.
