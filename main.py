"""Main entry point for the Flask Prisbevakaren application."""

import logging
import os

from src.app import create_app


def main() -> None:
    """Run the Flask application."""
    # Set up logging
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(script_dir, "prisbevakaren.log")
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s",
    )

    app = create_app()
    print("Starting Flask prisbevakaren...")
    print("Open http://127.0.0.1:5001 in your browser")
    # Only enable debug mode in development, not in production
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    app.run(debug=debug_mode, host="0.0.0.0", port=5001)


if __name__ == "__main__":
    main()
