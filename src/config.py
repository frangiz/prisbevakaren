"""Configuration module for Slack integration."""

from dataclasses import dataclass


@dataclass
class SlackConfig:
    """Configuration for Slack integration.

    Attributes:
        bot_token: Slack bot token for authentication
        channel_id: Slack channel ID where messages will be posted
    """

    bot_token: str
    channel_id: str
