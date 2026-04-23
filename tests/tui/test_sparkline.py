"""Tests for the Sparkline widget."""


from src.tui.widgets.sparkline import Sparkline


class TestSparkline:
    """Test suite for Sparkline widget."""

    def test_sparkline_creation(self):
        """Test that Sparkline can be instantiated with data."""
        widget = Sparkline(data=[1, 2, 3, 4, 5])
        assert widget is not None
        assert widget.data == [1, 2, 3, 4, 5]

    def test_sparkline_empty_data(self):
        """Test Sparkline handles empty data."""
        widget = Sparkline(data=[])
        assert widget.data == []

    def test_sparkline_normalize_values(self):
        """Test that values are normalized to 0-7 range for block chars."""
        widget = Sparkline(data=[0, 50, 100])
        normalized = widget._normalize(widget.data)
        assert normalized[0] == 0  # min value
        assert normalized[2] == 7  # max value
        assert 0 <= normalized[1] <= 7

    def test_sparkline_render_blocks(self):
        """Test that data renders to block characters."""
        widget = Sparkline(data=[0, 25, 50, 75, 100])
        blocks = widget._render_blocks()
        # Should produce Unicode block characters
        assert len(blocks) == 5
        # Blocks should be from the BLOCKS constant
        valid_blocks = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587"
        for block in blocks:
            assert block in valid_blocks

    def test_sparkline_max_width(self):
        """Test that Sparkline respects max_width."""
        widget = Sparkline(data=list(range(100)), max_width=20)
        assert widget.max_width == 20
        # When rendered, should only show last 20 values
        blocks = widget._render_blocks()
        assert len(blocks) <= 20

    def test_sparkline_single_value(self):
        """Test Sparkline with single value doesn't divide by zero."""
        widget = Sparkline(data=[42])
        normalized = widget._normalize(widget.data)
        assert normalized == [7]  # Single value should be max

    def test_sparkline_all_same_values(self):
        """Test Sparkline with all same values."""
        widget = Sparkline(data=[5, 5, 5, 5])
        normalized = widget._normalize(widget.data)
        # All same values should render as full blocks
        assert all(n == 7 for n in normalized)
