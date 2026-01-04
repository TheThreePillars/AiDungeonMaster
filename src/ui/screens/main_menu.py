"""Main menu screen for AI Dungeon Master."""

from textual.app import ComposeResult
from textual.containers import Center, Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from ..icons import Icons
from .save_load import LoadGameScreen


class TitleArt(Static):
    """ASCII art title display."""

    TITLE_ART = """
    ╔══════════════════════════════════════╗
    ║                                      ║
    ║       ⚔️  AI DUNGEON MASTER  ⚔️       ║
    ║                                      ║
    ║        Pathfinder 1st Edition        ║
    ║                                      ║
    ╚══════════════════════════════════════╝
    """

    def compose(self) -> ComposeResult:
        """Render the title art."""
        yield Label(self.TITLE_ART, id="title-art")


class MainMenuScreen(Screen):
    """The main menu screen."""

    CSS = """
    MainMenuScreen {
        background: $surface;
        align: center middle;
    }

    #title-art {
        text-align: center;
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }

    #menu-container {
        width: 50;
        height: auto;
        align: center middle;
        padding: 1 2;
    }

    #button-group {
        width: 100%;
        height: auto;
        padding: 1;
        border: round $primary;
        background: $surface-darken-1;
    }

    .menu-button {
        width: 100%;
        margin: 0 0 1 0;
        min-height: 3;
    }

    .menu-button:last-of-type {
        margin-bottom: 0;
    }

    #btn-new-game {
        background: $success;
        color: $text;
    }

    #btn-new-game:hover {
        background: $success-darken-1;
    }

    #btn-quit {
        background: $error;
        margin-top: 1;
    }

    #btn-quit:hover {
        background: $error-darken-1;
    }

    #footer-container {
        width: 100%;
        height: auto;
        margin-top: 1;
    }

    #version-label {
        text-align: center;
        color: $text-muted;
    }

    #powered-by {
        text-align: center;
        color: $text-muted;
        text-style: italic;
    }

    .separator {
        height: 1;
        margin: 1 0;
        background: $primary 30%;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the main menu."""
        i = Icons

        with Center():
            with Vertical(id="menu-container"):
                yield TitleArt()

                with Container(id="button-group"):
                    yield Button(
                        f"{i.PLAY}  New Game",
                        id="btn-new-game",
                        classes="menu-button",
                    )
                    yield Button(
                        f"{i.LOAD}  Continue Game",
                        id="btn-continue",
                        classes="menu-button",
                    )

                    yield Static("", classes="separator")

                    yield Button(
                        f"{i.CHARACTER}  Create Character",
                        id="btn-create-char",
                        classes="menu-button",
                    )
                    yield Button(
                        f"{i.PARTY}  Manage Party",
                        id="btn-party",
                        classes="menu-button",
                    )
                    yield Button(
                        f"{i.MONSTER}  Bestiary",
                        id="btn-bestiary",
                        classes="menu-button",
                    )

                    yield Static("", classes="separator")

                    yield Button(
                        f"{i.SETTINGS}  Settings",
                        id="btn-settings",
                        classes="menu-button",
                    )
                    yield Button(
                        f"{i.QUIT}  Quit",
                        id="btn-quit",
                        classes="menu-button",
                    )

                with Container(id="footer-container"):
                    yield Label("v0.1.0", id="version-label")
                    yield Label("Powered by Ollama", id="powered-by")

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
            self.app.push_screen("game_session")
