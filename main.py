"""Main entry point for the Flask Prisbevakaren application."""

import logging
import os

from src.app import create_app
from src.config import SlackConfig
from src.slack_notifier import SlackHandler


def main() -> None:
    """Run the Flask application."""
    # Set up logging
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(script_dir, "prisbevakaren.log")

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # Add Slack handler if configured
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    channel_id = os.environ.get("SLACK_CHANNEL_ID")

    if bot_token and channel_id:
        slack_config = SlackConfig(bot_token=bot_token, channel_id=channel_id)
        slack_handler = SlackHandler(slack_config)
        slack_handler.setLevel(logging.WARNING)
        logger.addHandler(slack_handler)
        logger.info("Slack notifications enabled for warnings and errors")

    app = create_app()
    print("Starting Flask prisbevakaren...")
    print("Open http://127.0.0.1:5001 in your browser")
    # Only enable debug mode in development, not in production
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    app.run(debug=debug_mode, host="0.0.0.0", port=5001)


if __name__ == "__main__":
    main()
