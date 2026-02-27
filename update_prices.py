"""Cron job script to update prices for all URLs in the database."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from typed_json_db import IndexedJsonDB

from src.app import URL, URLS_DB_PATH
from src.price_scraper import PriceScraper
from src.slack_notifier import send_error_notification, send_summary_notification


def update_all_prices() -> None:
    """Fetch and update prices for all URLs in the database."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting price update job...")

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
                        print(f"  ❌ Failed to fetch price")
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
                        print(f"  ✅ Updated in database")
                    else:
                        print(f"  ℹ️  Price unchanged: {new_price} kr")

                except Exception as e:
                    print(f"  ❌ Error processing URL: {e}")
                    failed += 1
                    failed_urls.append(url_obj.url)
                    # Note: Individual error notifications are sent for immediate alerting
                    # If this causes performance issues with many failures, consider
                    # disabling individual notifications and relying on the summary only
                    send_error_notification(
                        f"Failed to process URL: {url_obj.url}", details=str(e)
                    )

        print(f"\n{'=' * 60}")
        print(f"Price update job completed!")
        print(f"  Total URLs: {total}")
        print(f"  Successfully updated: {updated}")
        print(f"  Failed: {failed}")
        print(f"{'=' * 60}\n")

        # Send summary notification if there were any failures
        if failed > 0:
            details = None
            if failed_urls:
                details = "Failed URLs:\n" + "\n".join(
                    f"• {url}" for url in failed_urls[:10]
                )
                if len(failed_urls) > 10:
                    details += f"\n... and {len(failed_urls) - 10} more"

            send_summary_notification(
                title="Price Update Job Completed with Errors",
                total=total,
                succeeded=total - failed,
                failed=failed,
                details=details,
            )

    except Exception as e:
        error_msg = f"Critical error in price update job: {e}"
        print(f"\n❌ {error_msg}\n")
        send_error_notification("Price update job failed completely", details=str(e))
        raise


if __name__ == "__main__":
    update_all_prices()
