"""Tests for app module."""

from src.app import foo


def test_foo_returns_two() -> None:
    """Test that foo function returns 2."""
    result = foo()
    assert result == 2


def test_foo_returns_integer() -> None:
    """Test that foo function returns an integer."""
    result = foo()
    assert isinstance(result, int)
