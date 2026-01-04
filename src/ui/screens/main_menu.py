"""Main menu screen for AI Dungeon Master."""

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static


class TitleArt(Static):
    """ASCII art title display."""

    TITLE_ART = """
╔═══════════════════════════════════════════════════════════════╗
║     _    ___   ____                                           ║
║    / \\  |_ _| |  _ \\ _   _ _ __   __ _  ___  ___  _ __        ║
║   / _ \\  | |  | | | | | | | '_ \\ / _` |/ _ \\/ _ \\| '_ \\       ║
║  / ___ \\ | |  | |_| | |_| | | | | (_| |  __/ (_) | | | |      ║
║ /_/   \\_\\___| |____/ \\__,_|_| |_|\\__, |\\___|\\___/|_| |_|      ║
║                                   |___/                        ║
║               __  __           _                               ║
║              |  \\/  | __ _ ___| |_ ___ _ __                    ║
║              | |\\/| |/ _` / __| __/ _ \\ '__|                   ║
║              | |  | | (_| \\__ \\ ||  __/ |                      ║
║              |_|  |_|\\__,_|___/\\__\\___|_|                      ║
║                                                                ║
║                    Pathfinder 1st Edition                      ║
╚═══════════════════════════════════════════════════════════════╝
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
                yield Button("Settings", id="btn-settings")
                yield Button("Quit", id="btn-quit", variant="error")
                yield Label("v0.1.0 - Powered by Ollama", id="version-label")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-new-game":
            self.app.push_screen("game_session")
        elif button_id == "btn-continue":
            self.app.notify("No saved games found.", title="Continue")
        elif button_id == "btn-create-char":
            self.app.push_screen("character_creation")
        elif button_id == "btn-party":
            self.app.push_screen("party_manager")
        elif button_id == "btn-settings":
            self.app.notify("Settings coming soon!", title="Settings")
        elif button_id == "btn-quit":
            self.app.exit()
