"""Flask application for URL management with groups."""

import uuid
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from flask import Flask, redirect, render_template, request, url_for, flash
from flask.wrappers import Response
from typed_json_db import IndexedJsonDB
from werkzeug.wrappers import Response as WerkzeugResponse


@dataclass
class Group:
    """Group dataclass for persistence."""

    id: uuid.UUID
    name: str


@dataclass
class URL:
    """URL dataclass for persistence."""

    id: uuid.UUID
    url: str
    group_id: uuid.UUID
    current_price: Optional[float] = None
    last_price_change: Optional[str] = None  # ISO format datetime string


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.secret_key = "dev-secret-key-change-in-production"

    # Initialize database paths
    groups_db_path = Path("groups.json")
    urls_db_path = Path("urls.json")

    def get_groups_db() -> IndexedJsonDB[Group, uuid.UUID]:
        """Get a fresh groups database instance."""
        return IndexedJsonDB(Group, groups_db_path, primary_key="id")

    def get_urls_db() -> IndexedJsonDB[URL, uuid.UUID]:
        """Get a fresh URLs database instance."""
        return IndexedJsonDB(URL, urls_db_path, primary_key="id")

    @app.route("/")
    def index() -> str:
        """Display the list of groups and URLs."""
        groups = get_groups_db().all()
        urls = get_urls_db().all()

        # Organize URLs by group
        urls_by_group: dict[uuid.UUID, list[URL]] = defaultdict(list)
        for url in urls:
            urls_by_group[url.group_id].append(url)

        return render_template("index.html", groups=groups, urls_by_group=urls_by_group)

    # Group routes
    @app.route("/group/add", methods=["POST"])
    def add_group() -> Union[Response, WerkzeugResponse]:
        """Add a new group."""
        group_name = request.form.get("group_name", "").strip()
        if not group_name:
            flash("Group name cannot be empty!", "error")
        else:
            groups_db = get_groups_db()
            # Check for duplicate name
            existing = groups_db.find(name=group_name)
            if existing:
                flash("Group with this name already exists!", "error")
            else:
                new_group = Group(id=uuid.uuid4(), name=group_name)
                groups_db.add(new_group)
                flash("Group added successfully!", "success")
        return redirect(url_for("index"))

    @app.route("/group/update/<uuid:group_id>", methods=["POST"])
    def update_group(group_id: uuid.UUID) -> Union[Response, WerkzeugResponse]:
        """Update/rename a group."""
        group_name = request.form.get("group_name", "").strip()
        if not group_name:
            flash("Group name cannot be empty!", "error")
        else:
            groups_db = get_groups_db()
            existing_group = groups_db.get(group_id)
            if not existing_group:
                flash("Group not found!", "error")
            else:
                # Check for duplicate name (excluding current group)
                duplicates = [g for g in groups_db.find(name=group_name) if g.id != group_id]
                if duplicates:
                    flash("Another group with this name already exists!", "error")
                else:
                    updated_group = Group(id=group_id, name=group_name)
                    groups_db.update(updated_group)
                    flash("Group updated successfully!", "success")
        return redirect(url_for("index"))

    @app.route("/group/delete/<uuid:group_id>", methods=["POST"])
    def delete_group(group_id: uuid.UUID) -> Union[Response, WerkzeugResponse]:
        """Delete a group (only if it has no URLs)."""
        urls_db = get_urls_db()
        # Check if group has any URLs
        urls_in_group = urls_db.find(group_id=group_id)
        if urls_in_group:
            flash("Cannot delete group with URLs! Remove all URLs first.", "error")
        else:
            groups_db = get_groups_db()
            if groups_db.remove(group_id):
                flash("Group deleted successfully!", "success")
            else:
                flash("Group not found!", "error")
        return redirect(url_for("index"))

    # URL routes
    @app.route("/url/add", methods=["POST"])
    def add_url() -> Union[Response, WerkzeugResponse]:
        """Add a new URL to a group."""
        url_input = request.form.get("url", "").strip()
        group_id_str = request.form.get("group_id", "")

        if not url_input:
            flash("URL cannot be empty!", "error")
        elif not group_id_str:
            flash("Please select a group!", "error")
        else:
            try:
                group_id = uuid.UUID(group_id_str)
            except ValueError:
                flash("Invalid group ID!", "error")
                return redirect(url_for("index"))

            groups_db = get_groups_db()
            # Verify group exists
            if not groups_db.get(group_id):
                flash("Group does not exist!", "error")
            else:
                new_url = URL(
                    id=uuid.uuid4(),
                    url=url_input,
                    group_id=group_id,
                )
                urls_db = get_urls_db()
                urls_db.add(new_url)
                flash("URL added successfully!", "success")
        return redirect(url_for("index"))

    @app.route("/url/update/<uuid:url_id>", methods=["POST"])
    def update_url(url_id: uuid.UUID) -> Union[Response, WerkzeugResponse]:
        """Update an existing URL."""
        url_input = request.form.get("url", "").strip()
        if not url_input:
            flash("URL cannot be empty!", "error")
        else:
            urls_db = get_urls_db()
            existing_url = urls_db.get(url_id)
            if not existing_url:
                flash("URL not found!", "error")
            else:
                updated_url = URL(
                    id=url_id,
                    url=url_input,
                    group_id=existing_url.group_id,
                    current_price=existing_url.current_price,
                    last_price_change=existing_url.last_price_change,
                )
                urls_db.update(updated_url)
                flash("URL updated successfully!", "success")
        return redirect(url_for("index"))

    @app.route("/url/delete/<uuid:url_id>", methods=["POST"])
    def delete_url(url_id: uuid.UUID) -> Union[Response, WerkzeugResponse]:
        """Delete a URL from a group."""
        urls_db = get_urls_db()
        if urls_db.remove(url_id):
            flash("URL deleted successfully!", "success")
        else:
            flash("URL not found!", "error")
        return redirect(url_for("index"))

    return app
