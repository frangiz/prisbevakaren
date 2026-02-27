"""Tests for slack_notifier module."""

from unittest.mock import MagicMock, patch

import pytest

from src.slack_notifier import send_error_notification, send_summary_notification


@pytest.fixture
def mock_env_with_webhook(monkeypatch: pytest.MonkeyPatch) -> str:
    """Set up environment with Slack webhook URL."""
    webhook_url = "https://hooks.slack.com/services/TEST/WEBHOOK/URL"
    monkeypatch.setenv("SLACK_WEBHOOK_URL", webhook_url)
    return webhook_url


@pytest.fixture
def mock_env_without_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up environment without Slack webhook URL."""
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)


class TestSendErrorNotification:
    """Tests for send_error_notification function."""

    def test_sends_notification_when_webhook_configured(
        self, mock_env_with_webhook: str
    ) -> None:
        """Test that notification is sent when webhook URL is configured."""
        with patch("src.slack_notifier.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = send_error_notification("Test error message")

            assert result is True
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == mock_env_with_webhook
            assert "Test error message" in call_args[1]["json"]["text"]

    def test_sends_notification_with_details(self, mock_env_with_webhook: str) -> None:
        """Test that notification includes details when provided."""
        with patch("src.slack_notifier.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = send_error_notification(
                "Test error message", details="Additional context"
            )

            assert result is True
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert "Test error message" in payload["text"]
            assert "Additional context" in payload["text"]

    def test_returns_false_when_no_webhook(
        self, mock_env_without_webhook: None
    ) -> None:
        """Test that function returns False when webhook is not configured."""
        with patch("src.slack_notifier.requests.post") as mock_post:
            result = send_error_notification("Test error")

            assert result is False
            mock_post.assert_not_called()

    def test_handles_request_failure_gracefully(
        self, mock_env_with_webhook: str
    ) -> None:
        """Test that function handles request failures gracefully."""
        with patch("src.slack_notifier.requests.post") as mock_post:
            mock_post.side_effect = Exception("Network error")

            result = send_error_notification("Test error")

            assert result is False


class TestSendSummaryNotification:
    """Tests for send_summary_notification function."""

    def test_sends_summary_notification(self, mock_env_with_webhook: str) -> None:
        """Test that summary notification is sent correctly."""
        with patch("src.slack_notifier.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = send_summary_notification(
                title="Test Summary", total=10, succeeded=8, failed=2
            )

            assert result is True
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert "Test Summary" in payload["text"]
            assert "Total: 10" in payload["text"]
            assert "Succeeded: 8" in payload["text"]
            assert "Failed: 2" in payload["text"]

    def test_uses_correct_emoji_for_success(self, mock_env_with_webhook: str) -> None:
        """Test that success emoji is used when no failures."""
        with patch("src.slack_notifier.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            send_summary_notification(
                title="All Good", total=10, succeeded=10, failed=0
            )

            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert "✅" in payload["text"]

    def test_uses_correct_emoji_for_partial_failure(
        self, mock_env_with_webhook: str
    ) -> None:
        """Test that warning emoji is used when some failures."""
        with patch("src.slack_notifier.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            send_summary_notification(
                title="Some Issues", total=10, succeeded=8, failed=2
            )

            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert "⚠️" in payload["text"]

    def test_uses_correct_emoji_for_total_failure(
        self, mock_env_with_webhook: str
    ) -> None:
        """Test that error emoji is used when all failures."""
        with patch("src.slack_notifier.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            send_summary_notification(
                title="Complete Failure", total=10, succeeded=0, failed=10
            )

            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert "❌" in payload["text"]

    def test_includes_details_when_provided(self, mock_env_with_webhook: str) -> None:
        """Test that details are included in summary notification."""
        with patch("src.slack_notifier.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            send_summary_notification(
                title="Test",
                total=5,
                succeeded=3,
                failed=2,
                details="URL1 failed\nURL2 failed",
            )

            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert "URL1 failed" in payload["text"]
            assert "URL2 failed" in payload["text"]

    def test_returns_false_when_no_webhook(
        self, mock_env_without_webhook: None
    ) -> None:
        """Test that function returns False when webhook is not configured."""
        with patch("src.slack_notifier.requests.post") as mock_post:
            result = send_summary_notification(
                title="Test", total=5, succeeded=5, failed=0
            )

            assert result is False
            mock_post.assert_not_called()

    def test_handles_request_failure_gracefully(
        self, mock_env_with_webhook: str
    ) -> None:
        """Test that function handles request failures gracefully."""
        with patch("src.slack_notifier.requests.post") as mock_post:
            mock_post.side_effect = Exception("Network error")

            result = send_summary_notification(
                title="Test", total=5, succeeded=5, failed=0
            )

            assert result is False
