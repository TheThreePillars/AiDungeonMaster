"""Combat view screen for AI Dungeon Master."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Label,
    RichLog,
    Static,
)


class InitiativeTracker(Static):
    """Display and manage initiative order."""

    CSS = """
    InitiativeTracker {
        height: auto;
        border: solid $warning;
        padding: 1;
    }

    .tracker-header {
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }

    .current-turn {
        background: $primary;
        color: $text;
    }
    """

    def __init__(self, **kwargs):
        """Initialize the initiative tracker."""
        super().__init__(**kwargs)
        self.combatants = []
        self.current_index = 0

    def compose(self) -> ComposeResult:
        """Compose the initiative tracker."""
        yield Label("Initiative Order", classes="tracker-header")
        yield DataTable(id="initiative-table")

    def on_mount(self) -> None:
        """Set up the initiative table."""
        table = self.query_one("#initiative-table", DataTable)
        table.add_columns("Init", "Name", "HP", "AC", "Status")

        # Add some example combatants for demonstration
        self._add_example_combatants()

    def _add_example_combatants(self) -> None:
        """Add example combatants for demonstration."""
        table = self.query_one("#initiative-table", DataTable)

        examples = [
            (18, "Valeros (Fighter)", "45/45", "18", ""),
            (15, "Merisiel (Rogue)", "32/32", "17", ""),
            (12, "Goblin 1", "8/8", "16", ""),
            (12, "Goblin 2", "8/8", "16", ""),
            (10, "Kyra (Cleric)", "38/38", "16", ""),
            (5, "Goblin Boss", "21/21", "17", ""),
        ]

        for init, name, hp, ac, status in examples:
            table.add_row(str(init), name, hp, ac, status)

    def highlight_current(self) -> None:
        """Highlight the current combatant."""
        table = self.query_one("#initiative-table", DataTable)
        if self.current_index < table.row_count:
            table.move_cursor(row=self.current_index)

    def next_turn(self) -> None:
        """Advance to the next turn."""
        table = self.query_one("#initiative-table", DataTable)
        if table.row_count > 0:
            self.current_index = (self.current_index + 1) % table.row_count
            self.highlight_current()


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
        border: solid $error;
        padding: 1;
    }

    #combat-main {
        height: 100%;
        border: solid $secondary;
    }

    #combat-log {
        height: 1fr;
        border: none;
    }

    #action-buttons {
        dock: bottom;
        height: auto;
        padding: 1;
    }

    .action-row {
        margin-bottom: 1;
    }

    Button {
        margin-right: 1;
    }

    #round-counter {
        text-align: center;
        text-style: bold;
        color: $warning;
        border: solid $warning;
        padding: 1;
        margin-bottom: 1;
    }

    .section-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #target-info {
        border: solid $accent;
        padding: 1;
        margin-top: 1;
    }
    """

    def __init__(self):
        """Initialize combat view."""
        super().__init__()
        self.current_round = 1
        self.current_turn = 0

    def compose(self) -> ComposeResult:
        """Compose the combat screen."""
        # Left sidebar - Initiative and actions
        with Container(id="combat-sidebar"):
            yield Static("Round 1", id="round-counter")
            yield InitiativeTracker(id="initiative-tracker")
            yield Static(id="target-info")

        # Main area - Combat log and action buttons
        with Container(id="combat-main"):
            yield Label("Combat Log", classes="section-header")
            yield RichLog(id="combat-log", highlight=True, markup=True)

            with Container(id="action-buttons"):
                with Horizontal(classes="action-row"):
                    yield Button("Attack", id="btn-attack", variant="error")
                    yield Button("Full Attack", id="btn-full-attack", variant="error")
                    yield Button("Charge", id="btn-charge", variant="warning")
                with Horizontal(classes="action-row"):
                    yield Button("Move", id="btn-move")
                    yield Button("5-ft Step", id="btn-5ft")
                    yield Button("Withdraw", id="btn-withdraw")
                with Horizontal(classes="action-row"):
                    yield Button("Cast Spell", id="btn-spell", variant="primary")
                    yield Button("Use Item", id="btn-item")
                    yield Button("Special", id="btn-special")
                with Horizontal(classes="action-row"):
                    yield Button("Delay", id="btn-delay")
                    yield Button("Ready", id="btn-ready")
                    yield Button("End Turn", id="btn-end-turn", variant="success")
                    yield Button("End Combat", id="btn-end-combat", variant="error")

    def on_mount(self) -> None:
        """Handle screen mount."""
        self._add_combat_message("[bold red]COMBAT BEGINS![/bold red]\n")
        self._add_combat_message("Roll for initiative!\n")
        self._add_combat_message("---\n")
        self._add_combat_message("[bold]Round 1[/bold]\n")
        self._add_combat_message("Valeros's turn!\n")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-attack":
            self._handle_attack()
        elif button_id == "btn-full-attack":
            self._add_combat_message("Full attack action selected.\n")
        elif button_id == "btn-charge":
            self._add_combat_message("Charge action selected.\n")
        elif button_id == "btn-move":
            self._add_combat_message("Move action - select destination.\n")
        elif button_id == "btn-5ft":
            self._add_combat_message("5-foot step taken.\n")
        elif button_id == "btn-withdraw":
            self._add_combat_message("Withdraw action - moving away safely.\n")
        elif button_id == "btn-spell":
            self._add_combat_message("Cast spell - select spell from list.\n")
        elif button_id == "btn-item":
            self._add_combat_message("Use item - select from inventory.\n")
        elif button_id == "btn-special":
            self._add_combat_message("Special actions: Combat Maneuvers, Aid Another, etc.\n")
        elif button_id == "btn-delay":
            self._add_combat_message("Delaying turn...\n")
        elif button_id == "btn-ready":
            self._add_combat_message("Ready action - specify trigger and action.\n")
        elif button_id == "btn-end-turn":
            self._end_turn()
        elif button_id == "btn-end-combat":
            self._end_combat()

    def _handle_attack(self) -> None:
        """Handle an attack action."""
        from ...game.dice import DiceRoller

        roller = DiceRoller()

        # Roll attack
        attack_roll = roller.roll("1d20+5")
        self._add_combat_message(f"\n[bold]Attack Roll:[/bold] {attack_roll.total} ({attack_roll.rolls})\n")

        # Check for hit (assuming AC 16 target)
        target_ac = 16
        if attack_roll.total >= target_ac:
            # Roll damage
            damage_roll = roller.roll("1d8+3")
            self._add_combat_message(f"[green]HIT![/green] Damage: {damage_roll.total}\n")
        else:
            self._add_combat_message("[red]MISS![/red]\n")

    def _end_turn(self) -> None:
        """End the current turn."""
        tracker = self.query_one("#initiative-tracker", InitiativeTracker)
        tracker.next_turn()

        self.current_turn += 1

        # Check for new round
        if self.current_turn >= 6:  # Example: 6 combatants
            self.current_turn = 0
            self.current_round += 1
            round_counter = self.query_one("#round-counter", Static)
            round_counter.update(f"Round {self.current_round}")
            self._add_combat_message(f"\n[bold]--- Round {self.current_round} ---[/bold]\n")

        self._add_combat_message("Next combatant's turn!\n")

    def _end_combat(self) -> None:
        """End the combat encounter."""
        self._add_combat_message("\n[bold green]COMBAT ENDED![/bold green]\n")
        self.app.notify("Combat encounter ended.", title="Combat")
        self.app.pop_screen()

    def _add_combat_message(self, text: str) -> None:
        """Add a message to the combat log."""
        log = self.query_one("#combat-log", RichLog)
        log.write(text)
