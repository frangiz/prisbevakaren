"""Shared test fixtures for Playwright E2E tests."""

import os
import socket
import threading
from pathlib import Path
from typing import Generator

import pytest
from werkzeug.serving import make_server

from src.app import create_app


def _find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


@pytest.fixture()
def live_server(tmp_path: Path) -> Generator[str, None, None]:
    """Start a live Flask server for E2E testing.

    Creates a temporary database directory and starts the Flask app
    on a random free port. Yields the base URL of the running server.
    """
    groups_file = tmp_path / "groups.json"
    urls_file = tmp_path / "urls.json"
    groups_file.write_text("[]")
    urls_file.write_text("[]")

    original_cwd = Path.cwd()
    os.chdir(tmp_path)

    app = create_app()
    app.config["TESTING"] = True

    port = _find_free_port()
    server = make_server("127.0.0.1", port, app)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        os.chdir(original_cwd)
