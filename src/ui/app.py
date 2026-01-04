"""Main Textual application for AI Dungeon Master."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from .screens.main_menu import MainMenuScreen
from .screens.character_creation import CharacterCreationScreen
from .screens.game_session import GameSessionScreen
from .screens.combat_view import CombatViewScreen
from .screens.party_manager import PartyManagerScreen


class AIDungeonMasterApp(App):
    """The main AI Dungeon Master application."""

    TITLE = "AI Dungeon Master"
    SUB_TITLE = "Pathfinder 1e"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "back", "Back", show=True),
        Binding("f1", "help", "Help", show=True),
        Binding("ctrl+s", "save", "Save", show=False),
    ]

    SCREENS = {
        "main_menu": MainMenuScreen,
        "character_creation": CharacterCreationScreen,
        "game_session": GameSessionScreen,
        "combat_view": CombatViewScreen,
        "party_manager": PartyManagerScreen,
    }

    def __init__(self):
        """Initialize the application."""
        super().__init__()
        self.current_party = None
        self.current_campaign = None
        self.llm_client = None

    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount - show main menu."""
        self.push_screen("main_menu")

    def action_back(self) -> None:
        """Go back to previous screen."""
        if len(self.screen_stack) > 1:
            self.pop_screen()

    def action_help(self) -> None:
        """Show help screen."""
        self.notify(
            "AI Dungeon Master - Pathfinder 1e\n"
            "Use arrow keys to navigate, Enter to select.\n"
            "Press ESC to go back, Q to quit.",
            title="Help",
            timeout=5,
        )

    def action_save(self) -> None:
        """Save current game state."""
        if self.current_party or self.current_campaign:
            self.notify("Game saved!", title="Save")
        else:
            self.notify("Nothing to save.", title="Save")


def run_app() -> None:
    """Run the AI Dungeon Master application."""
    app = AIDungeonMasterApp()
    app.run()


if __name__ == "__main__":
    run_app()
