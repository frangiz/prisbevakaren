"""Flask application for URL management with groups."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from flask import Flask, redirect, render_template, request, url_for, flash
from flask.wrappers import Response
from typed_json_db import JsonDB
from werkzeug.wrappers import Response as WerkzeugResponse


@dataclass
class Group:
    """Group dataclass for persistence."""

    id: int
    name: str


@dataclass
class URL:
    """URL dataclass for persistence."""

    id: int
    url: str
    group_id: int
    current_price: float | None = None
    last_price_change: str | None = None


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.secret_key = "dev-secret-key-change-in-production"

    # Initialize databases
    groups_db_path = Path("groups.json")
    urls_db_path = Path("urls.json")
    groups_db = JsonDB(Group, groups_db_path)
    urls_db = JsonDB(URL, urls_db_path)

    @app.route("/")
    def index() -> str:
        """Display the list of groups and URLs."""
        # Reload databases to get fresh data (in case external script updated prices)
        fresh_groups_db = JsonDB(Group, groups_db_path)
        fresh_urls_db = JsonDB(URL, urls_db_path)
        groups = fresh_groups_db.all()
        urls = fresh_urls_db.all()

        # Organize URLs by group
        urls_by_group: dict[int, list[URL]] = {}
        for url in urls:
            if url.group_id not in urls_by_group:
                urls_by_group[url.group_id] = []
            urls_by_group[url.group_id].append(url)

        return render_template("index.html", groups=groups, urls_by_group=urls_by_group)

    # Group routes
    @app.route("/group/add", methods=["POST"])
    def add_group() -> Union[Response, WerkzeugResponse]:
        """Add a new group."""
        group_name = request.form.get("group_name", "").strip()
        if group_name:
            existing_groups = groups_db.all()
            next_id = max([g.id for g in existing_groups], default=0) + 1
            new_group = Group(id=next_id, name=group_name)
            groups_db.add(new_group)
            flash("Group added successfully!", "success")
        else:
            flash("Group name cannot be empty!", "error")
        return redirect(url_for("index"))

    @app.route("/group/update/<int:group_id>", methods=["POST"])
    def update_group(group_id: int) -> Union[Response, WerkzeugResponse]:
        """Update/rename a group."""
        group_name = request.form.get("group_name", "").strip()
        if group_name:
            groups = groups_db.all()
            updated_groups = [
                Group(id=g.id, name=group_name) if g.id == group_id else g
                for g in groups
            ]
            with open(groups_db_path, "w") as f:
                json.dump(
                    [{"id": g.id, "name": g.name} for g in updated_groups], f, indent=2
                )
            flash("Group updated successfully!", "success")
        else:
            flash("Group name cannot be empty!", "error")
        return redirect(url_for("index"))

    @app.route("/group/delete/<int:group_id>", methods=["POST"])
    def delete_group(group_id: int) -> Union[Response, WerkzeugResponse]:
        """Delete a group (only if it has no URLs)."""
        urls = urls_db.all()
        # Check if group has any URLs
        urls_in_group = [u for u in urls if u.group_id == group_id]
        if urls_in_group:
            flash("Cannot delete group with URLs! Remove all URLs first.", "error")
        else:
            groups = groups_db.all()
            updated_groups = [g for g in groups if g.id != group_id]
            if len(updated_groups) < len(groups):
                with open(groups_db_path, "w") as f:
                    json.dump(
                        [{"id": g.id, "name": g.name} for g in updated_groups],
                        f,
                        indent=2,
                    )
                flash("Group deleted successfully!", "success")
        return redirect(url_for("index"))

    # URL routes
    @app.route("/url/add", methods=["POST"])
    def add_url() -> Union[Response, WerkzeugResponse]:
        """Add a new URL to a group."""
        url_input = request.form.get("url", "").strip()
        group_id = request.form.get("group_id", type=int)

        if not url_input:
            flash("URL cannot be empty!", "error")
        elif group_id is None:
            flash("Please select a group!", "error")
        else:
            # Verify group exists
            groups = groups_db.all()
            if not any(g.id == group_id for g in groups):
                flash("Group does not exist!", "error")
            else:
                existing_urls = urls_db.all()
                next_id = max([u.id for u in existing_urls], default=0) + 1
                new_url = URL(
                    id=next_id,
                    url=url_input,
                    group_id=group_id,
                    current_price=None,
                    last_price_change=None,
                )
                urls_db.add(new_url)
                flash("URL added successfully!", "success")
        return redirect(url_for("index"))

    @app.route("/url/update/<int:url_id>", methods=["POST"])
    def update_url(url_id: int) -> Union[Response, WerkzeugResponse]:
        """Update an existing URL."""
        url_input = request.form.get("url", "").strip()
        if url_input:
            # Reload database to get fresh data (in case external script updated prices)
            fresh_urls_db = JsonDB(URL, urls_db_path)
            urls = fresh_urls_db.all()
            updated_urls = [
                URL(
                    id=u.id,
                    url=url_input,
                    group_id=u.group_id,
                    current_price=u.current_price,
                    last_price_change=u.last_price_change,
                )
                if u.id == url_id
                else u
                for u in urls
            ]
            with open(urls_db_path, "w") as f:
                json.dump(
                    [
                        {
                            "id": u.id,
                            "url": u.url,
                            "group_id": u.group_id,
                            "current_price": u.current_price,
                            "last_price_change": u.last_price_change,
                        }
                        for u in updated_urls
                    ],
                    f,
                    indent=2,
                )
            flash("URL updated successfully!", "success")
        else:
            flash("URL cannot be empty!", "error")
        return redirect(url_for("index"))

    @app.route("/url/delete/<int:url_id>", methods=["POST"])
    def delete_url(url_id: int) -> Union[Response, WerkzeugResponse]:
        """Delete a URL from a group."""
        # Reload database to get fresh data (in case external script updated prices)
        fresh_urls_db = JsonDB(URL, urls_db_path)
        urls = fresh_urls_db.all()
        updated_urls = [u for u in urls if u.id != url_id]
        if len(updated_urls) < len(urls):
            with open(urls_db_path, "w") as f:
                json.dump(
                    [
                        {
                            "id": u.id,
                            "url": u.url,
                            "group_id": u.group_id,
                            "current_price": u.current_price,
                            "last_price_change": u.last_price_change,
                        }
                        for u in updated_urls
                    ],
                    f,
                    indent=2,
                )
            flash("URL deleted successfully!", "success")
        return redirect(url_for("index"))

    return app
