"""Tests for app module."""

import json
from pathlib import Path
from typing import Generator
import uuid

import pytest
from flask import Flask
from flask.testing import FlaskClient

from src.app import create_app


@pytest.fixture
def test_db_path(tmp_path: Path) -> Generator[Path, None, None]:
    """Create temporary database paths for testing."""
    groups_file = tmp_path / "groups.json"
    urls_file = tmp_path / "urls.json"
    groups_file.write_text("[]")
    urls_file.write_text("[]")
    yield tmp_path
    if groups_file.exists():
        groups_file.unlink()
    if urls_file.exists():
        urls_file.unlink()


@pytest.fixture
def app(test_db_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    """Create a Flask app instance for testing."""
    monkeypatch.chdir(test_db_path)
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create a test client for the Flask app."""
    return app.test_client()


def get_group_id_by_name(name: str) -> uuid.UUID:
    """Helper to get group ID by name from database."""
    groups_file = Path("groups.json")
    if not groups_file.exists():
        raise ValueError("Groups file not found")
    groups_data = json.loads(groups_file.read_text())
    for group in groups_data:
        if group.get("name") == name:
            return uuid.UUID(group["id"])
    raise ValueError(f"Group '{name}' not found")


def get_url_id_by_url(url: str) -> uuid.UUID:
    """Helper to get URL ID by url string from database."""
    urls_file = Path("urls.json")
    if not urls_file.exists():
        raise ValueError("URLs file not found")
    urls_data = json.loads(urls_file.read_text())
    for url_item in urls_data:
        if url_item.get("url") == url:
            return uuid.UUID(url_item["id"])
    raise ValueError(f"URL '{url}' not found")


def test_index_empty(client: FlaskClient) -> None:
    """Test that index page loads with empty state."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"No groups yet" in response.data


def test_add_group(client: FlaskClient) -> None:
    """Test adding a group."""
    response = client.post(
        "/group/add", data={"group_name": "Work"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Group added successfully!" in response.data
    assert b"Work" in response.data


def test_add_empty_group(client: FlaskClient) -> None:
    """Test adding an empty group name."""
    response = client.post("/group/add", data={"group_name": ""}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Group name cannot be empty!" in response.data


def test_update_group(client: FlaskClient) -> None:
    """Test renaming a group."""
    # First add a group
    client.post("/group/add", data={"group_name": "Work"})

    # Get the group ID
    group_id = get_group_id_by_name("Work")

    # Then rename it
    response = client.post(
        f"/group/update/{group_id}",
        data={"group_name": "Personal"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Group updated successfully!" in response.data


def test_delete_empty_group(client: FlaskClient) -> None:
    """Test deleting an empty group."""
    # Add a group
    client.post("/group/add", data={"group_name": "Work"})

    # Get the group ID
    group_id = get_group_id_by_name("Work")

    # Delete it
    response = client.post(f"/group/delete/{group_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"Group deleted successfully!" in response.data


def test_delete_group_with_urls(client: FlaskClient) -> None:
    """Test that groups with URLs cannot be deleted."""
    # Add a group
    client.post("/group/add", data={"group_name": "Work"})

    # Get the group ID
    group_id = get_group_id_by_name("Work")

    # Add a URL to the group
    client.post(
        "/url/add", data={"url": "https://example.com", "group_id": str(group_id)}
    )

    # Try to delete the group
    response = client.post(f"/group/delete/{group_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"Cannot delete group with URLs!" in response.data


def test_add_url_to_group(client: FlaskClient) -> None:
    """Test adding a URL to a group."""
    # Add a group first
    client.post("/group/add", data={"group_name": "Work"})

    # Get the group ID
    group_id = get_group_id_by_name("Work")

    # Add a URL
    response = client.post(
        "/url/add",
        data={"url": "https://example.com", "group_id": str(group_id)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"URL added successfully!" in response.data
    assert b"https://example.com" in response.data


def test_add_url_without_group(client: FlaskClient) -> None:
    """Test adding a URL without selecting a group."""
    response = client.post(
        "/url/add", data={"url": "https://example.com"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Please select a group!" in response.data


def test_add_empty_url(client: FlaskClient) -> None:
    """Test adding an empty URL."""
    # Add a group first
    client.post("/group/add", data={"group_name": "Work"})

    # Get the group ID
    group_id = get_group_id_by_name("Work")

    response = client.post(
        "/url/add", data={"url": "", "group_id": str(group_id)}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"URL cannot be empty!" in response.data


def test_update_url(client: FlaskClient) -> None:
    """Test updating a URL."""
    # Add a group and URL
    client.post("/group/add", data={"group_name": "Work"})
    group_id = get_group_id_by_name("Work")
    client.post(
        "/url/add", data={"url": "https://example.com", "group_id": str(group_id)}
    )

    # Get the URL ID
    url_id = get_url_id_by_url("https://example.com")

    # Update the URL
    response = client.post(
        f"/url/update/{url_id}",
        data={"url": "https://updated.com"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"URL updated successfully!" in response.data


def test_delete_url(client: FlaskClient) -> None:
    """Test deleting a URL."""
    # Add a group and URL
    client.post("/group/add", data={"group_name": "Work"})
    group_id = get_group_id_by_name("Work")
    client.post(
        "/url/add", data={"url": "https://example.com", "group_id": str(group_id)}
    )

    # Get the URL ID
    url_id = get_url_id_by_url("https://example.com")

    # Delete the URL
    response = client.post(f"/url/delete/{url_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"URL deleted successfully!" in response.data


def test_multiple_groups_and_urls(client: FlaskClient) -> None:
    """Test multiple groups with URLs."""
    # Add groups
    client.post("/group/add", data={"group_name": "Work"})
    client.post("/group/add", data={"group_name": "Personal"})

    # Get group IDs
    work_id = get_group_id_by_name("Work")
    personal_id = get_group_id_by_name("Personal")

    # Add URLs to different groups
    client.post("/url/add", data={"url": "https://work1.com", "group_id": str(work_id)})
    client.post("/url/add", data={"url": "https://work2.com", "group_id": str(work_id)})
    client.post(
        "/url/add", data={"url": "https://personal1.com", "group_id": str(personal_id)}
    )

    response = client.get("/")
    assert b"Work" in response.data
    assert b"Personal" in response.data
    assert b"https://work1.com" in response.data
    assert b"https://work2.com" in response.data
    assert b"https://personal1.com" in response.data


def test_url_with_price_fields(client: FlaskClient) -> None:
    """Test that URLs can have price fields and they are displayed."""
    # Add a group
    client.post("/group/add", data={"group_name": "Shopping"})

    # Get the group ID
    group_id = get_group_id_by_name("Shopping")

    # Add a URL
    client.post(
        "/url/add", data={"url": "https://shop.com/item", "group_id": str(group_id)}
    )

    # Manually update the JSON to include price fields (simulating script update)
    urls_file = Path("urls.json")
    urls_data = json.loads(urls_file.read_text())
    urls_data[0]["current_price"] = 99.99
    urls_data[0]["last_price_change"] = "2025-12-18"
    urls_file.write_text(json.dumps(urls_data, indent=2))

    # Verify the price fields are displayed in the UI (database reloads on each request)
    response = client.get("/")
    assert b"99.99" in response.data
    assert b"Updated" in response.data


def test_url_without_price_fields(client: FlaskClient) -> None:
    """Test that URLs without price fields display correctly."""
    # Add a group and URL
    client.post("/group/add", data={"group_name": "Work"})
    group_id = get_group_id_by_name("Work")
    client.post(
        "/url/add", data={"url": "https://example.com", "group_id": str(group_id)}
    )

    # Get the page
    response = client.get("/")

    # URL should be displayed
    assert b"https://example.com" in response.data
    # But price fields should not be shown since they're None
    assert b'class="price-tag"' not in response.data
    assert b"Updated" not in response.data


def test_url_update_preserves_price_fields(client: FlaskClient) -> None:
    """Test that updating a URL preserves price fields."""
    # Add a group and URL
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")
    client.post(
        "/url/add", data={"url": "https://shop.com/item1", "group_id": str(group_id)}
    )

    # Manually add price fields (simulating script update)
    urls_file = Path("urls.json")
    urls_data = json.loads(urls_file.read_text())
    urls_data[0]["current_price"] = 49.99
    urls_data[0]["previous_price"] = 44.99
    urls_data[0]["last_price_change"] = "2025-12-15"
    urls_file.write_text(json.dumps(urls_data, indent=2))

    # Get the URL ID
    url_id = get_url_id_by_url("https://shop.com/item1")

    # Update the URL
    client.post(f"/url/update/{url_id}", data={"url": "https://shop.com/item2"})

    # Verify price fields are preserved
    urls_data = json.loads(urls_file.read_text())
    assert urls_data[0]["url"] == "https://shop.com/item2"
    assert urls_data[0]["current_price"] == 49.99
    assert urls_data[0]["previous_price"] == 44.99
    assert urls_data[0]["last_price_change"] == "2025-12-15"


def test_url_with_previous_price_shows_diff(client: FlaskClient) -> None:
    """Test that URLs with previous_price show price difference in UI."""
    # Add a group and URL
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")
    client.post(
        "/url/add", data={"url": "https://shop.com/item", "group_id": str(group_id)}
    )

    # Manually add price fields showing a price increase
    urls_file = Path("urls.json")
    urls_data = json.loads(urls_file.read_text())
    urls_data[0]["current_price"] = 55.00
    urls_data[0]["previous_price"] = 50.00
    urls_data[0]["last_price_change"] = "2025-12-18"
    urls_file.write_text(json.dumps(urls_data, indent=2))

    # Get the page
    response = client.get("/")

    # Should show the price increase
    assert b"55.00" in response.data or b"55.0" in response.data
    # Should show the price diff (increase by 5.00)
    assert b"+5.00" in response.data or b"5.00" in response.data


def test_url_with_previous_price_decrease(client: FlaskClient) -> None:
    """Test that URLs show price decrease correctly."""
    # Add a group and URL
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")
    client.post(
        "/url/add", data={"url": "https://shop.com/item", "group_id": str(group_id)}
    )

    # Manually add price fields showing a price decrease
    urls_file = Path("urls.json")
    urls_data = json.loads(urls_file.read_text())
    urls_data[0]["current_price"] = 45.00
    urls_data[0]["previous_price"] = 50.00
    urls_data[0]["last_price_change"] = "2025-12-18"
    urls_file.write_text(json.dumps(urls_data, indent=2))

    # Get the page
    response = client.get("/")

    # Should show the price decrease
    assert b"45.00" in response.data or b"45.0" in response.data
    # Should show the price diff (decrease by 5.00)
    assert b"-5.00" in response.data or b"5.00" in response.data


def test_timestamp_filter_today(client: FlaskClient, app: Flask) -> None:
    """Test that timestamp filter shows 'today' for today's date."""
    from datetime import datetime, timezone

    # Add a group and URL
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")
    client.post(
        "/url/add", data={"url": "https://shop.com/item", "group_id": str(group_id)}
    )

    # Set last_price_change to today
    urls_file = Path("urls.json")
    urls_data = json.loads(urls_file.read_text())
    urls_data[0]["current_price"] = 50.00
    urls_data[0]["last_price_change"] = datetime.now(timezone.utc).isoformat()
    urls_file.write_text(json.dumps(urls_data, indent=2))

    # Get the page
    response = client.get("/")

    # Should show 'today'
    assert b"today" in response.data


def test_timestamp_filter_days_ago(client: FlaskClient) -> None:
    """Test that timestamp filter shows 'N days ago' correctly."""
    from datetime import datetime, timedelta, timezone

    # Add a group and URL
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")
    client.post(
        "/url/add", data={"url": "https://shop.com/item", "group_id": str(group_id)}
    )

    # Set last_price_change to 5 days ago
    urls_file = Path("urls.json")
    urls_data = json.loads(urls_file.read_text())
    urls_data[0]["current_price"] = 50.00
    five_days_ago = datetime.now(timezone.utc) - timedelta(days=5)
    urls_data[0]["last_price_change"] = five_days_ago.isoformat()
    urls_file.write_text(json.dumps(urls_data, indent=2))

    # Get the page
    response = client.get("/")

    # Should show '5 days ago'
    assert b"5 days ago" in response.data


def test_timestamp_filter_months_ago(client: FlaskClient) -> None:
    """Test that timestamp filter shows 'N months ago' for older dates."""
    from datetime import datetime, timedelta, timezone

    # Add a group and URL
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")
    client.post(
        "/url/add", data={"url": "https://shop.com/item", "group_id": str(group_id)}
    )

    # Set last_price_change to 90 days ago (3 months)
    urls_file = Path("urls.json")
    urls_data = json.loads(urls_file.read_text())
    urls_data[0]["current_price"] = 50.00
    ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
    urls_data[0]["last_price_change"] = ninety_days_ago.isoformat()
    urls_file.write_text(json.dumps(urls_data, indent=2))

    # Get the page
    response = client.get("/")

    # Should show '3 months ago'
    assert b"3 months ago" in response.data or b"months ago" in response.data


# --- Feature: Duplicate URL Prevention ---


def test_add_duplicate_url_same_group(client: FlaskClient) -> None:
    """Test that adding the same URL to the same group is prevented."""
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")

    # Add a URL
    client.post(
        "/url/add",
        data={"url": "https://example.com/product", "group_id": str(group_id)},
    )

    # Try adding the same URL again to the same group
    response = client.post(
        "/url/add",
        data={"url": "https://example.com/product", "group_id": str(group_id)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"This URL already exists in the selected group!" in response.data


def test_add_duplicate_url_with_trailing_slash(client: FlaskClient) -> None:
    """Test that adding a URL with a trailing slash is detected as duplicate."""
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")

    client.post(
        "/url/add",
        data={"url": "https://example.com/product", "group_id": str(group_id)},
    )

    response = client.post(
        "/url/add",
        data={"url": "https://example.com/product/", "group_id": str(group_id)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"This URL already exists in the selected group!" in response.data


def test_add_same_url_different_groups(client: FlaskClient) -> None:
    """Test that the same URL can be added to different groups."""
    client.post("/group/add", data={"group_name": "Work"})
    client.post("/group/add", data={"group_name": "Personal"})
    work_id = get_group_id_by_name("Work")
    personal_id = get_group_id_by_name("Personal")

    # Add URL to first group
    client.post(
        "/url/add",
        data={"url": "https://example.com/product", "group_id": str(work_id)},
    )

    # Add same URL to second group - should succeed
    response = client.post(
        "/url/add",
        data={"url": "https://example.com/product", "group_id": str(personal_id)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"URL added successfully!" in response.data


# --- Feature: Product Name ---


def test_add_url_with_name(client: FlaskClient) -> None:
    """Test adding a URL with an optional product name."""
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")

    response = client.post(
        "/url/add",
        data={
            "url": "https://example.com/product",
            "group_id": str(group_id),
            "name": "My Product",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"URL added successfully!" in response.data
    assert b"My Product" in response.data


def test_add_url_without_name(client: FlaskClient) -> None:
    """Test adding a URL without a product name shows URL instead."""
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")

    response = client.post(
        "/url/add",
        data={"url": "https://example.com/product", "group_id": str(group_id)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"https://example.com/product" in response.data


def test_update_url_with_name(client: FlaskClient) -> None:
    """Test updating a URL to add a product name."""
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")
    client.post(
        "/url/add", data={"url": "https://example.com", "group_id": str(group_id)}
    )

    url_id = get_url_id_by_url("https://example.com")

    response = client.post(
        f"/url/update/{url_id}",
        data={"url": "https://example.com", "name": "My Product"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"URL updated successfully!" in response.data
    assert b"My Product" in response.data


def test_update_url_preserves_name(client: FlaskClient) -> None:
    """Test that updating a URL name is stored in the database."""
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")
    client.post(
        "/url/add",
        data={
            "url": "https://example.com",
            "group_id": str(group_id),
            "name": "Original Name",
        },
    )

    # Verify name is stored
    urls_file = Path("urls.json")
    urls_data = json.loads(urls_file.read_text())
    assert urls_data[0]["name"] == "Original Name"

    url_id = get_url_id_by_url("https://example.com")

    # Update with new name
    client.post(
        f"/url/update/{url_id}",
        data={"url": "https://example.com", "name": "Updated Name"},
    )

    urls_data = json.loads(urls_file.read_text())
    assert urls_data[0]["name"] == "Updated Name"


def test_update_url_clear_name(client: FlaskClient) -> None:
    """Test that clearing the name field removes the name."""
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")
    client.post(
        "/url/add",
        data={
            "url": "https://example.com",
            "group_id": str(group_id),
            "name": "My Product",
        },
    )

    url_id = get_url_id_by_url("https://example.com")

    # Clear the name
    client.post(
        f"/url/update/{url_id}",
        data={"url": "https://example.com", "name": ""},
    )

    urls_file = Path("urls.json")
    urls_data = json.loads(urls_file.read_text())
    assert urls_data[0]["name"] is None


def test_url_name_displayed_with_url_reveal(client: FlaskClient) -> None:
    """Test that when a name is set, URL is available via reveal toggle."""
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")
    client.post(
        "/url/add",
        data={
            "url": "https://example.com/product",
            "group_id": str(group_id),
            "name": "Cool Product",
        },
        follow_redirects=True,
    )

    response = client.get("/")
    assert b"Cool Product" in response.data
    assert b"url-reveal" in response.data
    assert b"url-small-link" in response.data


def test_url_without_name_shows_derived_name(client: FlaskClient) -> None:
    """Test that URLs without a manual name show an auto-derived name."""
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")
    client.post(
        "/url/add",
        data={
            "url": "https://www.jula.se/catalog/hammare-123",
            "group_id": str(group_id),
        },
        follow_redirects=True,
    )

    response = client.get("/")
    # Should show auto-derived name instead of raw URL
    assert "jula.se".encode() in response.data
    assert "hammare 123".encode() in response.data


def test_derive_name_filter_domain_only(app: Flask) -> None:
    """Test derive_name_from_url filter with domain-only URL."""
    with app.app_context():
        env = app.jinja_env
        derive = env.filters["derive_name_from_url"]
        assert derive("https://www.example.com") == "example.com"
        assert derive("https://www.example.com/") == "example.com"


def test_derive_name_filter_with_path(app: Flask) -> None:
    """Test derive_name_from_url filter with path segments."""
    with app.app_context():
        env = app.jinja_env
        derive = env.filters["derive_name_from_url"]
        result = derive("https://www.jula.se/catalog/snickarhammer-029205")
        assert result == "jula.se \u2014 snickarhammer 029205"


def test_url_reveal_toggle_present(client: FlaskClient) -> None:
    """Test that the URL reveal toggle button is present for tracked URLs."""
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")
    client.post(
        "/url/add",
        data={
            "url": "https://example.com/product",
            "group_id": str(group_id),
            "name": "My Product",
        },
        follow_redirects=True,
    )

    response = client.get("/")
    assert b"toggleUrlReveal" in response.data
