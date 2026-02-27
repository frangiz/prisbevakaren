"""Cron job script to update prices for all URLs in the database."""

import logging
import os
import uuid
from datetime import datetime, timezone

from typed_json_db import IndexedJsonDB

from src.app import URL, URLS_DB_PATH
from src.config import SlackConfig
from src.price_scraper import PriceScraper
from src.slack_notifier import Slack, SlackHandler


def update_all_prices() -> None:
    """Fetch and update prices for all URLs in the database."""
    # Set up logging
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(script_dir, "update_prices.log")

    # Configure logging to write to file
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Remove any existing handlers
    logger.handlers.clear()

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler (for print-like output)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Starting price update job..."
    )

    # Set up Slack handler if configured
    slack_client = None
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    channel_id = os.environ.get("SLACK_CHANNEL_ID")

    if bot_token and channel_id:
        slack_config = SlackConfig(bot_token=bot_token, channel_id=channel_id)
        slack_client = Slack(slack_config)

        # Add Slack handler for WARNING and ERROR levels
        slack_handler = SlackHandler(slack_config)
        slack_handler.setLevel(logging.WARNING)
        logger.addHandler(slack_handler)

        logger.info("Slack notifications enabled")
    else:
        logger.info("Slack notifications not configured")

    try:
        # Initialize database and scraper (using context manager for cleanup)
        urls_db: IndexedJsonDB[URL, uuid.UUID] = IndexedJsonDB(
            URL, URLS_DB_PATH, primary_key="id"
        )

        with PriceScraper() as scraper:
            urls = urls_db.all()
            total = len(urls)
            updated = 0
            failed = 0
            failed_urls = []

            logger.info(f"Found {total} URLs to process")

            for url_obj in urls:
                logger.info(f"\nProcessing: {url_obj.url}")

                try:
                    # Fetch the current price
                    new_price = scraper.fetch_price(url_obj.url)

                    if new_price is None:
                        logger.warning(f"Failed to fetch price for {url_obj.url}")
                        failed += 1
                        failed_urls.append(url_obj.url)
                        continue

                    logger.info(f"  💰 Found price: {new_price} kr")

                    # Check if price has changed
                    price_changed = url_obj.current_price != new_price

                    if price_changed:
                        logger.info(
                            f"  📈 Price changed: {url_obj.current_price} → {new_price}"
                        )
                        url_obj.previous_price = url_obj.current_price
                        url_obj.current_price = new_price
                        url_obj.last_price_change = datetime.now(
                            timezone.utc
                        ).isoformat()
                        urls_db.update(url_obj)
                        updated += 1
                        logger.info("  ✅ Updated in database")
                    else:
                        logger.info(f"  ℹ️  Price unchanged: {new_price} kr")

                except Exception as e:
                    logger.error(f"Error processing URL {url_obj.url}: {e}")
                    failed += 1
                    failed_urls.append(url_obj.url)

        logger.info(f"\n{'=' * 60}")
        logger.info("Price update job completed!")
        logger.info(f"  Total URLs: {total}")
        logger.info(f"  Successfully updated: {updated}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"{'=' * 60}\n")

        # Send summary notification if there were any failures
        if failed > 0 and slack_client:
            emoji = "⚠️" if failed < total else "❌"
            summary = f"{emoji} *Price Update Job Completed with Errors*\n\n"
            summary += f"Total: {total}\n"
            summary += f"Succeeded: {total - failed}\n"
            summary += f"Failed: {failed}"

            if failed_urls:
                details = "\nFailed URLs:\n" + "\n".join(
                    f"• {url}" for url in failed_urls[:10]
                )
                if len(failed_urls) > 10:
                    details += f"\n... and {len(failed_urls) - 10} more"
                summary += details

            slack_client.post_message_to_slack(summary)

    except Exception as e:
        logger.error(f"Critical error in price update job: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    update_all_prices()
