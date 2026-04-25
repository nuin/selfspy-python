"""Pure analytics: read from Store, return dataclasses/dicts. No I/O beyond DB."""

from . import stats, terminal, viz

__all__ = ["stats", "terminal", "viz"]
