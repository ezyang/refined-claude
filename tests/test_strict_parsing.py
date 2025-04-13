import pytest
import logging
from unittest.mock import patch, MagicMock

from refined_claude.parsing import UnrecognizedElementError, parse_para


def test_strict_mode_raises_exception():
    """Test that strict mode raises an exception for unrecognized elements."""
    # Create a mock HAX object with an unrecognized role
    mock_hax = MagicMock()
    mock_hax.role = "UnknownRole"
    mock_hax.repr.return_value = "mock representation"

    # In strict mode, we should raise an exception
    with pytest.raises(UnrecognizedElementError):
        parse_para(mock_hax, strict=True)


def test_normal_mode_logs_warning():
    """Test that normal mode logs a warning for unrecognized elements."""
    # Create a mock HAX object with an unrecognized role
    mock_hax = MagicMock()
    mock_hax.role = "UnknownRole"
    mock_hax.repr.return_value = "mock representation"
    mock_hax.inner_text.return_value = "Some text"

    # In normal mode, we should log a warning and return some content
    with patch('refined_claude.parsing.log.warning') as mock_warning:
        result = parse_para(mock_hax, strict=False)

        # Assert that warning was called
        mock_warning.assert_called_once()

        # Assert that the function returned content
        assert len(result) > 0
