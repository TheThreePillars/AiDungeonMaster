"""Main menu screen for AI Dungeon Master."""

from textual.app import ComposeResult
from textual.containers import Center, Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from ..icons import Icons
from .save_load import LoadGameScreen


class MainMenuScreen(Screen):
    """The main menu screen with modern dark theme."""

    CSS = """
    MainMenuScreen {
        background: $surface;
        align: center middle;
    }

    #main-title {
        text-align: center;
        color: $primary;
        text-style: bold;
        padding: 1 0;
    }

    #subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }

    #menu-container {
        width: 60;
        height: auto;
        align: center middle;
        padding: 2;
        background: $surface-darken-1;
        border: round $primary;
    }

    #button-group {
        width: 100%;
        height: auto;
        padding: 1 2;
    }

    .menu-button {
        width: 100%;
        margin: 1 0;
        min-height: 3;
        background: $surface-lighten-1;
        border: none;
    }

    .menu-button:hover {
        background: $primary;
    }

    .menu-button:focus {
        background: $primary;
        text-style: bold;
    }

    #btn-new-game {
        background: $success-darken-1;
    }

    #btn-new-game:hover {
        background: $success;
    }

    #btn-new-game:focus {
        background: $success;
    }

    #btn-quit {
        background: $error-darken-2;
    }

    #btn-quit:hover {
        background: $error;
    }

    .divider {
        height: 1;
        margin: 1 0;
        background: $surface-lighten-2;
    }

    #footer-container {
        width: 100%;
        height: auto;
        margin-top: 2;
        padding: 1;
    }

    #status-label {
        text-align: center;
        color: $text-muted;
    }

    .status-online {
        color: $success;
    }

    .status-offline {
        color: $error;
    }

    #version-label {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the main menu."""
        with Center():
            with Vertical(id="menu-container"):
                yield Label(f"{Icons.DICE} AI Dungeon Master", id="main-title")
                yield Label("Pathfinder 1st Edition", id="subtitle")

                with Container(id="button-group"):
                    yield Button(
                        f"{Icons.PLAY}  New Game",
                        id="btn-new-game",
                        classes="menu-button",
                    )
                    yield Button(
                        f"{Icons.LOAD}  Continue Game",
                        id="btn-continue",
                        classes="menu-button",
                    )

                    yield Static("", classes="divider")

                    yield Button(
                        f"{Icons.CHARACTER}  Create Character",
                        id="btn-create-char",
                        classes="menu-button",
                    )
                    yield Button(
                        f"{Icons.PARTY}  Manage Party",
                        id="btn-party",
                        classes="menu-button",
                    )
                    yield Button(
                        f"{Icons.MONSTER}  Bestiary",
                        id="btn-bestiary",
                        classes="menu-button",
                    )

                    yield Static("", classes="divider")

                    yield Button(
                        f"{Icons.SETTINGS}  Settings",
                        id="btn-settings",
                        classes="menu-button",
                    )
                    yield Button(
                        f"{Icons.QUIT}  Quit",
                        id="btn-quit",
                        classes="menu-button",
                    )

                with Container(id="footer-container"):
                    yield Label("", id="status-label")
                    yield Label("v0.1.0", id="version-label")

    def on_mount(self) -> None:
        """Update status label based on AI availability."""
        status_label = self.query_one("#status-label", Label)
        if hasattr(self.app, '_llm_available') and self.app._llm_available:
            status_label.update("✅ AI Online")
            status_label.add_class("status-online")
        else:
            status_label.update("⚠ AI Offline - Basic Mode")
            status_label.add_class("status-offline")

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
