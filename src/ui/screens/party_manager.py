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

from ...database.session import session_scope
from ...database.models import Character, Party
from .level_up import LevelUpScreen
from .character_edit import CharacterEditScreen


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
        self.selected_character_id = None
        self.party_id = None
        self.party_gold = 0
        self._characters: dict[str, dict] = {}  # row_key -> character data

    def compose(self) -> ComposeResult:
        """Compose the party manager screen."""
        # Left panel - Party list
        with Container(id="party-list-panel"):
            yield Label("Party Management", classes="section-header")
            yield Static(f"Party Gold: {self.party_gold} gp", id="party-gold")
            yield DataTable(id="party-table")

            with Horizontal(id="button-row"):
                yield Button("Add Character", id="btn-add", variant="success")
                yield Button("Level Up", id="btn-levelup", variant="primary")
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

        # Load characters from database
        self._load_party_from_database()

    def _load_party_from_database(self) -> None:
        """Load party and characters from database."""
        table = self.query_one("#party-table", DataTable)
        table.clear()
        self._characters.clear()

        try:
            with session_scope() as session:
                # Get first party or create one
                party = session.query(Party).first()
                if party:
                    self.party_id = party.id
                    self.party_gold = party.shared_gold or 0

                    # Update gold display
                    gold_display = self.query_one("#party-gold", Static)
                    gold_display.update(f"Party Gold: {self.party_gold} gp")

                    # Load characters in this party
                    characters = session.query(Character).filter_by(party_id=party.id).all()
                    for char in characters:
                        hp_str = f"{char.current_hp}/{char.max_hp}"
                        row_key = table.add_row(
                            char.name,
                            char.race,
                            char.character_class,
                            str(char.level),
                            hp_str,
                        )
                        # Store character data for detail view
                        self._characters[str(row_key)] = {
                            "id": char.id,
                            "name": char.name,
                            "race": char.race,
                            "class": char.character_class,
                            "level": char.level,
                            "current_hp": char.current_hp,
                            "max_hp": char.max_hp,
                            "strength": char.strength,
                            "dexterity": char.dexterity,
                            "constitution": char.constitution,
                            "intelligence": char.intelligence,
                            "wisdom": char.wisdom,
                            "charisma": char.charisma,
                            "armor_class": char.armor_class,
                            "touch_ac": char.touch_ac,
                            "flat_footed_ac": char.flat_footed_ac,
                            "base_attack_bonus": char.base_attack_bonus,
                            "fortitude_base": char.fortitude_base,
                            "reflex_base": char.reflex_base,
                            "will_base": char.will_base,
                            "speed": char.speed,
                        }

                if not self._characters:
                    detail = self.query_one("#character-detail", Static)
                    detail.update("No characters in party.\nUse 'Add Character' to create one.")

        except Exception as e:
            self.app.notify(f"Error loading party: {e}", title="Error", severity="error")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the party table."""
        row_key = event.row_key

        if row_key is not None:
            char_data = self._characters.get(str(row_key))
            if char_data:
                self.selected_character_id = char_data["id"]
                self._update_character_detail(char_data)

    def _update_character_detail(self, char: dict) -> None:
        """Update the character detail panel."""
        if not char:
            return

        # Calculate modifiers
        def mod(score: int) -> str:
            m = (score - 10) // 2
            return f"{m:+d}"

        str_score = char["strength"]
        dex_score = char["dexterity"]
        con_score = char["constitution"]
        int_score = char["intelligence"]
        wis_score = char["wisdom"]
        cha_score = char["charisma"]

        detail = self.query_one("#character-detail", Static)
        detail.update(f"""[bold]{char['name']}[/bold]
{char['race']} {char['class']} Level {char['level']}
HP: {char['current_hp']}/{char['max_hp']}
Speed: {char['speed']} ft.
""")

        # Calculate saves with ability modifiers
        fort = char["fortitude_base"] + (con_score - 10) // 2
        ref = char["reflex_base"] + (dex_score - 10) // 2
        will = char["will_base"] + (wis_score - 10) // 2

        # Calculate CMB/CMD
        bab = char["base_attack_bonus"]
        str_mod = (str_score - 10) // 2
        dex_mod = (dex_score - 10) // 2
        cmb = bab + str_mod
        cmd = 10 + bab + str_mod + dex_mod

        stats = self.query_one("#character-stats", Static)
        stats.update(f"""[bold]Ability Scores:[/bold]
  STR: {str_score} ({mod(str_score)})  DEX: {dex_score} ({mod(dex_score)})  CON: {con_score} ({mod(con_score)})
  INT: {int_score} ({mod(int_score)})  WIS: {wis_score} ({mod(wis_score)})  CHA: {cha_score} ({mod(cha_score)})

[bold]Saves:[/bold]
  Fort: {fort:+d}  Ref: {ref:+d}  Will: {will:+d}

[bold]Combat:[/bold]
  BAB: +{bab}  CMB: {cmb:+d}  CMD: {cmd}
  AC: {char['armor_class']} (Touch {char['touch_ac']}, Flat {char['flat_footed_ac']})
""")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-add":
            self.app.push_screen("character_creation")
        elif button_id == "btn-levelup":
            self._open_level_up()
        elif button_id == "btn-remove":
            self._remove_selected()
        elif button_id == "btn-edit":
            self._open_character_edit()
        elif button_id == "btn-back":
            self.app.pop_screen()

    def _open_level_up(self) -> None:
        """Open the level up screen for the selected character."""
        if not self.selected_character_id:
            self.app.notify("Select a character first.", title="Level Up")
            return

        # Find the selected character data
        char_data = None
        for data in self._characters.values():
            if data["id"] == self.selected_character_id:
                char_data = data
                break

        if not char_data:
            self.app.notify("Character not found.", title="Error", severity="error")
            return

        # Check max level
        if char_data["level"] >= 20:
            self.app.notify("Character is already at max level!", title="Level Up")
            return

        self.app.push_screen(LevelUpScreen(char_data), self._handle_level_up_result)

    def _handle_level_up_result(self, result: dict | None) -> None:
        """Handle the result from the level up screen."""
        if result is None:
            return  # User cancelled

        try:
            with session_scope() as session:
                character = session.query(Character).filter_by(
                    id=self.selected_character_id
                ).first()

                if not character:
                    self.app.notify("Character not found.", title="Error", severity="error")
                    return

                # Apply level up
                character.level = result["new_level"]
                character.max_hp += result["hp_gain"]
                character.current_hp += result["hp_gain"]

                # Update BAB
                character.base_attack_bonus += result["bab_change"]

                # Update saves
                character.fortitude_base += result["save_changes"]["fortitude"]
                character.reflex_base += result["save_changes"]["reflex"]
                character.will_base += result["save_changes"]["will"]

                # Add skill points
                character.skill_points_remaining = (
                    (character.skill_points_remaining or 0) + result["skill_points"]
                )

                # Apply ability increase if any
                if result.get("ability_increase"):
                    ability_map = {
                        "STR": "strength",
                        "DEX": "dexterity",
                        "CON": "constitution",
                        "INT": "intelligence",
                        "WIS": "wisdom",
                        "CHA": "charisma",
                    }
                    ability_attr = ability_map.get(result["ability_increase"])
                    if ability_attr:
                        current = getattr(character, ability_attr, 10)
                        setattr(character, ability_attr, current + 1)

                        # If CON increased, add 1 HP per level
                        if ability_attr == "constitution":
                            character.max_hp += result["new_level"]
                            character.current_hp += result["new_level"]

                # Update CMB/CMD
                str_mod = (character.strength - 10) // 2
                dex_mod = (character.dexterity - 10) // 2
                character.cmb = character.base_attack_bonus + str_mod
                character.cmd = 10 + character.base_attack_bonus + str_mod + dex_mod

                # Update game state
                for char in self.app.game_state.characters:
                    if char.get("id") == self.selected_character_id:
                        char["level"] = character.level
                        char["max_hp"] = character.max_hp
                        char["current_hp"] = character.current_hp
                        break

                self.app.notify(
                    f"{character.name} is now level {character.level}!",
                    title="Level Up"
                )

            # Reload the party table
            self._load_party_from_database()

        except Exception as e:
            self.app.notify(f"Error leveling up: {e}", title="Error", severity="error")

    def _open_character_edit(self) -> None:
        """Open the character edit screen for the selected character."""
        if not self.selected_character_id:
            self.app.notify("Select a character first.", title="Edit")
            return

        self.app.push_screen(
            CharacterEditScreen(self.selected_character_id),
            self._handle_edit_result
        )

    def _handle_edit_result(self, saved: bool) -> None:
        """Handle the result from the character edit screen."""
        if saved:
            # Reload the party table to reflect changes
            self._load_party_from_database()

            # Update game state
            for char_data in self._characters.values():
                if char_data["id"] == self.selected_character_id:
                    # Update the detail panel
                    self._update_character_detail(char_data)
                    break

    def _remove_selected(self) -> None:
        """Remove the selected character from party and database."""
        if not self.selected_character_id:
            self.app.notify("No character selected.", title="Party")
            return

        try:
            with session_scope() as session:
                character = session.query(Character).filter_by(id=self.selected_character_id).first()
                if character:
                    char_name = character.name
                    session.delete(character)

                    # Also remove from app's game state
                    self.app.game_state.characters = [
                        c for c in self.app.game_state.characters
                        if c.get("id") != self.selected_character_id
                    ]

                    self.app.notify(f"{char_name} removed from party.", title="Party")

            # Reload the table
            self.selected_character_id = None
            self._load_party_from_database()

            # Clear detail panel
            detail = self.query_one("#character-detail", Static)
            detail.update("Select a character to view details.")
            stats = self.query_one("#character-stats", Static)
            stats.update("")

        except Exception as e:
            self.app.notify(f"Error removing character: {e}", title="Error", severity="error")
