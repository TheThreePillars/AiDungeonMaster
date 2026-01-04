"""Spell selection screen for casting spells in combat."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label, Static

from ...game.spells import SPELLS, SpellCaster, get_spells_for_class


class SpellSelectScreen(ModalScreen):
    """Modal screen for selecting a spell to cast."""

    CSS = """
    SpellSelectScreen {
        align: center middle;
    }

    #spell-dialog {
        width: 70;
        height: 30;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    #spell-table {
        height: 1fr;
        margin-bottom: 1;
    }

    #spell-info {
        height: 6;
        border: solid $accent;
        padding: 1;
        margin-bottom: 1;
    }

    #slots-display {
        text-align: center;
        margin-bottom: 1;
    }

    .header {
        text-style: bold;
        color: $primary;
        text-align: center;
        margin-bottom: 1;
    }

    #button-row {
        height: 3;
        align: center middle;
    }
    """

    def __init__(
        self,
        class_name: str,
        caster_level: int,
        casting_ability: int,
        spellcaster: SpellCaster | None = None,
    ):
        super().__init__()
        self.class_name = class_name
        self.caster_level = caster_level
        self.casting_ability = casting_ability

        # Use provided spellcaster or create one
        if spellcaster:
            self.spellcaster = spellcaster
        else:
            self.spellcaster = SpellCaster(
                class_name=class_name,
                caster_level=caster_level,
                casting_ability_score=casting_ability,
            )

        self.selected_spell: str | None = None

    def compose(self) -> ComposeResult:
        with Container(id="spell-dialog"):
            yield Label("Select Spell", classes="header")
            yield Static(self.spellcaster.get_slots_display(), id="slots-display")
            yield DataTable(id="spell-table")
            yield Static("Select a spell to see details.", id="spell-info")
            with Container(id="button-row"):
                yield Button("Cast", id="btn-cast", variant="primary")
                yield Button("Cancel", id="btn-cancel")

    def on_mount(self) -> None:
        """Set up the spell table."""
        table = self.query_one("#spell-table", DataTable)
        table.add_columns("Lvl", "Spell", "School", "Save")
        table.cursor_type = "row"

        # Get available spells for this class
        max_spell_level = self._get_max_spell_level()
        spells = get_spells_for_class(self.class_name, max_spell_level)

        for spell in spells:
            spell_level = spell.get_level_for_class(self.class_name.lower())
            remaining = self.spellcaster.spell_slots.get_remaining(spell_level)

            # Mark unavailable spells
            level_str = str(spell_level)
            if remaining <= 0:
                level_str = f"({spell_level})"  # Parentheses = no slots

            save_str = spell.saving_throw if spell.saving_throw != "None" else "-"
            table.add_row(level_str, spell.name, spell.school.value[:4], save_str)

    def _get_max_spell_level(self) -> int:
        """Get max spell level this caster can use."""
        for level in range(9, -1, -1):
            if self.spellcaster.spell_slots.max_slots.get(level, 0) > 0:
                return level
        return 0

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle spell selection."""
        table = self.query_one("#spell-table", DataTable)
        if event.row_key is None:
            return

        row_data = table.get_row(event.row_key)
        if not row_data:
            return

        spell_name = row_data[1]
        self.selected_spell = spell_name.lower()

        # Show spell info
        if self.selected_spell in SPELLS:
            spell = SPELLS[self.selected_spell]
            spell_level = spell.get_level_for_class(self.class_name.lower())
            remaining = self.spellcaster.spell_slots.get_remaining(spell_level)
            dc = self.spellcaster.get_spell_dc(spell_level)

            info = f"[bold]{spell.name}[/bold] (Level {spell_level})\n"
            info += f"School: {spell.school.value} | Range: {spell.range}\n"

            if spell.damage_dice:
                info += f"Damage: {spell.damage_dice}/level ({spell.damage_type})\n"
            if spell.heal_dice:
                info += f"Healing: {spell.heal_dice} + level\n"

            info += f"Save DC: {dc} ({spell.saving_throw}) | Slots: {remaining}"

            spell_info = self.query_one("#spell-info", Static)
            spell_info.update(info)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-cast":
            if self.selected_spell:
                can_cast, reason = self.spellcaster.can_cast(self.selected_spell)
                if can_cast:
                    self.dismiss(self.selected_spell)
                else:
                    self.app.notify(reason, title="Cannot Cast", severity="error")
            else:
                self.app.notify("Select a spell first.", title="Spell")
        elif event.button.id == "btn-cancel":
            self.dismiss(None)
