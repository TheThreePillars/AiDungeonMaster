"""Main entry point for AI Dungeon Master."""

import asyncio
import sys
from pathlib import Path

from .config import get_config, load_config
from .database.session import init_db


def setup_paths() -> None:
    """Ensure required directories exist."""
    config = get_config()

    config.paths.saves.mkdir(parents=True, exist_ok=True)
    config.paths.srd_data.mkdir(parents=True, exist_ok=True)
    config.paths.prompts.mkdir(parents=True, exist_ok=True)


def main() -> int:
    """Main entry point for the application.

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Load configuration
        config = load_config()

        # Setup required directories
        setup_paths()

        # Initialize database
        init_db(config.paths.database)

        # Import and run the UI app
        from .ui.app import AIDungeonMasterApp

        app = AIDungeonMasterApp()
        app.run()

        return 0

    except KeyboardInterrupt:
        print("\nGoodbye, adventurer!")
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
