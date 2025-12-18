"""Tests for update_prices module."""

import json
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch
import uuid

import pytest

from update_prices import update_all_prices


@pytest.fixture
def test_db_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[Path, None, None]:
    """Create temporary database paths for testing."""
    urls_file = tmp_path / "urls.json"
    urls_file.write_text("[]")
    monkeypatch.chdir(tmp_path)
    yield tmp_path
    if urls_file.exists():
        urls_file.unlink()


def test_update_prices_with_price_change(test_db_path: Path) -> None:
    """Test that prices are updated when they change."""
    # Create a URL with an initial price
    urls_file = Path("urls.json")
    url_id = uuid.uuid4()
    group_id = uuid.uuid4()
    initial_data = [
        {
            "id": str(url_id),
            "url": "https://example.com/product",
            "group_id": str(group_id),
            "current_price": 100.0,
            "previous_price": None,
            "last_price_change": "2025-12-10T00:00:00+00:00",
        }
    ]
    urls_file.write_text(json.dumps(initial_data, indent=2))

    # Mock the PriceScraper to return a new price
    with patch("update_prices.PriceScraper") as mock_scraper_class:
        mock_scraper = Mock()
        mock_scraper.__enter__ = Mock(return_value=mock_scraper)
        mock_scraper.__exit__ = Mock(return_value=False)
        mock_scraper.fetch_price = Mock(return_value=120.0)
        mock_scraper_class.return_value = mock_scraper

        # Run the update
        update_all_prices()

    # Verify the price was updated and previous_price was set
    urls_data = json.loads(urls_file.read_text())
    assert len(urls_data) == 1
    assert urls_data[0]["current_price"] == 120.0
    assert urls_data[0]["previous_price"] == 100.0
    assert urls_data[0]["last_price_change"] != "2025-12-10T00:00:00+00:00"


def test_update_prices_no_change(test_db_path: Path) -> None:
    """Test that database is not updated when price doesn't change."""
    # Create a URL with an initial price
    urls_file = Path("urls.json")
    url_id = uuid.uuid4()
    group_id = uuid.uuid4()
    initial_timestamp = "2025-12-10T00:00:00+00:00"
    initial_data = [
        {
            "id": str(url_id),
            "url": "https://example.com/product",
            "group_id": str(group_id),
            "current_price": 100.0,
            "previous_price": 95.0,
            "last_price_change": initial_timestamp,
        }
    ]
    urls_file.write_text(json.dumps(initial_data, indent=2))

    # Mock the PriceScraper to return the same price
    with patch("update_prices.PriceScraper") as mock_scraper_class:
        mock_scraper = Mock()
        mock_scraper.__enter__ = Mock(return_value=mock_scraper)
        mock_scraper.__exit__ = Mock(return_value=False)
        mock_scraper.fetch_price = Mock(return_value=100.0)
        mock_scraper_class.return_value = mock_scraper

        # Run the update
        update_all_prices()

    # Verify nothing was changed (timestamp and previous_price unchanged)
    urls_data = json.loads(urls_file.read_text())
    assert len(urls_data) == 1
    assert urls_data[0]["current_price"] == 100.0
    assert urls_data[0]["previous_price"] == 95.0  # Should not change
    assert urls_data[0]["last_price_change"] == initial_timestamp  # Should not change


def test_update_prices_failed_fetch(test_db_path: Path) -> None:
    """Test that database is not updated when price fetch fails."""
    # Create a URL with an initial price
    urls_file = Path("urls.json")
    url_id = uuid.uuid4()
    group_id = uuid.uuid4()
    initial_timestamp = "2025-12-10T00:00:00+00:00"
    initial_data = [
        {
            "id": str(url_id),
            "url": "https://example.com/product",
            "group_id": str(group_id),
            "current_price": 100.0,
            "previous_price": None,
            "last_price_change": initial_timestamp,
        }
    ]
    urls_file.write_text(json.dumps(initial_data, indent=2))

    # Mock the PriceScraper to return None (fetch failed)
    with patch("update_prices.PriceScraper") as mock_scraper_class:
        mock_scraper = Mock()
        mock_scraper.__enter__ = Mock(return_value=mock_scraper)
        mock_scraper.__exit__ = Mock(return_value=False)
        mock_scraper.fetch_price = Mock(return_value=None)
        mock_scraper_class.return_value = mock_scraper

        # Run the update
        update_all_prices()

    # Verify nothing was changed
    urls_data = json.loads(urls_file.read_text())
    assert len(urls_data) == 1
    assert urls_data[0]["current_price"] == 100.0
    assert urls_data[0]["previous_price"] is None
    assert urls_data[0]["last_price_change"] == initial_timestamp


def test_update_prices_first_price(test_db_path: Path) -> None:
    """Test setting price for URL without previous price."""
    # Create a URL without any price
    urls_file = Path("urls.json")
    url_id = uuid.uuid4()
    group_id = uuid.uuid4()
    initial_data = [
        {
            "id": str(url_id),
            "url": "https://example.com/product",
            "group_id": str(group_id),
            "current_price": None,
            "previous_price": None,
            "last_price_change": None,
        }
    ]
    urls_file.write_text(json.dumps(initial_data, indent=2))

    # Mock the PriceScraper to return a price
    with patch("update_prices.PriceScraper") as mock_scraper_class:
        mock_scraper = Mock()
        mock_scraper.__enter__ = Mock(return_value=mock_scraper)
        mock_scraper.__exit__ = Mock(return_value=False)
        mock_scraper.fetch_price = Mock(return_value=150.0)
        mock_scraper_class.return_value = mock_scraper

        # Run the update
        update_all_prices()

    # Verify the price was set
    urls_data = json.loads(urls_file.read_text())
    assert len(urls_data) == 1
    assert urls_data[0]["current_price"] == 150.0
    assert (
        urls_data[0]["previous_price"] is None
    )  # No previous price since this is first fetch
    assert urls_data[0]["last_price_change"] is not None


def test_update_prices_multiple_urls(test_db_path: Path) -> None:
    """Test updating multiple URLs with different outcomes."""
    # Create multiple URLs
    urls_file = Path("urls.json")
    group_id = uuid.uuid4()
    initial_data = [
        {
            "id": str(uuid.uuid4()),
            "url": "https://example.com/product1",
            "group_id": str(group_id),
            "current_price": 100.0,
            "previous_price": None,
            "last_price_change": "2025-12-10T00:00:00+00:00",
        },
        {
            "id": str(uuid.uuid4()),
            "url": "https://example.com/product2",
            "group_id": str(group_id),
            "current_price": 200.0,
            "previous_price": 180.0,
            "last_price_change": "2025-12-10T00:00:00+00:00",
        },
        {
            "id": str(uuid.uuid4()),
            "url": "https://example.com/product3",
            "group_id": str(group_id),
            "current_price": None,
            "previous_price": None,
            "last_price_change": None,
        },
    ]
    urls_file.write_text(json.dumps(initial_data, indent=2))

    # Mock the PriceScraper with different results
    def mock_fetch_price(url: str) -> float | None:
        if "product1" in url:
            return 120.0  # Price increase
        elif "product2" in url:
            return 200.0  # No change
        elif "product3" in url:
            return None  # Fetch failed
        return None

    with patch("update_prices.PriceScraper") as mock_scraper_class:
        mock_scraper = Mock()
        mock_scraper.__enter__ = Mock(return_value=mock_scraper)
        mock_scraper.__exit__ = Mock(return_value=False)
        mock_scraper.fetch_price = Mock(side_effect=mock_fetch_price)
        mock_scraper_class.return_value = mock_scraper

        # Run the update
        update_all_prices()

    # Verify results
    urls_data = json.loads(urls_file.read_text())
    assert len(urls_data) == 3

    # Product 1 should be updated
    assert urls_data[0]["current_price"] == 120.0
    assert urls_data[0]["previous_price"] == 100.0

    # Product 2 should not be updated (same price)
    assert urls_data[1]["current_price"] == 200.0
    assert urls_data[1]["previous_price"] == 180.0  # Unchanged
    assert urls_data[1]["last_price_change"] == "2025-12-10T00:00:00+00:00"  # Unchanged

    # Product 3 should not be updated (fetch failed)
    assert urls_data[2]["current_price"] is None
    assert urls_data[2]["previous_price"] is None
    assert urls_data[2]["last_price_change"] is None
