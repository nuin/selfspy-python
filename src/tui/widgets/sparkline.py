"""
Sparkline Widget - Unicode block-based activity visualization

Renders a list of values as a horizontal sparkline using Unicode block
characters for a compact visual representation of activity over time.
"""


from rich.text import Text
from textual.widget import Widget

# Unicode block characters for 8 levels (0-7)
BLOCKS = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587"


class Sparkline(Widget):
    """A sparkline widget using Unicode block characters.

    Displays a list of numeric values as a horizontal bar chart using
    Unicode block elements. Values are normalized to fit 8 levels.
    """

    DEFAULT_CSS = """
    Sparkline {
        height: 1;
        width: auto;
    }
    """

    def __init__(
        self,
        data: list[float] | None = None,
        max_width: int = 20,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the Sparkline widget.

        Args:
            data: List of numeric values to display
            max_width: Maximum number of blocks to display
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        self._data: list[float] = list(data) if data else []
        self.max_width = max_width

    @property
    def data(self) -> list[float]:
        """Get the current data."""
        return self._data

    @data.setter
    def data(self, value: list[float]) -> None:
        """Set the data and trigger refresh."""
        self._data = list(value) if value else []
        self.refresh()

    def _normalize(self, values: list[float]) -> list[int]:
        """Normalize values to 0-7 range for block character selection.

        Args:
            values: List of numeric values

        Returns:
            List of integers in range 0-7
        """
        if not values:
            return []

        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val

        if range_val == 0:
            # All values are the same - render as full blocks
            return [7] * len(values)

        normalized = []
        for v in values:
            # Scale to 0-7 range
            level = int(((v - min_val) / range_val) * 7)
            normalized.append(min(7, max(0, level)))

        return normalized

    def _render_blocks(self) -> str:
        """Render data as block characters.

        Returns:
            String of Unicode block characters
        """
        # Take only the last max_width values
        display_data = self._data[-self.max_width :] if self._data else []

        if not display_data:
            return ""

        normalized = self._normalize(display_data)
        return "".join(BLOCKS[level] for level in normalized)

    def render(self) -> Text:
        """Render the sparkline widget."""
        blocks = self._render_blocks()
        return Text(blocks, style="green")

    def update_data(self, new_data: list[float]) -> None:
        """Update the sparkline data.

        Args:
            new_data: New list of values to display
        """
        self.data = new_data

    def append(self, value: float) -> None:
        """Append a single value to the sparkline.

        Args:
            value: Value to append
        """
        self._data.append(value)
        # Keep only max_width * 2 values for memory efficiency
        if len(self._data) > self.max_width * 2:
            self._data = self._data[-self.max_width :]
        self.refresh()
