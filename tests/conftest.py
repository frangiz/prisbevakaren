"""Shared test fixtures for Playwright E2E tests."""

import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

import pytest
import requests
from werkzeug.serving import make_server

from src.app import create_app


def _find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


def _wait_for_server(url: str, timeout: float = 5.0) -> None:
    """Wait until the server is ready to accept connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            requests.get(url, timeout=1)
            return
        except requests.ConnectionError:
            time.sleep(0.1)
    raise RuntimeError(f"Server at {url} did not start within {timeout}s")


@dataclass
class LiveServer:
    """Holds the live server URL and the temporary database path."""

    url: str
    tmp_path: Path


@pytest.fixture()
def live_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[LiveServer, None, None]:
    """Start a live Flask server for E2E testing.

    Creates a temporary database directory and starts the Flask app
    on a random free port. Yields a LiveServer with the base URL and tmp_path.
    """
    groups_file = tmp_path / "groups.json"
    urls_file = tmp_path / "urls.json"
    groups_file.write_text("[]")
    urls_file.write_text("[]")

    monkeypatch.chdir(tmp_path)

    server = None
    try:
        app = create_app()
        app.config["TESTING"] = True

        port = _find_free_port()
        server = make_server("127.0.0.1", port, app)
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()

        url = f"http://127.0.0.1:{port}"
        _wait_for_server(url)

        yield LiveServer(url=url, tmp_path=tmp_path)
    finally:
        if server is not None:
            server.shutdown()
