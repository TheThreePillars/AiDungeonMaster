"""Quest log screen for tracking adventures and objectives."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Label,
    Select,
    Static,
    TextArea,
)

from ...database.session import session_scope
from ...database.models import Quest


class QuestLogScreen(Screen):
    """Screen for viewing and managing quests."""

    CSS = """
    QuestLogScreen {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 2fr;
    }

    #quest-list-panel {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    #quest-detail-panel {
        height: 100%;
        border: solid $secondary;
        padding: 1;
    }

    .section-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #quest-table {
        height: 1fr;
    }

    #quest-filter {
        margin-bottom: 1;
    }

    #button-row {
        dock: bottom;
        height: 3;
    }

    Button {
        margin-right: 1;
    }

    #quest-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #quest-description {
        height: auto;
        margin-bottom: 1;
    }

    #objectives-section {
        border: solid $accent;
        padding: 1;
        margin-bottom: 1;
        height: auto;
    }

    .objective-row {
        height: 1;
    }

    .objective-checkbox {
        width: 3;
    }

    .objective-text {
        width: 1fr;
    }

    #rewards-section {
        border: solid $success;
        padding: 1;
        margin-bottom: 1;
    }

    #notes-section {
        height: 1fr;
        border: solid $warning;
        padding: 1;
    }

    #detail-buttons {
        dock: bottom;
        height: 3;
    }
    """

    def __init__(self):
        super().__init__()
        self._quests: dict[str, dict] = {}
        self.selected_quest_id = None
        self.filter_status = "active"

    def compose(self) -> ComposeResult:
        # Left panel - Quest list
        with Container(id="quest-list-panel"):
            yield Label("Quest Log", classes="section-header")

            yield Select(
                [
                    ("Active Quests", "active"),
                    ("Completed", "completed"),
                    ("Failed", "failed"),
                    ("All Quests", "all"),
                ],
                id="quest-filter",
                value="active",
            )

            yield DataTable(id="quest-table")

            with Horizontal(id="button-row"):
                yield Button("New Quest", id="btn-new", variant="success")
                yield Button("Back", id="btn-back")

        # Right panel - Quest details
        with Container(id="quest-detail-panel"):
            yield Label("Quest Details", classes="section-header")

            with VerticalScroll():
                yield Static("Select a quest to view details.", id="quest-title")
                yield Static("", id="quest-description")

                with Container(id="objectives-section"):
                    yield Label("Objectives", classes="section-header")
                    yield Static("No objectives.", id="objectives-list")

                with Container(id="rewards-section"):
                    yield Label("Rewards", classes="section-header")
                    yield Static("No rewards listed.", id="rewards-display")

                with Container(id="notes-section"):
                    yield Label("Notes & Clues", classes="section-header")
                    yield Static("No notes.", id="notes-display")

            with Horizontal(id="detail-buttons"):
                yield Button("Complete", id="btn-complete", variant="success")
                yield Button("Fail", id="btn-fail", variant="error")
                yield Button("Add Note", id="btn-note")
                yield Button("Toggle Objective", id="btn-toggle")

    def on_mount(self) -> None:
        """Set up the quest table."""
        table = self.query_one("#quest-table", DataTable)
        table.add_columns("Quest", "Type", "Giver")
        table.cursor_type = "row"

        self._load_quests()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle filter change."""
        if event.select.id == "quest-filter":
            self.filter_status = str(event.value)
            self._load_quests()

    def _load_quests(self) -> None:
        """Load quests from database."""
        table = self.query_one("#quest-table", DataTable)
        table.clear()
        self._quests.clear()

        try:
            with session_scope() as session:
                query = session.query(Quest)

                if self.filter_status != "all":
                    query = query.filter_by(status=self.filter_status)

                # Filter by campaign if set
                game_state = self.app.game_state
                if game_state.campaign_id:
                    query = query.filter_by(campaign_id=game_state.campaign_id)

                quests = query.all()

                for quest in quests:
                    row_key = table.add_row(
                        quest.name[:20] + "..." if len(quest.name) > 20 else quest.name,
                        quest.quest_type or "main",
                        quest.quest_giver or "Unknown",
                    )

                    self._quests[str(row_key)] = {
                        "id": quest.id,
                        "name": quest.name,
                        "description": quest.description or "",
                        "quest_giver": quest.quest_giver or "Unknown",
                        "quest_type": quest.quest_type or "main",
                        "status": quest.status,
                        "objectives": quest.objectives or [],
                        "rewards": quest.rewards or {},
                        "notes": quest.notes or "",
                        "clues": quest.clues or [],
                    }

                if not quests:
                    self._clear_detail_panel()

        except Exception as e:
            self.app.notify(f"Error loading quests: {e}", title="Error", severity="error")

    def _clear_detail_panel(self) -> None:
        """Clear the detail panel."""
        self.query_one("#quest-title", Static).update("No quests found.")
        self.query_one("#quest-description", Static).update("")
        self.query_one("#objectives-list", Static).update("No objectives.")
        self.query_one("#rewards-display", Static).update("No rewards.")
        self.query_one("#notes-display", Static).update("No notes.")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle quest selection."""
        row_key = event.row_key
        if row_key is not None:
            quest_data = self._quests.get(str(row_key))
            if quest_data:
                self.selected_quest_id = quest_data["id"]
                self._update_detail_panel(quest_data)

    def _update_detail_panel(self, quest: dict) -> None:
        """Update the detail panel with quest info."""
        # Title
        status_color = {
            "active": "yellow",
            "completed": "green",
            "failed": "red",
        }.get(quest["status"], "white")

        title = self.query_one("#quest-title", Static)
        title.update(f"[bold]{quest['name']}[/bold] [{status_color}]({quest['status']})[/{status_color}]")

        # Description
        desc = self.query_one("#quest-description", Static)
        desc.update(quest["description"] or "[dim]No description.[/dim]")

        # Objectives
        obj_list = self.query_one("#objectives-list", Static)
        objectives = quest.get("objectives", [])
        if objectives:
            obj_text = ""
            for i, obj in enumerate(objectives):
                if isinstance(obj, dict):
                    completed = obj.get("completed", False)
                    text = obj.get("description", f"Objective {i + 1}")
                    marker = "[green](+)[/green]" if completed else "( )"
                else:
                    marker = "( )"
                    text = str(obj)
                obj_text += f"{marker} {text}\n"
            obj_list.update(obj_text.strip())
        else:
            obj_list.update("[dim]No specific objectives.[/dim]")

        # Rewards
        rewards_display = self.query_one("#rewards-display", Static)
        rewards = quest.get("rewards", {})
        if rewards:
            reward_text = ""
            if rewards.get("gold"):
                reward_text += f"Gold: {rewards['gold']} gp\n"
            if rewards.get("xp"):
                reward_text += f"XP: {rewards['xp']}\n"
            if rewards.get("items"):
                reward_text += f"Items: {', '.join(rewards['items'])}\n"
            rewards_display.update(reward_text.strip() if reward_text else "[dim]No rewards listed.[/dim]")
        else:
            rewards_display.update("[dim]No rewards listed.[/dim]")

        # Notes and clues
        notes_display = self.query_one("#notes-display", Static)
        notes = quest.get("notes", "")
        clues = quest.get("clues", [])
        notes_text = ""
        if notes:
            notes_text += notes + "\n\n"
        if clues:
            notes_text += "[bold]Clues:[/bold]\n"
            for clue in clues:
                notes_text += f"- {clue}\n"
        notes_display.update(notes_text.strip() if notes_text else "[dim]No notes or clues.[/dim]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-back":
            self.app.pop_screen()
        elif button_id == "btn-new":
            self._create_quest()
        elif button_id == "btn-complete":
            self._update_quest_status("completed")
        elif button_id == "btn-fail":
            self._update_quest_status("failed")
        elif button_id == "btn-note":
            self._add_note()
        elif button_id == "btn-toggle":
            self._toggle_objective()

    def _create_quest(self) -> None:
        """Create a new quest."""
        try:
            with session_scope() as session:
                quest = Quest(
                    campaign_id=self.app.game_state.campaign_id or 1,
                    name=f"New Quest {len(self._quests) + 1}",
                    description="A new adventure awaits...",
                    quest_type="main",
                    status="active",
                    objectives=[
                        {"description": "Complete the objective", "completed": False}
                    ],
                )
                session.add(quest)
                session.flush()

                self.app.notify(f"Created: {quest.name}", title="Quest")

            self._load_quests()

        except Exception as e:
            self.app.notify(f"Error creating quest: {e}", title="Error", severity="error")

    def _update_quest_status(self, new_status: str) -> None:
        """Update the selected quest's status."""
        if not self.selected_quest_id:
            self.app.notify("Select a quest first.", title="Quest")
            return

        try:
            with session_scope() as session:
                quest = session.query(Quest).filter_by(id=self.selected_quest_id).first()
                if quest:
                    quest.status = new_status
                    self.app.notify(f"Quest {new_status}!", title="Quest")

            self._load_quests()

        except Exception as e:
            self.app.notify(f"Error updating quest: {e}", title="Error", severity="error")

    def _add_note(self) -> None:
        """Add a note to the selected quest."""
        if not self.selected_quest_id:
            self.app.notify("Select a quest first.", title="Quest")
            return

        # For simplicity, add a placeholder note
        try:
            with session_scope() as session:
                quest = session.query(Quest).filter_by(id=self.selected_quest_id).first()
                if quest:
                    current_notes = quest.notes or ""
                    quest.notes = current_notes + "\n[New note added]" if current_notes else "[New note added]"
                    self.app.notify("Note added!", title="Quest")

            self._load_quests()
            # Refresh detail panel
            for data in self._quests.values():
                if data["id"] == self.selected_quest_id:
                    self._update_detail_panel(data)
                    break

        except Exception as e:
            self.app.notify(f"Error adding note: {e}", title="Error", severity="error")

    def _toggle_objective(self) -> None:
        """Toggle the first incomplete objective."""
        if not self.selected_quest_id:
            self.app.notify("Select a quest first.", title="Quest")
            return

        try:
            with session_scope() as session:
                quest = session.query(Quest).filter_by(id=self.selected_quest_id).first()
                if quest and quest.objectives:
                    objectives = quest.objectives.copy()
                    # Find first incomplete objective and toggle it
                    for obj in objectives:
                        if isinstance(obj, dict) and not obj.get("completed"):
                            obj["completed"] = True
                            break
                    quest.objectives = objectives
                    self.app.notify("Objective completed!", title="Quest")

            self._load_quests()
            # Refresh detail panel
            for data in self._quests.values():
                if data["id"] == self.selected_quest_id:
                    self._update_detail_panel(data)
                    break

        except Exception as e:
            self.app.notify(f"Error toggling objective: {e}", title="Error", severity="error")
