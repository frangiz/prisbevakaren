"""Cron job script to update prices for all URLs in the database."""

import os
import uuid
from datetime import datetime, timezone

from typed_json_db import IndexedJsonDB

from src.app import URL, URLS_DB_PATH
from src.config import SlackConfig
from src.price_scraper import PriceScraper
from src.slack_notifier import Slack


def update_all_prices() -> None:
    """Fetch and update prices for all URLs in the database."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting price update job...")

    # Set up Slack client if configured
    slack_client = None
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    channel_id = os.environ.get("SLACK_CHANNEL_ID")

    if bot_token and channel_id:
        slack_config = SlackConfig(bot_token=bot_token, channel_id=channel_id)
        slack_client = Slack(slack_config)
        print("Slack notifications enabled")
    else:
        print("Slack notifications not configured")

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

            print(f"Found {total} URLs to process")

            for url_obj in urls:
                print(f"\nProcessing: {url_obj.url}")

                try:
                    # Fetch the current price
                    new_price = scraper.fetch_price(url_obj.url)

                    if new_price is None:
                        print("  ❌ Failed to fetch price")
                        failed += 1
                        failed_urls.append(url_obj.url)
                        continue

                    print(f"  💰 Found price: {new_price} kr")

                    # Check if price has changed
                    price_changed = url_obj.current_price != new_price

                    if price_changed:
                        print(
                            f"  📈 Price changed: {url_obj.current_price} → {new_price}"
                        )
                        url_obj.previous_price = url_obj.current_price
                        url_obj.current_price = new_price
                        url_obj.last_price_change = datetime.now(
                            timezone.utc
                        ).isoformat()
                        urls_db.update(url_obj)
                        updated += 1
                        print("  ✅ Updated in database")
                    else:
                        print(f"  ℹ️  Price unchanged: {new_price} kr")

                except Exception as e:
                    print(f"  ❌ Error processing URL: {e}")
                    failed += 1
                    failed_urls.append(url_obj.url)
                    if slack_client:
                        error_msg = (
                            f"Failed to process URL: {url_obj.url}\nError: {str(e)}"
                        )
                        slack_client.post_warn_to_slack(error_msg)

        print(f"\n{'=' * 60}")
        print("Price update job completed!")
        print(f"  Total URLs: {total}")
        print(f"  Successfully updated: {updated}")
        print(f"  Failed: {failed}")
        print(f"{'=' * 60}\n")

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
        error_msg = f"Critical error in price update job: {e}"
        print(f"\n❌ {error_msg}\n")
        if slack_client:
            slack_client.post_message_to_slack(f":x: {error_msg}")
        raise


if __name__ == "__main__":
    update_all_prices()
