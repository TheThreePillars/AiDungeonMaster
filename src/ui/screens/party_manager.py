"""Party management screen for AI Dungeon Master."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Label,
    Static,
)


class PartyManagerScreen(Screen):
    """Screen for managing the adventuring party."""

    CSS = """
    PartyManagerScreen {
        layout: grid;
        grid-size: 2;
        grid-columns: 2fr 1fr;
    }

    #party-list-panel {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    #character-detail-panel {
        height: 100%;
        border: solid $secondary;
        padding: 1;
    }

    .section-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #party-table {
        height: 1fr;
    }

    #party-gold {
        border: solid $warning;
        padding: 1;
        margin-bottom: 1;
    }

    #button-row {
        dock: bottom;
        height: 3;
    }

    Button {
        margin-right: 1;
    }

    #character-detail {
        height: 1fr;
        border: solid $accent;
        padding: 1;
    }

    #character-stats {
        margin-top: 1;
    }
    """

    def __init__(self):
        """Initialize the party manager."""
        super().__init__()
        self.selected_character = None
        self.party_gold = 150

    def compose(self) -> ComposeResult:
        """Compose the party manager screen."""
        # Left panel - Party list
        with Container(id="party-list-panel"):
            yield Label("Party Management", classes="section-header")
            yield Static(f"Party Gold: {self.party_gold} gp", id="party-gold")
            yield DataTable(id="party-table")

            with Horizontal(id="button-row"):
                yield Button("Add Character", id="btn-add", variant="success")
                yield Button("Remove", id="btn-remove", variant="error")
                yield Button("Edit", id="btn-edit")
                yield Button("Back", id="btn-back")

        # Right panel - Character details
        with Container(id="character-detail-panel"):
            yield Label("Character Details", classes="section-header")
            yield Static("Select a character to view details.", id="character-detail")
            yield Static(id="character-stats")

    def on_mount(self) -> None:
        """Set up the party table."""
        table = self.query_one("#party-table", DataTable)
        table.add_columns("Name", "Race", "Class", "Level", "HP")
        table.cursor_type = "row"

        # Add example characters
        self._add_example_characters()

    def _add_example_characters(self) -> None:
        """Add example characters to the party."""
        table = self.query_one("#party-table", DataTable)

        examples = [
            ("Valeros", "Human", "Fighter", "5", "45/45"),
            ("Merisiel", "Elf", "Rogue", "5", "32/32"),
            ("Kyra", "Human", "Cleric", "5", "38/38"),
            ("Ezren", "Human", "Wizard", "5", "22/22"),
        ]

        for name, race, cls, level, hp in examples:
            table.add_row(name, race, cls, level, hp)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the party table."""
        table = self.query_one("#party-table", DataTable)
        row_key = event.row_key

        if row_key is not None:
            # Get row data
            row_data = table.get_row(row_key)
            self._update_character_detail(row_data)

    def _update_character_detail(self, row_data: tuple) -> None:
        """Update the character detail panel."""
        if not row_data:
            return

        name, race, cls, level, hp = row_data

        detail = self.query_one("#character-detail", Static)
        detail.update(f"""[bold]{name}[/bold]
{race} {cls} {level}
HP: {hp}
""")

        # Show more detailed stats
        stats = self.query_one("#character-stats", Static)
        stats.update(f"""[bold]Ability Scores:[/bold]
  STR: 16 (+3)  DEX: 14 (+2)  CON: 14 (+2)
  INT: 10 (+0)  WIS: 12 (+1)  CHA: 10 (+0)

[bold]Saves:[/bold]
  Fort: +6  Ref: +3  Will: +2

[bold]Combat:[/bold]
  BAB: +5  CMB: +8  CMD: 20
  AC: 18 (Touch 12, Flat 16)

[bold]Equipment:[/bold]
  Longsword +1, Full Plate, Heavy Shield
""")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-add":
            self.app.push_screen("character_creation")
        elif button_id == "btn-remove":
            self._remove_selected()
        elif button_id == "btn-edit":
            self.app.notify("Character editing coming soon!", title="Edit")
        elif button_id == "btn-back":
            self.app.pop_screen()

    def _remove_selected(self) -> None:
        """Remove the selected character."""
        table = self.query_one("#party-table", DataTable)
        if table.cursor_row is not None:
            # Get the row key at cursor position
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            table.remove_row(row_key)
            self.app.notify("Character removed from party.", title="Party")
