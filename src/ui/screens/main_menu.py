"""Main menu screen for AI Dungeon Master."""

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from .save_load import LoadGameScreen


class TitleArt(Static):
    """ASCII art title display."""

    TITLE_ART = """
┌─────────────────────────────┐
│      AI Dungeon Master      │
│                             │
│    Pathfinder 1st Edition   │
└─────────────────────────────┘
    """

    def compose(self) -> ComposeResult:
        """Render the title art."""
        yield Label(self.TITLE_ART, id="title-art")


class MainMenuScreen(Screen):
    """The main menu screen."""

    CSS = """
    MainMenuScreen {
        align: center middle;
    }

    #title-art {
        text-align: center;
        color: $primary;
        margin-bottom: 2;
    }

    #menu-container {
        width: 40;
        height: auto;
        align: center middle;
    }

    Button {
        width: 100%;
        margin: 1 0;
    }

    #version-label {
        text-align: center;
        color: $text-muted;
        margin-top: 2;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the main menu."""
        with Center():
            with Vertical(id="menu-container"):
                yield TitleArt()
                yield Button("New Game", id="btn-new-game", variant="primary")
                yield Button("Continue Game", id="btn-continue")
                yield Button("Create Character", id="btn-create-char")
                yield Button("Manage Party", id="btn-party")
                yield Button("Bestiary", id="btn-bestiary")
                yield Button("Settings", id="btn-settings")
                yield Button("Quit", id="btn-quit", variant="error")
                yield Label("v0.1.0 - Powered by Ollama", id="version-label")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-new-game":
            self.app.push_screen("game_session")
        elif button_id == "btn-continue":
            self._open_load_game()
        elif button_id == "btn-create-char":
            self.app.push_screen("character_creation")
        elif button_id == "btn-party":
            self.app.push_screen("party_manager")
        elif button_id == "btn-bestiary":
            self.app.push_screen("bestiary")
        elif button_id == "btn-settings":
            self.app.push_screen("settings")
        elif button_id == "btn-quit":
            self.app.exit()

    def _open_load_game(self) -> None:
        """Open the load game screen."""
        self.app.push_screen(LoadGameScreen(), self._handle_load_result)

    def _handle_load_result(self, campaign_id: int | None) -> None:
        """Handle the result from the load game screen."""
        if campaign_id is not None:
            # Game was loaded, go to game session
            self.app.push_screen("game_session")
