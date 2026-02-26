"""Playwright end-to-end tests for the Prisbevakaren web application."""

import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page, expect
from typed_json_db import IndexedJsonDB

from src.app import URL
from tests.conftest import LiveServer


def _expand_add_group_section(page: Page) -> None:
    """Expand the collapsible Add Group section."""
    page.locator(".collapse-trigger").click()


def _create_group(page: Page, name: str) -> None:
    """Helper to create a group via the UI."""
    _expand_add_group_section(page)
    page.get_by_placeholder("Enter group name...").fill(name)
    page.get_by_role("button", name="Create Group").click()


def _add_url(page: Page, url: str, group_name: str, name: str = "Test Product") -> None:
    """Helper to add a URL to a group via the UI."""
    page.get_by_placeholder("Product name...").fill(name)
    page.get_by_placeholder(re.compile("product URL")).fill(url)
    page.get_by_role("combobox").select_option(label=group_name)
    page.get_by_role("button", name="Track").click()


def _set_price_fields(
    tmp_path: Path,
    current_price: Optional[float] = None,
    previous_price: Optional[float] = None,
    last_price_change: Optional[str] = None,
) -> None:
    """Set price fields on the first URL in the database using the db object."""
    urls_db: IndexedJsonDB[URL, uuid.UUID] = IndexedJsonDB(
        URL, tmp_path / "urls.json", primary_key="id"
    )
    url_entry = urls_db.all()[0]
    updated = URL(
        id=url_entry.id,
        url=url_entry.url,
        group_id=url_entry.group_id,
        name=url_entry.name,
        current_price=current_price,
        previous_price=previous_price,
        last_price_change=last_price_change,
    )
    urls_db.update(updated)


def test_index_page_loads(page: Page, live_server: LiveServer) -> None:
    """Test that the index page loads and shows the empty state."""
    page.goto(live_server.url)
    expect(page).to_have_title("Prisbevakaren")
    expect(page.locator("h1")).to_have_text("Price Tracker")
    expect(page.get_by_text("No groups yet")).to_be_visible()


def test_add_group(page: Page, live_server: LiveServer) -> None:
    """Test adding a new group via the UI."""
    page.goto(live_server.url)
    _create_group(page, "Test Group")

    # Verify group was added
    expect(page.get_by_text("Group added successfully!")).to_be_visible()
    expect(page.locator(".group-name", has_text="Test Group")).to_be_visible()


def test_add_group_empty_name(page: Page, live_server: LiveServer) -> None:
    """Test that adding a group with empty name shows an error."""
    page.goto(live_server.url)

    # Expand the Add Group section
    _expand_add_group_section(page)

    # Remove the required attribute to allow submitting empty form
    page.get_by_placeholder("Enter group name...").evaluate(
        "el => el.removeAttribute('required')"
    )
    page.get_by_role("button", name="Create Group").click()

    # Verify error is shown
    expect(page.get_by_text("Group name cannot be empty!")).to_be_visible()


def test_add_url_to_group(page: Page, live_server: LiveServer) -> None:
    """Test adding a URL to an existing group."""
    page.goto(live_server.url)
    _create_group(page, "Shopping")
    _add_url(page, "https://example.com", "Shopping")

    # Verify URL was added
    expect(page.get_by_text("URL added successfully!")).to_be_visible()
    expect(page.get_by_text("https://example.com")).to_be_visible()


def test_delete_url(page: Page, live_server: LiveServer) -> None:
    """Test deleting a URL from a group."""
    page.goto(live_server.url)
    _create_group(page, "Test Group")
    _add_url(page, "https://example.com", "Test Group")

    # Delete the URL (accept the confirmation dialog)
    page.on("dialog", lambda dialog: dialog.accept())
    page.locator(".url-item").get_by_title("Delete").click()

    # Verify URL was deleted
    expect(page.get_by_text("URL deleted successfully!")).to_be_visible()


def test_delete_empty_group(page: Page, live_server: LiveServer) -> None:
    """Test deleting an empty group."""
    page.goto(live_server.url)
    _create_group(page, "Empty Group")

    # Delete the group (accept the confirmation dialog)
    page.on("dialog", lambda dialog: dialog.accept())
    page.locator(".group-top").get_by_title("Delete").click()

    # Verify group was deleted
    expect(page.get_by_text("Group deleted successfully!")).to_be_visible()
    expect(page.get_by_text("No groups yet")).to_be_visible()


def test_cannot_delete_group_with_urls(page: Page, live_server: LiveServer) -> None:
    """Test that a group with URLs cannot be deleted."""
    page.goto(live_server.url)
    _create_group(page, "Non-Empty Group")
    _add_url(page, "https://example.com", "Non-Empty Group")

    # Try to delete the group (accept the confirmation dialog)
    page.on("dialog", lambda dialog: dialog.accept())
    page.locator(".group-top").get_by_title("Delete").click()

    # Verify error is shown
    expect(page.get_by_text("Cannot delete group with URLs!")).to_be_visible()


def test_rename_group(page: Page, live_server: LiveServer) -> None:
    """Test renaming a group."""
    page.goto(live_server.url)
    _create_group(page, "Old Name")

    # Click the edit button for the group
    page.get_by_title("Rename").click()

    # Fill in the new name and save
    page.locator(".group-edit input[name='group_name']").fill("New Name")
    page.get_by_title("Save").click()

    # Verify group was renamed
    expect(page.get_by_text("Group updated successfully!")).to_be_visible()
    expect(page.locator(".group-name", has_text="New Name")).to_be_visible()


def test_multiple_groups_and_urls(page: Page, live_server: LiveServer) -> None:
    """Test creating multiple groups with URLs."""
    page.goto(live_server.url)
    _create_group(page, "Work")
    _create_group(page, "Personal")

    # Add URL to Work group
    _add_url(page, "https://work.example.com", "Work")

    # Add URL to Personal group
    _add_url(page, "https://personal.example.com", "Personal")

    # Verify both groups and URLs are visible
    expect(page.locator(".group-name", has_text="Work")).to_be_visible()
    expect(page.locator(".group-name", has_text="Personal")).to_be_visible()
    expect(page.get_by_role("link", name="https://work.example.com")).to_be_visible()
    expect(
        page.get_by_role("link", name="https://personal.example.com")
    ).to_be_visible()


def test_url_displays_current_price(page: Page, live_server: LiveServer) -> None:
    """Test that a URL with a current price displays it correctly."""
    page.goto(live_server.url)
    _create_group(page, "Shopping")
    _add_url(page, "https://shop.com/item", "Shopping")

    # Set price data directly in the database
    _set_price_fields(live_server.tmp_path, current_price=99.99)

    # Reload the page to see the price
    page.reload()

    expect(page.get_by_text("99.99 kr")).to_be_visible()


def test_url_displays_price_increase(page: Page, live_server: LiveServer) -> None:
    """Test that a price increase shows a positive diff in the UI."""
    page.goto(live_server.url)
    _create_group(page, "Shopping")
    _add_url(page, "https://shop.com/item", "Shopping")

    # Set current > previous to simulate price increase
    _set_price_fields(
        live_server.tmp_path,
        current_price=55.00,
        previous_price=50.00,
        last_price_change="2025-12-18T00:00:00+00:00",
    )

    page.reload()

    expect(page.get_by_text("55.00 kr")).to_be_visible()
    expect(page.get_by_text("(+5.00 kr)")).to_be_visible()


def test_url_displays_price_decrease(page: Page, live_server: LiveServer) -> None:
    """Test that a price decrease shows a negative diff in the UI."""
    page.goto(live_server.url)
    _create_group(page, "Shopping")
    _add_url(page, "https://shop.com/item", "Shopping")

    # Set current < previous to simulate price decrease
    _set_price_fields(
        live_server.tmp_path,
        current_price=45.00,
        previous_price=50.00,
        last_price_change="2025-12-18T00:00:00+00:00",
    )

    page.reload()

    expect(page.get_by_text("45.00 kr")).to_be_visible()
    expect(page.get_by_text("(-5.00 kr)")).to_be_visible()


def test_url_displays_last_price_change(page: Page, live_server: LiveServer) -> None:
    """Test that the last price change timestamp is displayed."""
    page.goto(live_server.url)
    _create_group(page, "Shopping")
    _add_url(page, "https://shop.com/item", "Shopping")

    five_days_ago = datetime.now(timezone.utc) - timedelta(days=5)
    _set_price_fields(
        live_server.tmp_path,
        current_price=50.00,
        last_price_change=five_days_ago.isoformat(),
    )

    page.reload()

    expect(page.get_by_text("Updated")).to_be_visible()
    expect(page.get_by_text("5 days ago")).to_be_visible()


def test_url_without_price_shows_no_price_info(
    page: Page, live_server: LiveServer
) -> None:
    """Test that a URL without price data does not display price information."""
    page.goto(live_server.url)
    _create_group(page, "Work")
    _add_url(page, "https://example.com", "Work")

    # Verify the URL is shown but no price info appears
    expect(page.get_by_text("https://example.com")).to_be_visible()
    expect(page.locator(".price-tag")).not_to_be_visible()
    expect(page.get_by_text("Updated")).not_to_be_visible()
