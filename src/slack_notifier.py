"""Slack notification module for sending error alerts."""

import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from src.config import SlackConfig


class Slack:
    """Slack client for sending notifications."""

    def __init__(self, config: SlackConfig):
        """Initialize Slack client.

        Args:
            config: SlackConfig with bot_token and channel_id
        """
        self.logger = logging.getLogger(__name__)
        self.client = WebClient(token=config.bot_token)
        self.channel_id = config.channel_id

    def post_warn_to_slack(self, message: str) -> None:
        """Post a warning message to Slack.

        Args:
            message: Warning message to post
        """
        try:
            _ = self.client.chat_postMessage(
                channel=self.channel_id, text=f":warning: {message}"
            )
            self.logger.info(f"Posting warning message to Slack: {message[:200]}")
        except SlackApiError as e:
            self.logger.error(f"Error posting warning to Slack: {e}")

    def post_message_to_slack(self, message: str) -> None:
        """Post a message to Slack.

        Args:
            message: Message to post
        """
        try:
            _ = self.client.chat_postMessage(channel=self.channel_id, text=message)
            self.logger.info(f"Posting message to Slack: {message[:200]}")
        except SlackApiError as e:
            self.logger.error(f"Error posting message to Slack: {e}")

    def log_message(self, level_name: str, message: str) -> None:
        """Post a log message to Slack with appropriate emoji.

        Args:
            level_name: Log level (WARNING, ERROR, CRITICAL)
            message: Log message to post
        """
        prefix = {"WARNING": ":warning:", "ERROR": ":x:", "CRITICAL": ":exclamation:"}
        try:
            _ = self.client.chat_postMessage(
                channel=self.channel_id, text=f"{prefix[level_name]} {message}"
            )
        except SlackApiError as e:
            self.logger.error(f"Error posting log message to Slack: {e}")


class SlackHandler(logging.Handler):
    """Custom Slack logging handler."""

    def __init__(self, config: SlackConfig):
        """Initialize Slack logging handler.

        Args:
            config: SlackConfig with bot_token and channel_id
        """
        super().__init__()
        self.slack = Slack(config)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to Slack.

        Args:
            record: Log record to emit
        """
        # Prevent recursion: don't handle logs from slack_sdk or our own slack module
        if record.name.startswith("slack_sdk") or record.name == __name__:
            return

        log_entry = self.format(record)

        try:
            self.slack.log_message(record.levelname, log_entry)
        except Exception:
            # Catch any exceptions here to prevent infinite recursion
            # We can't log this failure since that would trigger another emit call
            pass
