"""Slack notification module for sending error alerts."""

import os
from typing import Optional

import requests


def send_error_notification(message: str, details: Optional[str] = None) -> bool:
    """Send an error notification to Slack.

    Args:
        message: The main error message
        details: Optional additional details about the error

    Returns:
        True if notification was sent successfully, False otherwise
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")

    if not webhook_url:
        # Silently skip if webhook is not configured
        return False

    try:
        # Format the message
        text = f"🚨 *Error in Prisbevakaren*\n\n{message}"
        if details:
            text += f"\n\n*Details:*\n```{details}```"

        payload = {
            "text": text,
            "username": "Prisbevakaren Bot",
            "icon_emoji": ":warning:",
        }

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        return True

    except Exception as e:
        # Don't let notification failures break the main application
        print(f"Failed to send Slack notification: {e}")
        return False


def send_summary_notification(
    title: str, total: int, succeeded: int, failed: int, details: Optional[str] = None
) -> bool:
    """Send a summary notification to Slack.

    Args:
        title: The title of the summary
        total: Total items processed
        succeeded: Number of successful operations
        failed: Number of failed operations
        details: Optional additional details

    Returns:
        True if notification was sent successfully, False otherwise
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")

    if not webhook_url:
        return False

    try:
        # Choose emoji based on results
        emoji = "✅" if failed == 0 else "⚠️" if failed < total else "❌"

        text = f"{emoji} *{title}*\n\n"
        text += f"Total: {total}\n"
        text += f"Succeeded: {succeeded}\n"
        text += f"Failed: {failed}"

        if details:
            text += f"\n\n*Details:*\n{details}"

        payload = {
            "text": text,
            "username": "Prisbevakaren Bot",
            "icon_emoji": ":bar_chart:",
        }

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        return True

    except Exception as e:
        print(f"Failed to send Slack notification: {e}")
        return False
