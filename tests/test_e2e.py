"""Playwright end-to-end tests for the Prisbevakaren web application."""

import re

from playwright.sync_api import Page, expect


def _expand_add_group_section(page: Page) -> None:
    """Expand the collapsible Add Group section."""
    page.locator(".collapsible-header").click()


def _create_group(page: Page, name: str) -> None:
    """Helper to create a group via the UI."""
    _expand_add_group_section(page)
    page.get_by_placeholder("Enter group name").fill(name)
    page.get_by_role("button", name="Add Group").click()


def _add_url(page: Page, url: str, group_name: str) -> None:
    """Helper to add a URL to a group via the UI."""
    page.get_by_placeholder(re.compile("Enter a URL")).fill(url)
    page.get_by_role("combobox").select_option(label=group_name)
    page.get_by_role("button", name="Add URL").click()


def test_index_page_loads(page: Page, live_server: str) -> None:
    """Test that the index page loads and shows the empty state."""
    page.goto(live_server)
    expect(page).to_have_title("URL Manager with Groups")
    expect(page.locator("h1")).to_have_text("Prisbevakaren")
    expect(page.get_by_text("No Groups yet")).to_be_visible()


def test_add_group(page: Page, live_server: str) -> None:
    """Test adding a new group via the UI."""
    page.goto(live_server)
    _create_group(page, "Test Group")

    # Verify group was added
    expect(page.get_by_text("Group added successfully!")).to_be_visible()
    expect(page.locator(".group-name", has_text="Test Group")).to_be_visible()


def test_add_group_empty_name(page: Page, live_server: str) -> None:
    """Test that adding a group with empty name shows an error."""
    page.goto(live_server)

    # Expand the Add Group section
    _expand_add_group_section(page)

    # Remove the required attribute to allow submitting empty form
    page.get_by_placeholder("Enter group name").evaluate(
        "el => el.removeAttribute('required')"
    )
    page.get_by_role("button", name="Add Group").click()

    # Verify error is shown
    expect(page.get_by_text("Group name cannot be empty!")).to_be_visible()


def test_add_url_to_group(page: Page, live_server: str) -> None:
    """Test adding a URL to an existing group."""
    page.goto(live_server)
    _create_group(page, "Shopping")
    _add_url(page, "https://example.com", "Shopping")

    # Verify URL was added
    expect(page.get_by_text("URL added successfully!")).to_be_visible()
    expect(page.get_by_text("https://example.com")).to_be_visible()


def test_delete_url(page: Page, live_server: str) -> None:
    """Test deleting a URL from a group."""
    page.goto(live_server)
    _create_group(page, "Test Group")
    _add_url(page, "https://example.com", "Test Group")

    # Delete the URL (accept the confirmation dialog)
    page.on("dialog", lambda dialog: dialog.accept())
    page.locator(".url-item").get_by_title("Delete").click()

    # Verify URL was deleted
    expect(page.get_by_text("URL deleted successfully!")).to_be_visible()


def test_delete_empty_group(page: Page, live_server: str) -> None:
    """Test deleting an empty group."""
    page.goto(live_server)
    _create_group(page, "Empty Group")

    # Delete the group (accept the confirmation dialog)
    page.on("dialog", lambda dialog: dialog.accept())
    page.locator(".group-header").get_by_title("Delete").click()

    # Verify group was deleted
    expect(page.get_by_text("Group deleted successfully!")).to_be_visible()
    expect(page.get_by_text("No Groups yet")).to_be_visible()


def test_cannot_delete_group_with_urls(page: Page, live_server: str) -> None:
    """Test that a group with URLs cannot be deleted."""
    page.goto(live_server)
    _create_group(page, "Non-Empty Group")
    _add_url(page, "https://example.com", "Non-Empty Group")

    # Try to delete the group (accept the confirmation dialog)
    page.on("dialog", lambda dialog: dialog.accept())
    page.locator(".group-header").get_by_title("Delete").click()

    # Verify error is shown
    expect(page.get_by_text("Cannot delete group with URLs!")).to_be_visible()


def test_rename_group(page: Page, live_server: str) -> None:
    """Test renaming a group."""
    page.goto(live_server)
    _create_group(page, "Old Name")

    # Click the edit button for the group
    page.get_by_title("Rename").click()

    # Fill in the new name and save
    page.locator(".group-edit input[name='group_name']").fill("New Name")
    page.get_by_title("Save").click()

    # Verify group was renamed
    expect(page.get_by_text("Group updated successfully!")).to_be_visible()
    expect(page.locator(".group-name", has_text="New Name")).to_be_visible()


def test_multiple_groups_and_urls(page: Page, live_server: str) -> None:
    """Test creating multiple groups with URLs."""
    page.goto(live_server)
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
