"""Combat view screen for AI Dungeon Master."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Label,
    RichLog,
    Select,
    Static,
)

from ..icons import Icons
from ...game.combat import CombatTracker, Combatant, CombatantType, CombatState
from ...game.conditions import ConditionManager
from ...game.dice import DiceRoller
from ...game.spells import SpellCaster, SPELLS


# Common enemy templates for quick adding
ENEMY_TEMPLATES = {
    "Goblin": {
        "max_hp": 6, "armor_class": 16, "touch_ac": 13, "flat_footed_ac": 14,
        "attack_bonus": 2, "damage_dice": "1d4", "damage_bonus": 1,
        "initiative_modifier": 6, "cmb": -1, "cmd": 11,
    },
    "Goblin Warrior": {
        "max_hp": 10, "armor_class": 17, "touch_ac": 13, "flat_footed_ac": 15,
        "attack_bonus": 4, "damage_dice": "1d6", "damage_bonus": 2,
        "initiative_modifier": 6, "cmb": 1, "cmd": 13,
    },
    "Orc": {
        "max_hp": 13, "armor_class": 13, "touch_ac": 10, "flat_footed_ac": 13,
        "attack_bonus": 5, "damage_dice": "2d4", "damage_bonus": 4,
        "initiative_modifier": 0, "cmb": 5, "cmd": 15,
    },
    "Skeleton": {
        "max_hp": 4, "armor_class": 16, "touch_ac": 12, "flat_footed_ac": 14,
        "attack_bonus": 2, "damage_dice": "1d4", "damage_bonus": 2,
        "initiative_modifier": 6, "cmb": 2, "cmd": 14,
    },
    "Zombie": {
        "max_hp": 12, "armor_class": 12, "touch_ac": 10, "flat_footed_ac": 12,
        "attack_bonus": 4, "damage_dice": "1d6", "damage_bonus": 4,
        "initiative_modifier": -2, "cmb": 4, "cmd": 12,
    },
    "Wolf": {
        "max_hp": 13, "armor_class": 14, "touch_ac": 12, "flat_footed_ac": 12,
        "attack_bonus": 3, "damage_dice": "1d6", "damage_bonus": 1,
        "initiative_modifier": 2, "cmb": 2, "cmd": 14,
    },
    "Ogre": {
        "max_hp": 30, "armor_class": 17, "touch_ac": 8, "flat_footed_ac": 17,
        "attack_bonus": 8, "damage_dice": "2d8", "damage_bonus": 7,
        "initiative_modifier": -1, "cmb": 12, "cmd": 21,
    },
}


class CombatViewScreen(Screen):
    """The combat encounter screen."""

    CSS = """
    CombatViewScreen {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 2fr;
    }

    #combat-sidebar {
        height: 100%;
        background: $surface-darken-1;
        border-right: wide $error;
        padding: 1;
    }

    #combat-main {
        height: 100%;
        background: $surface;
    }

    #combat-log {
        height: 1fr;
        background: $surface-darken-2;
        border: none;
        padding: 1;
    }

    #action-buttons {
        dock: bottom;
        height: auto;
        padding: 1;
        background: $surface-darken-1;
        border-top: solid $error 50%;
    }

    .action-row {
        margin-bottom: 1;
        height: 4;
    }

    .action-row Button {
        margin-right: 1;
    }

    #round-counter {
        text-align: center;
        text-style: bold;
        color: $text;
        background: $error;
        border: none;
        padding: 1;
        margin-bottom: 1;
    }

    .section-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
        padding-bottom: 1;
        border-bottom: solid $primary 30%;
    }

    #target-info {
        background: $surface-darken-2;
        border: round $warning 50%;
        padding: 1;
        margin-top: 1;
        height: auto;
    }

    #initiative-table {
        height: auto;
        max-height: 15;
        background: $surface-darken-2;
    }

    #enemy-select {
        margin-bottom: 1;
    }

    .current-turn {
        background: $primary;
    }

    #btn-attack, #btn-full-attack {
        background: $error;
    }

    #btn-end-turn {
        background: $success;
    }

    #btn-spell {
        background: $primary;
    }
    """

    def __init__(self):
        """Initialize combat view."""
        super().__init__()
        self.combat_tracker = CombatTracker()
        self.roller = DiceRoller()
        self.selected_target: Combatant | None = None
        self._enemy_count: dict[str, int] = {}

    def compose(self) -> ComposeResult:
        """Compose the combat screen."""
        i = Icons

        # Left sidebar - Initiative and actions
        with Container(id="combat-sidebar"):
            yield Static(f"{i.SWORD} Round 1", id="round-counter")
            yield Label(f"{i.TARGET}  Initiative Order", classes="section-header")
            yield DataTable(id="initiative-table")
            yield Static("", id="target-info")
            yield Label(f"{i.MONSTER}  Add Enemy", classes="section-header")
            yield Select(
                [(name, name) for name in ENEMY_TEMPLATES.keys()],
                id="enemy-select",
                prompt="Select enemy type",
            )
            yield Button(f"{i.NEW}  Add Enemy", id="btn-add-enemy", variant="warning")

        # Main area - Combat log and action buttons
        with Container(id="combat-main"):
            yield Label(f"{i.BOOK}  Combat Log", classes="section-header")
            yield RichLog(id="combat-log", highlight=True, markup=True, wrap=True)

            with Container(id="action-buttons"):
                with Horizontal(classes="action-row"):
                    yield Button(f"{i.SWORD} Attack", id="btn-attack", variant="error")
                    yield Button(f"{i.SWORD}{i.SWORD} Full Attack", id="btn-full-attack", variant="error")
                    yield Button(f"{i.FORWARD} Charge", id="btn-charge", variant="warning")
                with Horizontal(classes="action-row"):
                    yield Button(f"{i.TRAVEL} Move", id="btn-move")
                    yield Button("5-ft Step", id="btn-5ft")
                    yield Button(f"{i.BACK} Withdraw", id="btn-withdraw")
                with Horizontal(classes="action-row"):
                    yield Button(f"{i.MAGIC} Cast Spell", id="btn-spell", variant="primary")
                    yield Button(f"{i.POTION} Use Item", id="btn-item")
                    yield Button(f"{i.TARGET} Maneuver", id="btn-cmb")
                with Horizontal(classes="action-row"):
                    yield Button(f"{i.TIME} Delay", id="btn-delay")
                    yield Button(f"{i.TARGET} Ready", id="btn-ready")
                    yield Button(f"{i.CHECK} End Turn", id="btn-end-turn", variant="success")
                    yield Button(f"{i.CLOSE} End Combat", id="btn-end-combat", variant="error")

    def on_mount(self) -> None:
        """Handle screen mount."""
        # Set up initiative table
        table = self.query_one("#initiative-table", DataTable)
        table.add_columns("Init", "Name", "HP", "AC", "Status")
        table.cursor_type = "row"

        # Set up combat tracker callbacks
        self.combat_tracker.on_turn_change = self._on_turn_change
        self.combat_tracker.on_round_change = self._on_round_change
        self.combat_tracker.on_combatant_update = self._on_combatant_update

        # Load party members as combatants
        self._load_party_combatants()

        # Update game state
        self.app.game_state.in_combat = True

        self._add_combat_message("[bold red]COMBAT BEGINS![/bold red]\n")
        self._add_combat_message("Add enemies, then initiative will be rolled.\n")

    def _load_party_combatants(self) -> None:
        """Load party members from game state into combat."""
        for char in self.app.game_state.characters:
            # Calculate initiative modifier from DEX
            # We'd need full character data for this, use a reasonable default
            dex_mod = 2  # Default

            combatant = Combatant(
                name=char.get("name", "Unknown"),
                combatant_type=CombatantType.PLAYER,
                max_hp=char.get("max_hp", 10),
                current_hp=char.get("current_hp", 10),
                armor_class=char.get("ac", 10),
                touch_ac=char.get("ac", 10) - 2,  # Simplified
                flat_footed_ac=char.get("ac", 10) - 2,  # Simplified
                initiative_modifier=dex_mod,
                attack_bonus=char.get("level", 1),  # BAB approximation
                damage_dice="1d8",  # Default weapon
                damage_bonus=2,  # STR mod approximation
                character_id=char.get("id"),
            )
            self.combat_tracker.add_combatant(combatant)

        self._refresh_initiative_table()

    def _add_enemy(self, enemy_type: str) -> None:
        """Add an enemy to combat."""
        if enemy_type not in ENEMY_TEMPLATES:
            return

        template = ENEMY_TEMPLATES[enemy_type]

        # Track enemy count for naming
        self._enemy_count[enemy_type] = self._enemy_count.get(enemy_type, 0) + 1
        count = self._enemy_count[enemy_type]
        name = f"{enemy_type} {count}" if count > 1 else enemy_type

        combatant = Combatant(
            name=name,
            combatant_type=CombatantType.ENEMY,
            max_hp=template["max_hp"],
            current_hp=template["max_hp"],
            armor_class=template["armor_class"],
            touch_ac=template["touch_ac"],
            flat_footed_ac=template["flat_footed_ac"],
            initiative_modifier=template["initiative_modifier"],
            attack_bonus=template["attack_bonus"],
            damage_dice=template["damage_dice"],
            damage_bonus=template["damage_bonus"],
            cmb=template["cmb"],
            cmd=template["cmd"],
        )

        self.combat_tracker.add_combatant(combatant)
        self._add_combat_message(f"[yellow]{name} enters combat![/yellow]\n")
        self._refresh_initiative_table()

    def _start_combat(self) -> None:
        """Start combat and roll initiative."""
        if self.combat_tracker.state != CombatState.NOT_STARTED:
            return

        if len(self.combat_tracker.combatants) < 2:
            self.app.notify("Add at least one enemy to start combat.", title="Combat")
            return

        self.combat_tracker.start_combat()

        self._add_combat_message("\n[bold]Rolling Initiative![/bold]\n")
        for combatant in self.combat_tracker.initiative_order:
            type_color = "cyan" if combatant.combatant_type == CombatantType.PLAYER else "red"
            self._add_combat_message(
                f"  [{type_color}]{combatant.name}[/{type_color}]: {combatant.initiative}\n"
            )

        self._add_combat_message(f"\n[bold]--- Round 1 ---[/bold]\n")

        current = self.combat_tracker.get_current_combatant()
        if current:
            self._add_combat_message(f"\n[bold green]{current.name}'s turn![/bold green]\n")

        self._refresh_initiative_table()

    def _refresh_initiative_table(self) -> None:
        """Refresh the initiative table display."""
        table = self.query_one("#initiative-table", DataTable)
        table.clear()

        if self.combat_tracker.state == CombatState.NOT_STARTED:
            # Show combatants without initiative
            for combatant in self.combat_tracker.combatants:
                hp_str = f"{combatant.current_hp}/{combatant.max_hp}"
                status = combatant.hp_status
                if combatant.conditions:
                    status = ", ".join(combatant.conditions[:2])
                table.add_row("--", combatant.name, hp_str, str(combatant.armor_class), status)
        else:
            # Show in initiative order
            for i, combatant in enumerate(self.combat_tracker.initiative_order):
                hp_str = f"{combatant.current_hp}/{combatant.max_hp}"
                status = combatant.hp_status
                if combatant.conditions:
                    status = ", ".join(combatant.conditions[:2])

                is_current = i == self.combat_tracker.current_turn
                name = f">> {combatant.name}" if is_current else combatant.name

                table.add_row(
                    str(combatant.initiative),
                    name,
                    hp_str,
                    str(combatant.armor_class),
                    status,
                )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection for targeting."""
        table = self.query_one("#initiative-table", DataTable)
        if event.row_key is None:
            return

        row_data = table.get_row(event.row_key)
        if not row_data:
            return

        # Find the combatant by name
        name = row_data[1].replace(">> ", "")  # Remove current turn marker
        for combatant in self.combat_tracker.combatants:
            if combatant.name == name:
                self.selected_target = combatant
                self._update_target_info(combatant)
                break

    def _update_target_info(self, target: Combatant) -> None:
        """Update the target info panel."""
        target_info = self.query_one("#target-info", Static)

        type_str = "Player" if target.combatant_type == CombatantType.PLAYER else "Enemy"
        conditions = ", ".join(target.conditions) if target.conditions else "None"

        target_info.update(f"""[bold]Target: {target.name}[/bold]
Type: {type_str}
HP: {target.current_hp}/{target.max_hp} ({target.hp_status})
AC: {target.armor_class} (Touch {target.touch_ac}, FF {target.flat_footed_ac})
CMD: {target.cmd}
Conditions: {conditions}""")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-add-enemy":
            select = self.query_one("#enemy-select", Select)
            if select.value and select.value != Select.BLANK:
                self._add_enemy(str(select.value))
                # Auto-start combat if this is the first enemy
                if self.combat_tracker.state == CombatState.NOT_STARTED:
                    if len(self.combat_tracker.get_combatants_by_type(CombatantType.ENEMY)) >= 1:
                        self._start_combat()
        elif button_id == "btn-attack":
            self._handle_attack()
        elif button_id == "btn-full-attack":
            self._handle_full_attack()
        elif button_id == "btn-charge":
            self._handle_charge()
        elif button_id == "btn-move":
            self._add_combat_message("Move action taken.\n")
        elif button_id == "btn-5ft":
            self._add_combat_message("5-foot step taken.\n")
        elif button_id == "btn-withdraw":
            self._add_combat_message("Withdraw action - moving away safely.\n")
            self._end_turn()
        elif button_id == "btn-spell":
            self._handle_spell()
        elif button_id == "btn-item":
            self._add_combat_message("Use item - select from inventory.\n")
        elif button_id == "btn-cmb":
            self._handle_combat_maneuver()
        elif button_id == "btn-delay":
            self._handle_delay()
        elif button_id == "btn-ready":
            self._handle_ready()
        elif button_id == "btn-end-turn":
            self._end_turn()
        elif button_id == "btn-end-combat":
            self._end_combat()

    def _handle_attack(self) -> None:
        """Handle a standard attack action."""
        if self.combat_tracker.state != CombatState.ACTIVE:
            self.app.notify("Combat hasn't started yet.", title="Combat")
            return

        current = self.combat_tracker.get_current_combatant()
        if not current:
            return

        if not self.selected_target:
            self.app.notify("Select a target first.", title="Combat")
            return

        if self.selected_target == current:
            self.app.notify("Can't attack yourself!", title="Combat")
            return

        # Make the attack
        result = self.combat_tracker.make_attack(current, self.selected_target)

        # Display result
        attack_text = f"\n[bold]{current.name}[/bold] attacks [bold]{self.selected_target.name}[/bold]!\n"
        natural_roll = result.attack_roll.roll.rolls[0] if result.attack_roll.roll.rolls else 0
        modifier = result.attack_roll.modifier
        attack_text += f"  Attack roll: {natural_roll}"
        if modifier != 0:
            attack_text += f" + {modifier}" if modifier > 0 else f" {modifier}"
        attack_text += f" = {result.attack_roll.total} vs AC {self.selected_target.armor_class}\n"

        if result.critical_threat and result.critical_confirmed:
            attack_text += f"  [bold yellow]CRITICAL HIT![/bold yellow]\n"
            attack_text += f"  Damage: {result.total_damage} (x2)\n"
        elif result.hit:
            attack_text += f"  [green]HIT![/green] Damage: {result.total_damage}\n"
        else:
            attack_text += f"  [red]MISS![/red]\n"

        # Check if target is down
        if self.selected_target.is_dead:
            attack_text += f"  [bold red]{self.selected_target.name} is DEAD![/bold red]\n"
        elif self.selected_target.is_dying:
            attack_text += f"  [red]{self.selected_target.name} is dying![/red]\n"
        elif not self.selected_target.is_conscious:
            attack_text += f"  [yellow]{self.selected_target.name} falls unconscious![/yellow]\n"

        self._add_combat_message(attack_text)
        self._refresh_initiative_table()
        self._check_combat_end()

    def _handle_full_attack(self) -> None:
        """Handle a full attack action."""
        if self.combat_tracker.state != CombatState.ACTIVE:
            return

        current = self.combat_tracker.get_current_combatant()
        if not current or not self.selected_target:
            self.app.notify("Select a target first.", title="Combat")
            return

        # For now, just do two attacks with -5 on second
        self._add_combat_message(f"\n[bold]{current.name}[/bold] makes a full attack!\n")

        # First attack
        result1 = self.combat_tracker.make_attack(current, self.selected_target)
        self._add_combat_message(f"  Attack 1: {result1.attack_roll} - {'HIT' if result1.hit else 'MISS'}")
        if result1.hit:
            self._add_combat_message(f" for {result1.total_damage} damage")
        self._add_combat_message("\n")

        # Second attack at -5 (if BAB high enough, simplified)
        if current.attack_bonus >= 6 and self.selected_target.is_conscious:
            result2 = self.combat_tracker.make_attack(current, self.selected_target, attack_bonus_modifier=-5)
            self._add_combat_message(f"  Attack 2: {result2.attack_roll} - {'HIT' if result2.hit else 'MISS'}")
            if result2.hit:
                self._add_combat_message(f" for {result2.total_damage} damage")
            self._add_combat_message("\n")

        self._refresh_initiative_table()
        self._check_combat_end()

    def _handle_charge(self) -> None:
        """Handle a charge action."""
        if self.combat_tracker.state != CombatState.ACTIVE:
            return

        current = self.combat_tracker.get_current_combatant()
        if not current or not self.selected_target:
            self.app.notify("Select a target first.", title="Combat")
            return

        self._add_combat_message(f"\n[bold]{current.name}[/bold] CHARGES at [bold]{self.selected_target.name}[/bold]!\n")

        # Charge: +2 attack, -2 AC
        result = self.combat_tracker.make_attack(current, self.selected_target, attack_bonus_modifier=2)

        if result.hit:
            self._add_combat_message(f"  [green]HIT![/green] Damage: {result.total_damage}\n")
        else:
            self._add_combat_message(f"  [red]MISS![/red]\n")

        self._add_combat_message(f"  ({current.name} is at -2 AC until next turn)\n")
        self._refresh_initiative_table()
        self._check_combat_end()
        self._end_turn()

    def _handle_combat_maneuver(self) -> None:
        """Handle combat maneuver."""
        if self.combat_tracker.state != CombatState.ACTIVE:
            return

        current = self.combat_tracker.get_current_combatant()
        if not current or not self.selected_target:
            self.app.notify("Select a target first.", title="Combat")
            return

        # Roll CMB vs CMD
        roll = self.roller.roll("1d20")
        cmb_total = roll.total + current.cmb

        self._add_combat_message(
            f"\n[bold]{current.name}[/bold] attempts a combat maneuver!\n"
            f"  CMB: {roll.total} + {current.cmb} = {cmb_total} vs CMD {self.selected_target.cmd}\n"
        )

        if cmb_total >= self.selected_target.cmd:
            self._add_combat_message(f"  [green]SUCCESS![/green] Maneuver succeeds!\n")
        else:
            self._add_combat_message(f"  [red]FAILED![/red]\n")

    def _handle_spell(self) -> None:
        """Handle casting a spell."""
        if self.combat_tracker.state != CombatState.ACTIVE:
            self.app.notify("Combat hasn't started yet.", title="Combat")
            return

        current = self.combat_tracker.get_current_combatant()
        if not current or current.combatant_type != CombatantType.PLAYER:
            self.app.notify("Only players can cast spells this way.", title="Combat")
            return

        # Get character info from game state
        char_data = None
        for char in self.app.game_state.characters:
            if char.get("id") == current.character_id:
                char_data = char
                break

        if not char_data:
            self.app.notify("Character data not found.", title="Combat")
            return

        char_class = char_data.get("class", "Fighter")

        # Check if this class can cast spells
        from ...characters.classes import CLASSES
        class_info = CLASSES.get(char_class)
        if not class_info or not class_info.is_spellcaster():
            self.app.notify(f"{char_class}s cannot cast spells.", title="Combat")
            return

        # Create spellcaster (simplified - use default casting ability)
        casting_ability = 14  # Default casting ability score

        from .spell_select import SpellSelectScreen
        spellcaster = SpellCaster(
            class_name=char_class,
            caster_level=char_data.get("level", 1),
            casting_ability_score=casting_ability,
        )

        def on_spell_selected(spell_name: str | None) -> None:
            if spell_name:
                self._cast_spell(current, spellcaster, spell_name)

        self.app.push_screen(
            SpellSelectScreen(
                class_name=char_class,
                caster_level=char_data.get("level", 1),
                casting_ability=casting_ability,
                spellcaster=spellcaster,
            ),
            on_spell_selected,
        )

    def _cast_spell(self, caster: Combatant, spellcaster: SpellCaster, spell_name: str) -> None:
        """Execute spell casting."""
        target_name = self.selected_target.name if self.selected_target else "the area"
        result = spellcaster.cast_spell(spell_name, target_name)

        if not result["success"]:
            self._add_combat_message(f"\n[red]Failed to cast: {result['message']}[/red]\n")
            return

        spell = SPELLS.get(spell_name.lower())
        self._add_combat_message(f"\n[bold magenta]{caster.name}[/bold magenta] casts [bold]{spell.name}[/bold]!\n")

        if result.get("save_dc"):
            self._add_combat_message(f"  Save DC: {result['save_dc']} ({result['save_type']})\n")

        # Apply damage
        if result.get("damage") and self.selected_target:
            damage = result["damage"]
            damage_type = result.get("damage_type", "magical")

            # Check for save
            saved = False
            if result.get("save_type") and "half" in result["save_type"].lower():
                save_roll = self.roller.roll("1d20+5")  # Simplified save
                if save_roll.total >= result["save_dc"]:
                    damage = damage // 2
                    saved = True
                    self._add_combat_message(f"  {self.selected_target.name} saves! (half damage)\n")

            self.selected_target.take_damage(damage)
            self._add_combat_message(
                f"  [red]{self.selected_target.name} takes {damage} {damage_type} damage![/red]\n"
            )

            if self.selected_target.is_dead:
                self._add_combat_message(f"  [bold red]{self.selected_target.name} is slain![/bold red]\n")

        # Apply healing
        if result.get("healing") and self.selected_target:
            healing = result["healing"]
            self.selected_target.heal(healing)
            self._add_combat_message(
                f"  [green]{self.selected_target.name} is healed for {healing} HP![/green]\n"
            )

        self._refresh_initiative_table()
        self._check_combat_end()

    def _handle_delay(self) -> None:
        """Handle delay action."""
        if self.combat_tracker.state != CombatState.ACTIVE:
            return

        current = self.combat_tracker.get_current_combatant()
        if current:
            self._add_combat_message(f"\n{current.name} delays their turn.\n")
            # Move to end of current initiative
            self.combat_tracker.delay_turn(0)
            self._refresh_initiative_table()

    def _handle_ready(self) -> None:
        """Handle ready action."""
        if self.combat_tracker.state != CombatState.ACTIVE:
            return

        current = self.combat_tracker.get_current_combatant()
        if current:
            self._add_combat_message(f"\n{current.name} readies an action.\n")
            current.add_condition("Readying")
            self._end_turn()

    def _end_turn(self) -> None:
        """End the current turn."""
        if self.combat_tracker.state != CombatState.ACTIVE:
            return

        next_combatant = self.combat_tracker.next_turn()
        self._refresh_initiative_table()

        if next_combatant:
            type_color = "green" if next_combatant.combatant_type == CombatantType.PLAYER else "red"
            self._add_combat_message(f"\n[bold {type_color}]{next_combatant.name}'s turn![/bold {type_color}]\n")

            # AI enemies take automatic actions
            if next_combatant.combatant_type == CombatantType.ENEMY:
                self._enemy_turn(next_combatant)

    def _enemy_turn(self, enemy: Combatant) -> None:
        """Handle an enemy's turn automatically."""
        # Find a player target
        players = self.combat_tracker.get_active_players()
        if not players:
            self._end_turn()
            return

        # Pick random target (or lowest HP)
        target = min(players, key=lambda p: p.current_hp)

        self._add_combat_message(f"  {enemy.name} attacks {target.name}!\n")

        result = self.combat_tracker.make_attack(enemy, target)

        if result.hit:
            self._add_combat_message(f"  [red]HIT![/red] {target.name} takes {result.total_damage} damage!\n")
            if target.is_dying:
                self._add_combat_message(f"  [bold red]{target.name} falls![/bold red]\n")
        else:
            self._add_combat_message(f"  [green]MISS![/green]\n")

        self._refresh_initiative_table()
        self._check_combat_end()

        # Auto-end enemy turn
        if self.combat_tracker.state == CombatState.ACTIVE:
            self.call_later(self._end_turn, delay=0.5)

    def _on_turn_change(self, combatant: Combatant) -> None:
        """Callback for turn changes."""
        pass  # Handled in _end_turn

    def _on_round_change(self, round_number: int) -> None:
        """Callback for round changes."""
        i = Icons
        round_counter = self.query_one("#round-counter", Static)
        round_counter.update(f"{i.SWORD} Round {round_number}")
        self._add_combat_message(f"\n[bold]--- Round {round_number} ---[/bold]\n")

    def _on_combatant_update(self, combatant: Combatant) -> None:
        """Callback for combatant updates."""
        self._refresh_initiative_table()

    def _check_combat_end(self) -> None:
        """Check if combat should end."""
        result = self.combat_tracker.check_combat_end()

        if result == "victory":
            self._add_combat_message("\n[bold green]VICTORY![/bold green]\n")
            self._add_combat_message("All enemies have been defeated!\n")
            self.combat_tracker.end_combat()
        elif result == "defeat":
            self._add_combat_message("\n[bold red]DEFEAT![/bold red]\n")
            self._add_combat_message("The party has fallen...\n")
            self.combat_tracker.end_combat()

    def _end_combat(self) -> None:
        """End the combat encounter."""
        self.combat_tracker.end_combat()
        self.app.game_state.in_combat = False

        # Update character HP in game state
        for combatant in self.combat_tracker.combatants:
            if combatant.combatant_type == CombatantType.PLAYER and combatant.character_id:
                for char in self.app.game_state.characters:
                    if char.get("id") == combatant.character_id:
                        char["current_hp"] = combatant.current_hp
                        break

        self._add_combat_message("\n[bold]COMBAT ENDED![/bold]\n")
        self.app.notify("Combat encounter ended.", title="Combat")
        self.app.pop_screen()

    def _add_combat_message(self, text: str) -> None:
        """Add a message to the combat log."""
        log = self.query_one("#combat-log", RichLog)
        log.write(text)
