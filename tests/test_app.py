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
    assert b"No Groups yet" in response.data


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
        f"/group/update/{group_id}", data={"group_name": "Personal"}, follow_redirects=True
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
    client.post("/url/add", data={"url": "https://example.com", "group_id": str(group_id)})

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
    client.post("/url/add", data={"url": "https://example.com", "group_id": str(group_id)})

    # Get the URL ID
    url_id = get_url_id_by_url("https://example.com")

    # Update the URL
    response = client.post(
        f"/url/update/{url_id}", data={"url": "https://updated.com"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"URL updated successfully!" in response.data


def test_delete_url(client: FlaskClient) -> None:
    """Test deleting a URL."""
    # Add a group and URL
    client.post("/group/add", data={"group_name": "Work"})
    group_id = get_group_id_by_name("Work")
    client.post("/url/add", data={"url": "https://example.com", "group_id": str(group_id)})

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
    client.post("/url/add", data={"url": "https://personal1.com", "group_id": str(personal_id)})

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
    client.post("/url/add", data={"url": "https://shop.com/item", "group_id": str(group_id)})

    # Manually update the JSON to include price fields (simulating script update)
    urls_file = Path("urls.json")
    urls_data = json.loads(urls_file.read_text())
    urls_data[0]["current_price"] = 99.99
    urls_data[0]["last_price_change"] = "2025-12-18"
    urls_file.write_text(json.dumps(urls_data, indent=2))

    # Verify the price fields are displayed in the UI (database reloads on each request)
    response = client.get("/")
    assert b"Current Price" in response.data
    assert b"99.99" in response.data
    assert b"Last Change" in response.data
    assert b"2025-12-18" in response.data


def test_url_without_price_fields(client: FlaskClient) -> None:
    """Test that URLs without price fields display correctly."""
    # Add a group and URL
    client.post("/group/add", data={"group_name": "Work"})
    group_id = get_group_id_by_name("Work")
    client.post("/url/add", data={"url": "https://example.com", "group_id": str(group_id)})

    # Get the page
    response = client.get("/")

    # URL should be displayed
    assert b"https://example.com" in response.data
    # But price fields should not be shown since they're None
    assert b"Current Price" not in response.data
    assert b"Last Change" not in response.data


def test_url_update_preserves_price_fields(client: FlaskClient) -> None:
    """Test that updating a URL preserves price fields."""
    # Add a group and URL
    client.post("/group/add", data={"group_name": "Shopping"})
    group_id = get_group_id_by_name("Shopping")
    client.post("/url/add", data={"url": "https://shop.com/item1", "group_id": str(group_id)})

    # Manually add price fields (simulating script update)
    urls_file = Path("urls.json")
    urls_data = json.loads(urls_file.read_text())
    urls_data[0]["current_price"] = 49.99
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
    assert urls_data[0]["last_price_change"] == "2025-12-15"
