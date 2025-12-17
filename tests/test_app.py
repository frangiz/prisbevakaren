"""Tests for app module."""

from pathlib import Path
from typing import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from src.app import create_app, foo


def test_foo_returns_two() -> None:
    """Test that foo function returns 2."""
    result = foo()
    assert result == 2


def test_foo_returns_integer() -> None:
    """Test that foo function returns an integer."""
    result = foo()
    assert isinstance(result, int)


@pytest.fixture
def test_db_path(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary database path for testing."""
    db_file = tmp_path / "test_urls.json"
    db_file.write_text("[]")
    yield db_file
    if db_file.exists():
        db_file.unlink()


@pytest.fixture
def app(test_db_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    """Create a Flask app instance for testing."""
    # Monkey patch the db_path in the create_app function
    monkeypatch.chdir(test_db_path.parent)
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create a test client for the Flask app."""
    return app.test_client()


def test_index_empty(client: FlaskClient) -> None:
    """Test that index page loads with empty URL list."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"No URLs yet" in response.data


def test_add_url(client: FlaskClient, test_db_path: Path) -> None:
    """Test adding a URL."""
    response = client.post(
        "/add", data={"url": "https://example.com"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"URL added successfully!" in response.data
    assert b"https://example.com" in response.data


def test_add_empty_url(client: FlaskClient) -> None:
    """Test adding an empty URL."""
    response = client.post("/add", data={"url": ""}, follow_redirects=True)
    assert response.status_code == 200
    assert b"URL cannot be empty!" in response.data


def test_update_url(client: FlaskClient) -> None:
    """Test updating a URL."""
    # First add a URL
    client.post("/add", data={"url": "https://example.com"})

    # Then update it
    response = client.post(
        "/update/1", data={"url": "https://updated.com"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"URL updated successfully!" in response.data


def test_delete_url(client: FlaskClient) -> None:
    """Test deleting a URL."""
    # First add a URL
    client.post("/add", data={"url": "https://example.com"})

    # Then delete it
    response = client.post("/delete/1", follow_redirects=True)
    assert response.status_code == 200
    assert b"URL deleted successfully!" in response.data


def test_multiple_urls(client: FlaskClient) -> None:
    """Test adding multiple URLs."""
    client.post("/add", data={"url": "https://example1.com"})
    client.post("/add", data={"url": "https://example2.com"})
    client.post("/add", data={"url": "https://example3.com"})

    response = client.get("/")
    assert b"https://example1.com" in response.data
    assert b"https://example2.com" in response.data
    assert b"https://example3.com" in response.data
