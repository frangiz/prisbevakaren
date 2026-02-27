"""Tests for slack_notifier module."""

import logging
from unittest.mock import patch

import pytest
from slack_sdk.errors import SlackApiError

from src.config import SlackConfig
from src.slack_notifier import Slack, SlackHandler


@pytest.fixture
def slack_config() -> SlackConfig:
    """Create a test SlackConfig."""
    return SlackConfig(bot_token="xoxb-test-token", channel_id="C123456")


@pytest.fixture
def slack_client(slack_config: SlackConfig) -> Slack:
    """Create a test Slack client."""
    return Slack(slack_config)


class TestSlack:
    """Tests for Slack class."""

    def test_initialization(self, slack_config: SlackConfig) -> None:
        """Test Slack client initialization."""
        slack = Slack(slack_config)
        assert slack.channel_id == "C123456"
        assert slack.client is not None

    def test_post_warn_to_slack_success(self, slack_client: Slack) -> None:
        """Test posting warning message successfully."""
        with patch.object(slack_client.client, "chat_postMessage") as mock_post:
            mock_post.return_value = {"ok": True}

            slack_client.post_warn_to_slack("Test warning")

            mock_post.assert_called_once_with(
                channel="C123456", text=":warning: Test warning"
            )

    def test_post_warn_to_slack_failure(self, slack_client: Slack) -> None:
        """Test posting warning message with error."""
        with patch.object(slack_client.client, "chat_postMessage") as mock_post:
            mock_post.side_effect = SlackApiError("error", response={"error": "test"})

            # Should not raise, just log error
            slack_client.post_warn_to_slack("Test warning")

            mock_post.assert_called_once()

    def test_post_message_to_slack_success(self, slack_client: Slack) -> None:
        """Test posting message successfully."""
        with patch.object(slack_client.client, "chat_postMessage") as mock_post:
            mock_post.return_value = {"ok": True}

            slack_client.post_message_to_slack("Test message")

            mock_post.assert_called_once_with(channel="C123456", text="Test message")

    def test_post_message_to_slack_failure(self, slack_client: Slack) -> None:
        """Test posting message with error."""
        with patch.object(slack_client.client, "chat_postMessage") as mock_post:
            mock_post.side_effect = SlackApiError("error", response={"error": "test"})

            # Should not raise, just log error
            slack_client.post_message_to_slack("Test message")

            mock_post.assert_called_once()

    def test_log_message_warning(self, slack_client: Slack) -> None:
        """Test posting warning log message."""
        with patch.object(slack_client.client, "chat_postMessage") as mock_post:
            mock_post.return_value = {"ok": True}

            slack_client.log_message("WARNING", "Warning log")

            mock_post.assert_called_once_with(
                channel="C123456", text=":warning: Warning log"
            )

    def test_log_message_error(self, slack_client: Slack) -> None:
        """Test posting error log message."""
        with patch.object(slack_client.client, "chat_postMessage") as mock_post:
            mock_post.return_value = {"ok": True}

            slack_client.log_message("ERROR", "Error log")

            mock_post.assert_called_once_with(channel="C123456", text=":x: Error log")

    def test_log_message_critical(self, slack_client: Slack) -> None:
        """Test posting critical log message."""
        with patch.object(slack_client.client, "chat_postMessage") as mock_post:
            mock_post.return_value = {"ok": True}

            slack_client.log_message("CRITICAL", "Critical log")

            mock_post.assert_called_once_with(
                channel="C123456", text=":exclamation: Critical log"
            )

    def test_log_message_failure(self, slack_client: Slack) -> None:
        """Test posting log message with error."""
        with patch.object(slack_client.client, "chat_postMessage") as mock_post:
            mock_post.side_effect = SlackApiError("error", response={"error": "test"})

            # Should not raise, just log error
            slack_client.log_message("ERROR", "Error log")

            mock_post.assert_called_once()


class TestSlackHandler:
    """Tests for SlackHandler class."""

    def test_initialization(self, slack_config: SlackConfig) -> None:
        """Test SlackHandler initialization."""
        handler = SlackHandler(slack_config)
        assert handler.slack is not None
        assert isinstance(handler, logging.Handler)

    def test_emit_log_record(self, slack_config: SlackConfig) -> None:
        """Test emitting log record."""
        handler = SlackHandler(slack_config)
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test error",
            args=(),
            exc_info=None,
        )

        with patch.object(handler.slack, "log_message") as mock_log:
            handler.emit(record)

            mock_log.assert_called_once_with("ERROR", "Test error")

    def test_emit_ignores_slack_sdk_logs(self, slack_config: SlackConfig) -> None:
        """Test that handler ignores slack_sdk logs to prevent recursion."""
        handler = SlackHandler(slack_config)
        record = logging.LogRecord(
            name="slack_sdk.web.client",
            level=logging.ERROR,
            pathname="client.py",
            lineno=1,
            msg="SDK error",
            args=(),
            exc_info=None,
        )

        with patch.object(handler.slack, "log_message") as mock_log:
            handler.emit(record)

            mock_log.assert_not_called()

    def test_emit_ignores_own_logs(self, slack_config: SlackConfig) -> None:
        """Test that handler ignores its own logs to prevent recursion."""
        handler = SlackHandler(slack_config)
        record = logging.LogRecord(
            name="src.slack_notifier",
            level=logging.ERROR,
            pathname="slack_notifier.py",
            lineno=1,
            msg="Handler error",
            args=(),
            exc_info=None,
        )

        with patch.object(handler.slack, "log_message") as mock_log:
            handler.emit(record)

            mock_log.assert_not_called()

    def test_emit_handles_exceptions(self, slack_config: SlackConfig) -> None:
        """Test that emit handles exceptions gracefully."""
        handler = SlackHandler(slack_config)
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test error",
            args=(),
            exc_info=None,
        )

        with patch.object(handler.slack, "log_message") as mock_log:
            mock_log.side_effect = Exception("Test exception")

            # Should not raise
            handler.emit(record)

            mock_log.assert_called_once()
