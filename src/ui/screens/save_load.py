"""Save/Load game screens for AI Dungeon Master."""

from datetime import datetime
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Static

from ...database.session import session_scope
from ...database.models import Campaign, Session, Party


class SaveGameScreen(ModalScreen):
    """Modal screen for saving the game."""

    CSS = """
    SaveGameScreen {
        align: center middle;
    }

    #save-dialog {
        width: 60;
        height: 25;
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

    #save-table {
        height: 1fr;
        margin-bottom: 1;
    }

    #save-name-area {
        margin-bottom: 1;
    }

    .label {
        margin-bottom: 0;
    }

    Input {
        width: 100%;
    }

    #button-row {
        height: 3;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self):
        super().__init__()
        self._saves: dict[str, dict] = {}

    def compose(self) -> ComposeResult:
        with Container(id="save-dialog"):
            yield Label("Save Game", classes="header")
            yield DataTable(id="save-table")

            with Vertical(id="save-name-area"):
                yield Label("Save Name:", classes="label")
                yield Input(
                    placeholder="Enter save name...",
                    id="input-save-name",
                    value=f"Save {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )

            with Horizontal(id="button-row"):
                yield Button("Save", id="btn-save", variant="success")
                yield Button("Overwrite", id="btn-overwrite", variant="warning")
                yield Button("Cancel", id="btn-cancel")

    def on_mount(self) -> None:
        """Set up the save table."""
        table = self.query_one("#save-table", DataTable)
        table.add_columns("Name", "Date", "Party")
        table.cursor_type = "row"

        self._load_existing_saves()

    def _load_existing_saves(self) -> None:
        """Load existing save games from database."""
        table = self.query_one("#save-table", DataTable)
        table.clear()
        self._saves.clear()

        try:
            with session_scope() as session:
                campaigns = session.query(Campaign).all()
                for campaign in campaigns:
                    # Get latest session for this campaign
                    latest_session = (
                        session.query(Session)
                        .filter_by(campaign_id=campaign.id)
                        .order_by(Session.started_at.desc())
                        .first()
                    )

                    # Get party info
                    parties = session.query(Party).filter_by(campaign_id=campaign.id).all()
                    party_names = ", ".join(p.name for p in parties) if parties else "No party"

                    date_str = (
                        latest_session.started_at.strftime("%Y-%m-%d %H:%M")
                        if latest_session
                        else campaign.created_at.strftime("%Y-%m-%d %H:%M")
                    )

                    row_key = table.add_row(campaign.name, date_str, party_names)
                    self._saves[str(row_key)] = {
                        "id": campaign.id,
                        "name": campaign.name,
                    }

        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - populate save name."""
        row_key = event.row_key
        if row_key is not None:
            save_data = self._saves.get(str(row_key))
            if save_data:
                input_field = self.query_one("#input-save-name", Input)
                input_field.value = save_data["name"]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-save":
            self._save_game(overwrite=False)
        elif button_id == "btn-overwrite":
            self._save_game(overwrite=True)
        elif button_id == "btn-cancel":
            self.dismiss(False)

    def _save_game(self, overwrite: bool = False) -> None:
        """Save the current game state."""
        save_name = self.query_one("#input-save-name", Input).value.strip()
        if not save_name:
            self.app.notify("Please enter a save name.", title="Save", severity="error")
            return

        try:
            with session_scope() as session:
                # Check if save exists
                existing = session.query(Campaign).filter_by(name=save_name).first()

                if existing and not overwrite:
                    self.app.notify(
                        "Save already exists. Use Overwrite to replace.",
                        title="Save",
                        severity="warning"
                    )
                    return

                if existing:
                    campaign = existing
                else:
                    campaign = Campaign(name=save_name)
                    session.add(campaign)
                    session.flush()

                # Update campaign with current state
                game_state = self.app.game_state
                campaign.current_location = game_state.current_location
                campaign.world_state = {
                    "location_description": game_state.location_description,
                    "time_of_day": game_state.time_of_day,
                    "in_combat": game_state.in_combat,
                }

                # Link party to campaign
                if game_state.party_id:
                    party = session.query(Party).filter_by(id=game_state.party_id).first()
                    if party:
                        party.campaign_id = campaign.id

                # Create a session record for this save
                session_num = (
                    session.query(Session)
                    .filter_by(campaign_id=campaign.id)
                    .count() + 1
                )

                game_session = Session(
                    campaign_id=campaign.id,
                    session_number=session_num,
                    title=f"Session {session_num}",
                    conversation_log=self.app.memory.messages if hasattr(self.app, 'memory') else [],
                )
                session.add(game_session)

                self.app.game_state.campaign_id = campaign.id

            self.app.notify(f"Game saved: {save_name}", title="Save")
            self.dismiss(True)

        except Exception as e:
            self.app.notify(f"Error saving: {e}", title="Error", severity="error")


class LoadGameScreen(ModalScreen):
    """Modal screen for loading a saved game."""

    CSS = """
    LoadGameScreen {
        align: center middle;
    }

    #load-dialog {
        width: 60;
        height: 25;
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

    #load-table {
        height: 1fr;
        margin-bottom: 1;
    }

    #save-info {
        height: 5;
        border: solid $secondary;
        padding: 1;
        margin-bottom: 1;
    }

    #button-row {
        height: 3;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self):
        super().__init__()
        self._saves: dict[str, dict] = {}
        self.selected_campaign_id = None

    def compose(self) -> ComposeResult:
        with Container(id="load-dialog"):
            yield Label("Load Game", classes="header")
            yield DataTable(id="load-table")
            yield Static("Select a save to view details.", id="save-info")

            with Horizontal(id="button-row"):
                yield Button("Load", id="btn-load", variant="success")
                yield Button("Delete", id="btn-delete", variant="error")
                yield Button("Cancel", id="btn-cancel")

    def on_mount(self) -> None:
        """Set up the load table."""
        table = self.query_one("#load-table", DataTable)
        table.add_columns("Name", "Date", "Location")
        table.cursor_type = "row"

        self._load_saves()

    def _load_saves(self) -> None:
        """Load save games from database."""
        table = self.query_one("#load-table", DataTable)
        table.clear()
        self._saves.clear()

        try:
            with session_scope() as session:
                campaigns = session.query(Campaign).order_by(Campaign.updated_at.desc()).all()

                for campaign in campaigns:
                    date_str = campaign.updated_at.strftime("%Y-%m-%d %H:%M")
                    location = campaign.current_location or "Unknown"

                    row_key = table.add_row(campaign.name, date_str, location)
                    self._saves[str(row_key)] = {
                        "id": campaign.id,
                        "name": campaign.name,
                        "location": location,
                        "world_state": campaign.world_state or {},
                    }

        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        row_key = event.row_key
        if row_key is not None:
            save_data = self._saves.get(str(row_key))
            if save_data:
                self.selected_campaign_id = save_data["id"]
                info = self.query_one("#save-info", Static)

                world = save_data.get("world_state", {})
                info.update(
                    f"[bold]{save_data['name']}[/bold]\n"
                    f"Location: {save_data['location']}\n"
                    f"Time: {world.get('time_of_day', 'Unknown')}"
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-load":
            self._load_game()
        elif button_id == "btn-delete":
            self._delete_save()
        elif button_id == "btn-cancel":
            self.dismiss(None)

    def _load_game(self) -> None:
        """Load the selected game."""
        if not self.selected_campaign_id:
            self.app.notify("Select a save first.", title="Load")
            return

        try:
            with session_scope() as session:
                campaign = session.query(Campaign).filter_by(
                    id=self.selected_campaign_id
                ).first()

                if not campaign:
                    self.app.notify("Save not found.", title="Error", severity="error")
                    return

                # Load game state
                game_state = self.app.game_state
                game_state.campaign_id = campaign.id
                game_state.current_location = campaign.current_location or "The Rusty Dragon Inn"

                world = campaign.world_state or {}
                game_state.location_description = world.get(
                    "location_description",
                    "A warm and inviting tavern."
                )
                game_state.time_of_day = world.get("time_of_day", "morning")
                game_state.in_combat = world.get("in_combat", False)

                # Load party
                party = session.query(Party).filter_by(campaign_id=campaign.id).first()
                if party:
                    game_state.load_party(party.id)

                # Load conversation history from latest session
                latest_session = (
                    session.query(Session)
                    .filter_by(campaign_id=campaign.id)
                    .order_by(Session.started_at.desc())
                    .first()
                )

                if latest_session and latest_session.conversation_log:
                    self.app.memory.messages = latest_session.conversation_log

                self.app.notify(f"Loaded: {campaign.name}", title="Load")

            self.dismiss(campaign.id)

        except Exception as e:
            self.app.notify(f"Error loading: {e}", title="Error", severity="error")

    def _delete_save(self) -> None:
        """Delete the selected save."""
        if not self.selected_campaign_id:
            self.app.notify("Select a save first.", title="Delete")
            return

        try:
            with session_scope() as session:
                campaign = session.query(Campaign).filter_by(
                    id=self.selected_campaign_id
                ).first()

                if campaign:
                    name = campaign.name
                    session.delete(campaign)
                    self.app.notify(f"Deleted: {name}", title="Delete")

            self.selected_campaign_id = None
            self._load_saves()

            info = self.query_one("#save-info", Static)
            info.update("Select a save to view details.")

        except Exception as e:
            self.app.notify(f"Error deleting: {e}", title="Error", severity="error")
