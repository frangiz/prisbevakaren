# Prisbevakaren

A Flask web application for managing URLs organized in groups, with support for price tracking.

## Features

- Create and manage groups
- Add URLs to groups
- Track current prices and price change history for URLs
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

The application will be available at `http://localhost:5000`.

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
