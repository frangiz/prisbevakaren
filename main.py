"""Main entry point for the Flask Prisbevakaren application."""

import os

from src.app import create_app


def main() -> None:
    """Run the Flask application."""
    app = create_app()
    print("Starting Flask prisbevakaren...")
    print("Open http://127.0.0.1:5000 in your browser")
    # Only enable debug mode in development, not in production
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    app.run(debug=debug_mode, host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()
