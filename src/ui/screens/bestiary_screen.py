"""Bestiary screen for browsing and spawning monsters."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Label, Select, Static

from ..icons import Icons
from ...game.bestiary import (
    BESTIARY,
    Monster,
    MonsterType,
    get_monster,
    get_monsters_by_cr_range,
    get_monsters_by_type,
    list_all_monsters,
)
from ...game.combat import Combatant, CombatantType


class BestiaryScreen(Screen):
    """Screen for browsing the monster bestiary."""

    CSS = """
    BestiaryScreen {
        layout: horizontal;
    }

    #monster-list-panel {
        width: 35;
        height: 100%;
        background: $surface-darken-1;
        border-right: solid $primary 50%;
    }

    #monster-detail-panel {
        width: 1fr;
        height: 100%;
        background: $surface;
        padding: 1;
    }

    .panel-header {
        text-style: bold;
        color: $primary;
        text-align: center;
        padding: 1;
        border-bottom: solid $primary 50%;
        background: $primary 20%;
    }

    #filter-row {
        height: 3;
        padding: 0 1;
    }

    #search-input {
        width: 1fr;
    }

    #type-filter {
        width: 15;
    }

    #cr-filter {
        width: 10;
    }

    #monster-table {
        height: 1fr;
    }

    .section-title {
        text-style: bold;
        color: $secondary;
        margin-top: 1;
        margin-bottom: 0;
    }

    .stat-block {
        margin-left: 2;
    }

    .stat-line {
        height: 1;
    }

    #ability-scores {
        height: 3;
        margin: 1 0;
        padding: 1;
        border: solid $secondary;
    }

    #attacks-section {
        margin: 1 0;
        padding: 1;
        border: solid $warning;
    }

    #special-section {
        margin: 1 0;
        padding: 1;
        border: solid $error;
    }

    #monster-description {
        margin: 1 0;
        padding: 1;
        border: solid $primary;
        height: auto;
    }

    #button-row {
        dock: bottom;
        height: 3;
        padding: 0 1;
    }

    Button {
        margin: 0 1;
    }

    .no-selection {
        text-align: center;
        color: $text-muted;
        margin-top: 10;
    }
    """

    def __init__(self):
        super().__init__()
        self.selected_monster: Monster | None = None
        self.filtered_monsters: list[Monster] = list_all_monsters()

    def compose(self) -> ComposeResult:
        i = Icons

        # Left panel - monster list
        with Container(id="monster-list-panel"):
            yield Label(f"{i.MONSTER}  Bestiary", classes="panel-header")

            with Horizontal(id="filter-row"):
                yield Input(placeholder="Search...", id="search-input")

            with Horizontal(id="filter-row"):
                yield Select(
                    [("All Types", "all")] + [(t.value, t.name) for t in MonsterType],
                    id="type-filter",
                    value="all",
                )
                yield Select(
                    [
                        ("All CR", "all"),
                        ("CR 0-1", "0-1"),
                        ("CR 2-3", "2-3"),
                        ("CR 4-5", "4-5"),
                        ("CR 6-10", "6-10"),
                        ("CR 11+", "11+"),
                    ],
                    id="cr-filter",
                    value="all",
                )

            yield DataTable(id="monster-table")

        # Right panel - monster details
        with Container(id="monster-detail-panel"):
            yield Label(f"{i.BOOK}  Monster Details", classes="panel-header")

            with VerticalScroll():
                yield Static("Select a monster to view details.", id="detail-content", classes="no-selection")

            with Horizontal(id="button-row"):
                yield Button(f"{i.SWORD}  Spawn in Combat", id="btn-spawn", variant="warning", disabled=True)
                yield Button(f"{i.BACK}  Back", id="btn-back")

    def on_mount(self) -> None:
        """Initialize the monster table."""
        table = self.query_one("#monster-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Name", "CR", "Type")
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh the monster table with filtered results."""
        table = self.query_one("#monster-table", DataTable)
        table.clear()

        for monster in self.filtered_monsters:
            cr_str = self._format_cr(monster.challenge_rating)
            type_str = monster.monster_type.value[:10]
            table.add_row(monster.name, cr_str, type_str, key=monster.name.lower())

    def _format_cr(self, cr: float) -> str:
        """Format CR value for display."""
        if cr == 0.125:
            return "1/8"
        elif cr == 0.25:
            return "1/4"
        elif cr == 0.33:
            return "1/3"
        elif cr == 0.5:
            return "1/2"
        elif cr == int(cr):
            return str(int(cr))
        return str(cr)

    def _apply_filters(self) -> None:
        """Apply search and type filters."""
        search_text = self.query_one("#search-input", Input).value.lower().strip()
        type_filter = self.query_one("#type-filter", Select).value
        cr_filter = self.query_one("#cr-filter", Select).value

        # Start with all monsters
        monsters = list_all_monsters()

        # Apply type filter
        if type_filter != "all":
            try:
                monster_type = MonsterType[type_filter]
                monsters = [m for m in monsters if m.monster_type == monster_type]
            except KeyError:
                pass

        # Apply CR filter
        if cr_filter != "all":
            cr_ranges = {
                "0-1": (0, 1),
                "2-3": (2, 3),
                "4-5": (4, 5),
                "6-10": (6, 10),
                "11+": (11, 100),
            }
            if cr_filter in cr_ranges:
                min_cr, max_cr = cr_ranges[cr_filter]
                monsters = [m for m in monsters if min_cr <= m.challenge_rating <= max_cr]

        # Apply search filter
        if search_text:
            monsters = [m for m in monsters if search_text in m.name.lower() or
                       search_text in m.description.lower()]

        self.filtered_monsters = monsters
        self._refresh_table()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self._apply_filters()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle filter changes."""
        self._apply_filters()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle monster selection."""
        if event.row_key:
            monster = get_monster(str(event.row_key.value))
            if monster:
                self.selected_monster = monster
                self._show_monster_details(monster)
                self.query_one("#btn-spawn", Button).disabled = False

    def _show_monster_details(self, monster: Monster) -> None:
        """Display monster details."""
        cr_str = self._format_cr(monster.challenge_rating)
        xp = monster.get_xp_reward()

        # Build stat block
        lines = []

        # Header
        lines.append(f"[bold]{monster.name}[/bold]")
        lines.append(f"CR {cr_str} ({xp:,} XP)")
        lines.append(f"{monster.alignment} {monster.size.value} {monster.monster_type.value}")
        if monster.subtypes:
            lines.append(f"Subtypes: {', '.join(monster.subtypes)}")
        lines.append("")

        # Defense
        lines.append("[bold cyan]DEFENSE[/bold cyan]")
        lines.append(f"  AC {monster.armor_class}, touch {monster.touch_ac}, flat-footed {monster.flat_footed_ac}")
        lines.append(f"  HP {monster.hp} ({monster.hit_dice})")
        lines.append(f"  Fort +{monster.fortitude}, Ref +{monster.reflex}, Will +{monster.will}")

        if monster.damage_reduction:
            lines.append(f"  DR {monster.damage_reduction}")
        if monster.immunities:
            lines.append(f"  Immune {', '.join(monster.immunities)}")
        if monster.resistances:
            res_str = ", ".join(f"{k} {v}" for k, v in monster.resistances.items())
            lines.append(f"  Resist {res_str}")
        if monster.spell_resistance:
            lines.append(f"  SR {monster.spell_resistance}")
        lines.append("")

        # Offense
        lines.append("[bold yellow]OFFENSE[/bold yellow]")
        lines.append(f"  Speed {monster.speed} ft.")
        lines.append(f"  Base Atk +{monster.base_attack_bonus}; CMB +{monster.cmb}; CMD {monster.cmd}")

        for attack in monster.attacks:
            dmg_str = f"{attack.damage_dice}"
            if attack.damage_bonus > 0:
                dmg_str += f"+{attack.damage_bonus}"
            elif attack.damage_bonus < 0:
                dmg_str += str(attack.damage_bonus)

            special = f" {attack.special}" if attack.special else ""
            lines.append(f"  {attack.name} +{attack.attack_bonus} ({dmg_str} {attack.damage_type}{special})")
        lines.append("")

        # Statistics
        lines.append("[bold green]STATISTICS[/bold green]")
        lines.append(f"  Str {monster.strength}, Dex {monster.dexterity}, Con {monster.constitution or '—'}, "
                    f"Int {monster.intelligence}, Wis {monster.wisdom}, Cha {monster.charisma}")
        lines.append(f"  Init +{monster.initiative}")

        if monster.feats:
            lines.append(f"  Feats {', '.join(monster.feats)}")

        if monster.skills:
            skill_str = ", ".join(f"{k} +{v}" for k, v in monster.skills.items())
            lines.append(f"  Skills {skill_str}")
        lines.append("")

        # Senses
        senses = []
        if monster.darkvision:
            senses.append(f"darkvision {monster.darkvision} ft.")
        if monster.low_light_vision:
            senses.append("low-light vision")
        if monster.scent:
            senses.append("scent")
        if monster.blindsense:
            senses.append(f"blindsense {monster.blindsense} ft.")
        if senses:
            lines.append(f"[bold]Senses[/bold] {', '.join(senses)}")
            lines.append("")

        # Special Abilities
        if monster.special_abilities:
            lines.append("[bold red]SPECIAL ABILITIES[/bold red]")
            for ability in monster.special_abilities:
                lines.append(f"  [bold]{ability.name}[/bold] ({ability.ability_type})")
                # Wrap long descriptions
                desc = ability.description
                while len(desc) > 60:
                    split_pos = desc[:60].rfind(' ')
                    if split_pos == -1:
                        split_pos = 60
                    lines.append(f"    {desc[:split_pos]}")
                    desc = desc[split_pos:].strip()
                lines.append(f"    {desc}")
            lines.append("")

        # Ecology
        lines.append("[bold magenta]ECOLOGY[/bold magenta]")
        lines.append(f"  Environment {monster.environment}")
        lines.append(f"  Organization {monster.organization}")
        lines.append(f"  Treasure {monster.treasure}")
        lines.append("")

        # Description
        if monster.description:
            lines.append("[bold]DESCRIPTION[/bold]")
            # Word wrap description
            desc = monster.description
            while len(desc) > 55:
                split_pos = desc[:55].rfind(' ')
                if split_pos == -1:
                    split_pos = 55
                lines.append(f"  {desc[:split_pos]}")
                desc = desc[split_pos:].strip()
            lines.append(f"  {desc}")

        content = self.query_one("#detail-content", Static)
        content.update("\n".join(lines))
        content.remove_class("no-selection")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-spawn":
            self._spawn_monster()

    def _spawn_monster(self) -> None:
        """Spawn the selected monster into combat."""
        if not self.selected_monster:
            return

        monster = self.selected_monster

        # Check if we have an active combat tracker
        if not hasattr(self.app, 'combat_tracker') or self.app.combat_tracker is None:
            self.app.notify("No active combat! Start combat first.", title="Error", severity="error")
            return

        # Create combatant from monster
        primary_attack = monster.attacks[0] if monster.attacks else None

        combatant = Combatant(
            name=monster.name,
            combatant_type=CombatantType.ENEMY,
            max_hp=monster.hp,
            current_hp=monster.hp,
            armor_class=monster.armor_class,
            touch_ac=monster.touch_ac,
            flat_footed_ac=monster.flat_footed_ac,
            attack_bonus=primary_attack.attack_bonus if primary_attack else monster.base_attack_bonus,
            damage_dice=primary_attack.damage_dice if primary_attack else "1d4",
            damage_bonus=primary_attack.damage_bonus if primary_attack else 0,
            initiative_modifier=monster.initiative,
        )

        # Add to combat tracker
        self.app.combat_tracker.add_combatant(combatant)

        # Roll initiative for the new combatant
        from ...game.dice import DiceRoller
        roller = DiceRoller()
        init_roll = roller.roll("1d20").total + monster.initiative
        combatant.initiative = init_roll

        # Re-sort initiative order
        self.app.combat_tracker.initiative_order.append(combatant)
        self.app.combat_tracker.initiative_order.sort(key=lambda c: c.initiative, reverse=True)

        self.app.notify(f"Spawned {monster.name} (Init: {init_roll})!", title="Monster Spawned")


class BestiaryModal(Screen):
    """Modal version of bestiary for quick monster lookup."""

    CSS = """
    BestiaryModal {
        align: center middle;
    }

    #modal-container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: thick $primary;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="modal-container"):
            yield BestiaryScreen()
