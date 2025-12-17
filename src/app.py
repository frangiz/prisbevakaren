"""Flask application for URL management."""

from dataclasses import dataclass
from pathlib import Path
from typing import Union

from flask import Flask, redirect, render_template, request, url_for, flash
from flask.wrappers import Response
from typed_json_db import JsonDB
from werkzeug.wrappers import Response as WerkzeugResponse


@dataclass
class URL:
    """URL dataclass for persistence."""

    id: int
    url: str


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.secret_key = "dev-secret-key-change-in-production"

    # Initialize database
    db_path = Path("urls.json")
    db = JsonDB(URL, db_path)

    @app.route("/")
    def index() -> str:
        """Display the list of URLs."""
        urls = db.all()
        return render_template("index.html", urls=urls)

    @app.route("/add", methods=["POST"])
    def add_url() -> Union[Response, WerkzeugResponse]:
        """Add a new URL to the list."""
        url_input = request.form.get("url", "").strip()
        if url_input:
            # Get the next ID
            existing_urls = db.all()
            next_id = max([u.id for u in existing_urls], default=0) + 1

            new_url = URL(id=next_id, url=url_input)
            db.add(new_url)
            flash("URL added successfully!", "success")
        else:
            flash("URL cannot be empty!", "error")
        return redirect(url_for("index"))

    @app.route("/update/<int:url_id>", methods=["POST"])
    def update_url(url_id: int) -> Union[Response, WerkzeugResponse]:
        """Update an existing URL."""
        url_input = request.form.get("url", "").strip()
        if url_input:
            urls = db.all()
            updated_urls = [
                URL(id=u.id, url=url_input) if u.id == url_id else u for u in urls
            ]
            # Save the updated list
            import json

            with open(db_path, "w") as f:
                json.dump(
                    [{"id": u.id, "url": u.url} for u in updated_urls], f, indent=2
                )
            flash("URL updated successfully!", "success")
        else:
            flash("URL cannot be empty!", "error")
        return redirect(url_for("index"))

    @app.route("/delete/<int:url_id>", methods=["POST"])
    def delete_url(url_id: int) -> Union[Response, WerkzeugResponse]:
        """Delete a URL from the list."""
        urls = db.all()
        updated_urls = [u for u in urls if u.id != url_id]
        if len(updated_urls) < len(urls):
            # Save the updated list
            import json

            with open(db_path, "w") as f:
                json.dump(
                    [{"id": u.id, "url": u.url} for u in updated_urls], f, indent=2
                )
            flash("URL deleted successfully!", "success")
        return redirect(url_for("index"))

    return app


def foo() -> int:
    """Legacy function for backward compatibility."""
    return 2
