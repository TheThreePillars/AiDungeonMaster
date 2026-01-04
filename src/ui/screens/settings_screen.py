"""Settings screen for configuring the application."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Input, Label, Select, Static

from ...config import get_config


class SettingsScreen(Screen):
    """Screen for application settings."""

    CSS = """
    SettingsScreen {
        align: center middle;
    }

    #settings-container {
        width: 70;
        height: 90%;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    .header {
        text-style: bold;
        color: $primary;
        text-align: center;
        margin-bottom: 1;
    }

    .section {
        margin-bottom: 1;
        border: solid $secondary;
        padding: 1;
    }

    .section-title {
        text-style: bold;
        color: $secondary;
        margin-bottom: 1;
    }

    .setting-row {
        height: 3;
        margin-bottom: 1;
    }

    .setting-label {
        width: 20;
    }

    Input {
        width: 1fr;
    }

    Select {
        width: 1fr;
    }

    #scroll-area {
        height: 1fr;
    }

    #button-row {
        dock: bottom;
        height: 3;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    .hint {
        color: $text-muted;
        text-style: italic;
    }
    """

    def __init__(self):
        super().__init__()
        self._load_current_settings()

    def _load_current_settings(self) -> None:
        """Load current settings from config."""
        try:
            config = get_config()
            self.llm_model = config.llm.model
            self.llm_base_url = config.llm.base_url
        except Exception:
            self.llm_model = "mistral:latest"
            self.llm_base_url = "http://localhost:11434"

    def compose(self) -> ComposeResult:
        with Container(id="settings-container"):
            yield Label("Settings", classes="header")

            with VerticalScroll(id="scroll-area"):
                # LLM Settings
                with Container(classes="section"):
                    yield Label("AI / LLM Settings", classes="section-title")

                    with Horizontal(classes="setting-row"):
                        yield Label("Model:", classes="setting-label")
                        yield Input(
                            value=self.llm_model,
                            id="input-model",
                            placeholder="mistral:latest"
                        )

                    with Horizontal(classes="setting-row"):
                        yield Label("Ollama URL:", classes="setting-label")
                        yield Input(
                            value=self.llm_base_url,
                            id="input-url",
                            placeholder="http://localhost:11434"
                        )

                    yield Button("Test Connection", id="btn-test")
                    yield Static("", id="connection-status")

                # Game Settings
                with Container(classes="section"):
                    yield Label("Game Settings", classes="section-title")

                    with Horizontal(classes="setting-row"):
                        yield Label("XP Track:", classes="setting-label")
                        yield Select(
                            [
                                ("Slow", "slow"),
                                ("Medium (Default)", "medium"),
                                ("Fast", "fast"),
                            ],
                            id="select-xp-track",
                            value="medium",
                        )

                    with Horizontal(classes="setting-row"):
                        yield Label("Point Buy:", classes="setting-label")
                        yield Select(
                            [
                                ("Low Fantasy (10)", "10"),
                                ("Standard (15)", "15"),
                                ("High Fantasy (20)", "20"),
                                ("Epic (25)", "25"),
                            ],
                            id="select-point-buy",
                            value="20",
                        )

                    yield Checkbox("Allow multiclassing", id="chk-multiclass", value=True)
                    yield Checkbox("Use flanking rules", id="chk-flanking", value=True)
                    yield Checkbox("Critical hit confirmation", id="chk-crit-confirm", value=True)

                # UI Settings
                with Container(classes="section"):
                    yield Label("UI Settings", classes="section-title")

                    yield Checkbox("Show dice roll details", id="chk-dice-details", value=True)
                    yield Checkbox("Auto-scroll narrative", id="chk-auto-scroll", value=True)
                    yield Checkbox("Combat animations", id="chk-animations", value=False)

                # Danger Zone
                with Container(classes="section"):
                    yield Label("Danger Zone", classes="section-title")
                    yield Static(
                        "[red]These actions cannot be undone![/red]",
                        classes="hint"
                    )
                    yield Button(
                        "Reset All Settings",
                        id="btn-reset",
                        variant="warning"
                    )
                    yield Button(
                        "Clear All Data",
                        id="btn-clear-data",
                        variant="error"
                    )

            with Horizontal(id="button-row"):
                yield Button("Save", id="btn-save", variant="success")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-save":
            self._save_settings()
        elif button_id == "btn-cancel":
            self.app.pop_screen()
        elif button_id == "btn-test":
            self._test_connection()
        elif button_id == "btn-reset":
            self._reset_settings()
        elif button_id == "btn-clear-data":
            self._clear_data()

    def _save_settings(self) -> None:
        """Save settings to config."""
        try:
            model = self.query_one("#input-model", Input).value.strip()
            url = self.query_one("#input-url", Input).value.strip()

            if not model:
                self.app.notify("Model name is required.", title="Error", severity="error")
                return

            # Update app's LLM client
            if hasattr(self.app, 'llm_client') and self.app.llm_client:
                self.app.llm_client.model = model
                self.app.llm_client.base_url = url

            # Note: In a real app, we'd persist these to a config file
            self.app.notify("Settings saved!", title="Settings")
            self.app.pop_screen()

        except Exception as e:
            self.app.notify(f"Error saving: {e}", title="Error", severity="error")

    def _test_connection(self) -> None:
        """Test connection to Ollama."""
        status = self.query_one("#connection-status", Static)
        status.update("[yellow]Testing connection...[/yellow]")

        try:
            url = self.query_one("#input-url", Input).value.strip()
            model = self.query_one("#input-model", Input).value.strip()

            from ...llm.client import OllamaClient
            client = OllamaClient(model=model, base_url=url)

            if client.is_available():
                status.update("[green]Connection successful! Model is available.[/green]")
            else:
                status.update("[yellow]Connected but model not found.[/yellow]")

        except Exception as e:
            status.update(f"[red]Connection failed: {e}[/red]")

    def _reset_settings(self) -> None:
        """Reset all settings to defaults."""
        self.query_one("#input-model", Input).value = "mistral:latest"
        self.query_one("#input-url", Input).value = "http://localhost:11434"
        self.query_one("#select-xp-track", Select).value = "medium"
        self.query_one("#select-point-buy", Select).value = "20"

        self.app.notify("Settings reset to defaults.", title="Settings")

    def _clear_data(self) -> None:
        """Clear all game data."""
        try:
            from ...database.session import session_scope
            from ...database.models import (
                Character, Party, Campaign, Session, NPC, Quest, InventoryItem
            )

            with session_scope() as session:
                # Clear all data
                session.query(InventoryItem).delete()
                session.query(Character).delete()
                session.query(NPC).delete()
                session.query(Quest).delete()
                session.query(Session).delete()
                session.query(Party).delete()
                session.query(Campaign).delete()

            # Reset game state
            self.app.game_state.party_id = None
            self.app.game_state.campaign_id = None
            self.app.game_state.characters = []

            self.app.notify("All data cleared!", title="Data Cleared")

        except Exception as e:
            self.app.notify(f"Error clearing data: {e}", title="Error", severity="error")
