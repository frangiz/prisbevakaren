"""Flask application for URL management with groups."""

import os
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from flask import Flask, redirect, render_template, request, url_for, flash
from flask.wrappers import Response
from typed_json_db import IndexedJsonDB
from werkzeug.wrappers import Response as WerkzeugResponse

from src.price_scraper import PriceScraper

# Constants
GROUPS_DB_PATH = Path("groups.json")
URLS_DB_PATH = Path("urls.json")
FLASH_ERROR = "error"
FLASH_SUCCESS = "success"


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
    previous_price: Optional[float] = None
    last_price_change: Optional[str] = None  # ISO format datetime string


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "dev-secret-key-change-in-production"
    )
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max request size

    @app.template_filter("format_timestamp")
    def format_timestamp(iso_string: Optional[str]) -> str:
        """Convert ISO format timestamp to relative time format."""
        if not iso_string:
            return ""
        try:
            dt = datetime.fromisoformat(iso_string)
            now = datetime.now(dt.tzinfo)  # Use same timezone as the stored datetime
            diff = now - dt

            days = diff.days

            if days == 0:
                return "today"
            elif days == 1:
                return "1 day ago"
            elif days < 30:
                return f"{days} days ago"
            elif days < 60:
                return "1 month ago"
            else:
                months = days // 30
                return f"{months} months ago"
        except (ValueError, AttributeError):
            return iso_string  # Return original if parsing fails

    @app.template_filter("format_timestamp_absolute")
    def format_timestamp_absolute(iso_string: Optional[str]) -> str:
        """Convert ISO format timestamp to absolute readable format for tooltips."""
        if not iso_string:
            return ""
        try:
            dt = datetime.fromisoformat(iso_string)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            return iso_string  # Return original if parsing fails

    def get_groups_db() -> IndexedJsonDB[Group, uuid.UUID]:
        """Get a fresh groups database instance."""
        return IndexedJsonDB(Group, GROUPS_DB_PATH, primary_key="id")

    def get_urls_db() -> IndexedJsonDB[URL, uuid.UUID]:
        """Get a fresh URLs database instance."""
        return IndexedJsonDB(URL, URLS_DB_PATH, primary_key="id")

    def is_duplicate_group_name(
        name: str, exclude_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Check if a group name already exists, optionally excluding a specific group ID."""
        groups_db = get_groups_db()
        existing = groups_db.find(name=name)
        if not existing:
            return False
        if exclude_id is None:
            return True
        return any(g.id != exclude_id for g in existing)

    def validate_non_empty_input(value: str, field_name: str) -> bool:
        """Validate that input is not empty. Flash error and return False if empty."""
        if not value:
            flash(f"{field_name} cannot be empty!", FLASH_ERROR)
            return False
        return True

    def validate_group_exists(group_id: uuid.UUID) -> bool:
        """Validate that a group exists. Flash error and return False if not found."""
        groups_db = get_groups_db()
        if not groups_db.get(group_id):
            flash("Group does not exist!", FLASH_ERROR)
            return False
        return True

    def is_duplicate_url_in_group(url: str, group_id: uuid.UUID) -> bool:
        """Check if a URL already exists in the given group."""
        urls_db = get_urls_db()
        existing = urls_db.find(group_id=group_id)
        return any(u.url == url for u in existing)

    def parse_uuid(uuid_str: str, field_name: str = "ID") -> Optional[uuid.UUID]:
        """Parse UUID from string. Flash error and return None if invalid."""
        try:
            return uuid.UUID(uuid_str)
        except ValueError:
            flash(f"Invalid {field_name}!", FLASH_ERROR)
            return None

    def create_updated_url(existing_url: URL, new_url_string: str) -> URL:
        """Create an updated URL object, preserving price fields from existing URL."""
        return URL(
            id=existing_url.id,
            url=new_url_string,
            group_id=existing_url.group_id,
            current_price=existing_url.current_price,
            previous_price=existing_url.previous_price,
            last_price_change=existing_url.last_price_change,
        )

    @app.route("/")
    def index() -> str:
        """Display the list of groups and URLs."""
        groups = get_groups_db().all()
        urls = get_urls_db().all()

        # Organize URLs by group and sort by price (lowest first, None last)
        urls_by_group: dict[uuid.UUID, list[URL]] = defaultdict(list)
        for url in urls:
            urls_by_group[url.group_id].append(url)
        for group_id in urls_by_group:
            urls_by_group[group_id].sort(
                key=lambda u: (u.current_price is None, u.current_price or 0)
            )

        return render_template("index.html", groups=groups, urls_by_group=urls_by_group)

    # Group routes
    @app.route("/group/add", methods=["POST"])
    def add_group() -> Union[Response, WerkzeugResponse]:
        """Add a new group."""
        group_name = request.form.get("group_name", "").strip()
        if not validate_non_empty_input(group_name, "Group name"):
            return redirect(url_for("index"))

        if is_duplicate_group_name(group_name):
            flash("Group with this name already exists!", FLASH_ERROR)
            return redirect(url_for("index"))

        new_group = Group(id=uuid.uuid4(), name=group_name)
        groups_db = get_groups_db()
        groups_db.add(new_group)
        flash("Group added successfully!", FLASH_SUCCESS)
        return redirect(url_for("index"))

    @app.route("/group/update/<uuid:group_id>", methods=["POST"])
    def update_group(group_id: uuid.UUID) -> Union[Response, WerkzeugResponse]:
        """Update/rename a group."""
        group_name = request.form.get("group_name", "").strip()
        if not validate_non_empty_input(group_name, "Group name"):
            return redirect(url_for("index"))

        groups_db = get_groups_db()
        existing_group = groups_db.get(group_id)
        if not existing_group:
            flash("Group not found!", FLASH_ERROR)
            return redirect(url_for("index"))

        if is_duplicate_group_name(group_name, exclude_id=group_id):
            flash("Another group with this name already exists!", FLASH_ERROR)
            return redirect(url_for("index"))

        updated_group = Group(id=group_id, name=group_name)
        groups_db.update(updated_group)
        flash("Group updated successfully!", FLASH_SUCCESS)
        return redirect(url_for("index"))

    @app.route("/group/delete/<uuid:group_id>", methods=["POST"])
    def delete_group(group_id: uuid.UUID) -> Union[Response, WerkzeugResponse]:
        """Delete a group (only if it has no URLs)."""
        urls_db = get_urls_db()
        urls_in_group = urls_db.find(group_id=group_id)
        if urls_in_group:
            flash("Cannot delete group with URLs! Remove all URLs first.", FLASH_ERROR)
            return redirect(url_for("index"))

        groups_db = get_groups_db()
        if groups_db.remove(group_id):
            flash("Group deleted successfully!", FLASH_SUCCESS)
        else:
            flash("Group not found!", FLASH_ERROR)
        return redirect(url_for("index"))

    # URL routes
    @app.route("/url/add", methods=["POST"])
    def add_url() -> Union[Response, WerkzeugResponse]:
        """Add a new URL to a group."""
        url_input = request.form.get("url", "").strip()
        group_id_str = request.form.get("group_id", "")

        if not validate_non_empty_input(url_input, "URL"):
            return redirect(url_for("index"))

        if not group_id_str:
            flash("Please select a group!", FLASH_ERROR)
            return redirect(url_for("index"))

        group_id = parse_uuid(group_id_str, "group ID")
        if group_id is None:
            return redirect(url_for("index"))

        if not validate_group_exists(group_id):
            return redirect(url_for("index"))

        if is_duplicate_url_in_group(url_input, group_id):
            flash("This URL already exists in the selected group!", FLASH_ERROR)
            return redirect(url_for("index"))

        new_url = URL(
            id=uuid.uuid4(),
            url=url_input,
            group_id=group_id,
        )
        urls_db = get_urls_db()
        urls_db.add(new_url)
        flash("URL added successfully!", FLASH_SUCCESS)
        return redirect(url_for("index"))

    @app.route("/url/update/<uuid:url_id>", methods=["POST"])
    def update_url(url_id: uuid.UUID) -> Union[Response, WerkzeugResponse]:
        """Update an existing URL."""
        url_input = request.form.get("url", "").strip()
        if not validate_non_empty_input(url_input, "URL"):
            return redirect(url_for("index"))

        urls_db = get_urls_db()
        existing_url = urls_db.get(url_id)
        if not existing_url:
            flash("URL not found!", FLASH_ERROR)
            return redirect(url_for("index"))

        updated_url = create_updated_url(existing_url, url_input)
        urls_db.update(updated_url)
        flash("URL updated successfully!", FLASH_SUCCESS)
        return redirect(url_for("index"))

    @app.route("/url/delete/<uuid:url_id>", methods=["POST"])
    def delete_url(url_id: uuid.UUID) -> Union[Response, WerkzeugResponse]:
        """Delete a URL from a group."""
        urls_db = get_urls_db()
        if urls_db.remove(url_id):
            flash("URL deleted successfully!", FLASH_SUCCESS)
        else:
            flash("URL not found!", FLASH_ERROR)
        return redirect(url_for("index"))

    @app.route("/url/refresh/<uuid:url_id>", methods=["POST"])
    def refresh_url_price(url_id: uuid.UUID) -> Union[Response, WerkzeugResponse]:
        """Manually refresh the price for a single URL."""
        urls_db = get_urls_db()
        url_obj = urls_db.get(url_id)
        if not url_obj:
            flash("URL not found!", FLASH_ERROR)
            return redirect(url_for("index"))

        with PriceScraper() as scraper:
            new_price = scraper.fetch_price(url_obj.url)

        if new_price is None:
            flash("Failed to fetch price for this URL.", FLASH_ERROR)
            return redirect(url_for("index"))

        if url_obj.current_price != new_price:
            url_obj.previous_price = url_obj.current_price
            url_obj.current_price = new_price
            url_obj.last_price_change = datetime.now(timezone.utc).isoformat()
            urls_db.update(url_obj)
            flash(f"Price updated to {new_price:.2f} kr!", FLASH_SUCCESS)
        else:
            flash(f"Price unchanged at {new_price:.2f} kr.", FLASH_SUCCESS)

        return redirect(url_for("index"))

    return app
