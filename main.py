"""Main entry point for the Flask URL Manager application."""

from src.app import create_app


def main() -> None:
    """Run the Flask application."""
    app = create_app()
    print("Starting Flask URL Manager...")
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True, host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()
