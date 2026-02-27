# Prisbevakaren

A Flask web application for managing URLs organized in groups, with support for price tracking.

## Features

- Create and manage groups
- Add URLs to groups
- Track current prices and price change history for URLs
- **Duplicate URL prevention** — the same URL cannot be added to the same group twice
- Simple web interface for all operations

## Development Setup

### Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Install dependencies
uv sync

# Run tests
make test

# Run the application
uv run python main.py
```

The application will be available at `http://localhost:5001`.

## Price Tracking

### Slack Notifications (Optional)

To receive Slack notifications when errors occur during price updates, set up a Slack webhook:

1. Create a Slack Incoming Webhook:
   - Go to https://api.slack.com/messaging/webhooks
   - Create a new webhook for your workspace
   - Copy the webhook URL

2. Set the environment variable:
   ```bash
   export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
   ```

3. Run the price update script — errors will now be reported to Slack automatically.

**Note:** If the `SLACK_WEBHOOK_URL` is not set, the script will run normally without sending notifications.

### Manual Price Update

Update prices for all URLs in the database:

```bash
uv run python update_prices.py
```

### Automated Price Updates (Cron Job)

Set up a cron job to automatically update prices. Edit your crontab:

```bash
crontab -e
```

Add one of the following lines:

```bash
# Update prices every hour
# Note: Source webhook URL from a secure file to avoid exposing it in crontab
0 * * * * cd /path/to/prisbevakaren && . /path/to/.env && /path/to/uv run python update_prices.py >> /tmp/prisbevakaren-cron.log 2>&1

# Update prices every 6 hours
0 */6 * * * cd /path/to/prisbevakaren && /path/to/uv run python update_prices.py >> /tmp/prisbevakaren-cron.log 2>&1

# Update prices once daily at 8 AM
0 8 * * * cd /path/to/prisbevakaren && /path/to/uv run python update_prices.py >> /tmp/prisbevakaren-cron.log 2>&1
```

**Secure configuration for Slack notifications:**

Instead of exposing the webhook URL directly in crontab, create a `.env` file:

```bash
# /path/to/.env
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

Make sure to restrict permissions on the `.env` file:
```bash
chmod 600 /path/to/.env
```

### Supported Websites

The price scraper currently supports:
- Jula.se
- Willys.se
- Generic e-commerce sites (best effort)

To add support for more sites, edit [src/price_scraper.py](src/price_scraper.py) and add site-specific scraping logic.

## Production Deployment

For small-scale production use (1-2 concurrent users) on a local network.

### Setup

1. **Set the SECRET_KEY environment variable**:
   ```bash
   export SECRET_KEY="your-random-secret-key-here"
   ```
   
   Generate a secure secret key:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Install Gunicorn**:
   ```bash
   uv add gunicorn
   ```

3. **Run with Gunicorn**:
   ```bash
   SECRET_KEY="your-secret-key" uv run gunicorn -w 2 -b 0.0.0.0:8000 "src.app:create_app()"
   ```

   Options:
   - `-w 2`: Run with 2 worker processes (suitable for 1-2 concurrent users)
   - `-b 0.0.0.0:8000`: Bind to all interfaces on port 8000 (accessible on local network)
   - Adjust the port as needed for your environment

### Using systemd (Linux)

Create a systemd service file at `/etc/systemd/system/prisbevakaren.service`:

```ini
[Unit]
Description=Prisbevakaren Flask App
After=network.target

[Service]
Type=notify
User=your-username
WorkingDirectory=/path/to/prisbevakaren
Environment="SECRET_KEY=your-secret-key-here"
ExecStart=/path/to/uv run gunicorn -w 2 -b 0.0.0.0:8000 "src.app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl enable prisbevakaren
sudo systemctl start prisbevakaren
```

### Data Persistence

The application stores data in JSON files:
- `groups.json` - Group definitions
- `urls.json` - URL entries with prices

Make sure these files are writable by the application user and backed up regularly.

## License

See [LICENSE](LICENSE) file for details.
