"""Game session screen for AI Dungeon Master."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Input,
    Label,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)


class PartyStatusWidget(Static):
    """Display current party status."""

    CSS = """
    PartyStatusWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }

    .party-header {
        text-style: bold;
        color: $primary;
    }

    .character-row {
        height: 1;
    }

    .hp-good {
        color: $success;
    }

    .hp-warning {
        color: $warning;
    }

    .hp-danger {
        color: $error;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the party status display."""
        yield Label("Party Status", classes="party-header")
        yield Static("No active party. Create characters first.", id="party-list")

    def update_party(self, characters: list) -> None:
        """Update the party display with current characters."""
        party_list = self.query_one("#party-list", Static)

        if not characters:
            party_list.update("No active party. Create characters first.")
            return

        text = ""
        for char in characters:
            hp_pct = (char.current_hp / char.max_hp) * 100 if char.max_hp else 0
            if hp_pct > 50:
                hp_style = "[green]"
            elif hp_pct > 25:
                hp_style = "[yellow]"
            else:
                hp_style = "[red]"

            text += f"{char.name} ({char.race} {char.class_name} {char.level})\n"
            text += f"  HP: {hp_style}{char.current_hp}/{char.max_hp}[/] | AC: {char.ac}\n"

        party_list.update(text.strip())


class GameSessionScreen(Screen):
    """The main game session screen."""

    CSS = """
    GameSessionScreen {
        layout: grid;
        grid-size: 3;
        grid-columns: 1fr 2fr 1fr;
    }

    #left-sidebar {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    #main-area {
        height: 100%;
        border: solid $secondary;
    }

    #right-sidebar {
        height: 100%;
        border: solid $accent;
        padding: 1;
    }

    #narrative-log {
        height: 1fr;
        border: none;
    }

    #input-area {
        dock: bottom;
        height: 5;
        padding: 1;
    }

    #action-input {
        width: 100%;
    }

    .sidebar-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    .quick-action {
        width: 100%;
        margin-bottom: 1;
    }

    #dice-result {
        height: 3;
        border: solid $success;
        padding: 0 1;
        margin-top: 1;
    }

    #location-display {
        border: solid $warning;
        padding: 1;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the game session screen."""
        # Left sidebar - Party and quick actions
        with Container(id="left-sidebar"):
            yield PartyStatusWidget()
            yield Label("Quick Actions", classes="sidebar-header")
            yield Button("Roll d20", id="btn-d20", classes="quick-action")
            yield Button("Attack", id="btn-attack", classes="quick-action")
            yield Button("Skill Check", id="btn-skill", classes="quick-action")
            yield Button("Rest", id="btn-rest", classes="quick-action")
            yield Button("Inventory", id="btn-inventory", classes="quick-action")
            yield Button("Combat Mode", id="btn-combat", classes="quick-action", variant="warning")

        # Main area - Narrative and input
        with Container(id="main-area"):
            with TabbedContent():
                with TabPane("Narrative", id="tab-narrative"):
                    yield RichLog(id="narrative-log", highlight=True, markup=True)
                with TabPane("Map", id="tab-map"):
                    yield Static("Map view coming soon...", id="map-view")
                with TabPane("Quest Log", id="tab-quests"):
                    yield Static("No active quests.", id="quest-view")

            with Container(id="input-area"):
                yield Input(
                    placeholder="What do you do? (or type /help for commands)",
                    id="action-input",
                )

        # Right sidebar - Location and dice
        with Container(id="right-sidebar"):
            yield Static(id="location-display")
            yield Label("Dice", classes="sidebar-header")
            with Horizontal():
                yield Button("d4", id="btn-d4")
                yield Button("d6", id="btn-d6")
                yield Button("d8", id="btn-d8")
            with Horizontal():
                yield Button("d10", id="btn-d10")
                yield Button("d12", id="btn-d12")
                yield Button("d20", id="btn-d20-2")
            yield Static("", id="dice-result")
            yield Label("NPCs Present", classes="sidebar-header")
            yield Static("None nearby", id="npc-list")

    def on_mount(self) -> None:
        """Handle screen mount."""
        self._update_location("The Rusty Dragon Inn", "A warm and inviting tavern in the town of Sandpoint.")
        self._add_narrative(
            "[bold]Welcome, adventurer![/bold]\n\n"
            "You find yourself in the common room of the Rusty Dragon Inn. "
            "The smell of roasting meat and fresh bread fills the air. "
            "Patrons laugh and chat at nearby tables while a bard strums a lute in the corner.\n\n"
            "What would you like to do?"
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle player input."""
        action = event.value.strip()
        if not action:
            return

        event.input.clear()

        # Handle commands
        if action.startswith("/"):
            self._handle_command(action)
            return

        # Add player action to narrative
        self._add_narrative(f"\n[bold cyan]> {action}[/bold cyan]\n")

        # TODO: Send to AI for response
        self._add_narrative(
            "\n[italic]The GM considers your action...[/italic]\n"
            "(AI response would appear here)\n"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-d20" or button_id == "btn-d20-2":
            self._roll_dice("1d20")
        elif button_id == "btn-d4":
            self._roll_dice("1d4")
        elif button_id == "btn-d6":
            self._roll_dice("1d6")
        elif button_id == "btn-d8":
            self._roll_dice("1d8")
        elif button_id == "btn-d10":
            self._roll_dice("1d10")
        elif button_id == "btn-d12":
            self._roll_dice("1d12")
        elif button_id == "btn-attack":
            self.app.notify("Select a target for your attack.", title="Attack")
        elif button_id == "btn-skill":
            self.app.notify("Skill check system coming soon!", title="Skill Check")
        elif button_id == "btn-rest":
            self._handle_rest()
        elif button_id == "btn-inventory":
            self.app.notify("Inventory system coming soon!", title="Inventory")
        elif button_id == "btn-combat":
            self.app.push_screen("combat_view")

    def _roll_dice(self, notation: str) -> None:
        """Roll dice and display result."""
        from ...game.dice import DiceRoller

        roller = DiceRoller()
        result = roller.roll(notation)

        dice_result = self.query_one("#dice-result", Static)
        dice_result.update(f"[bold]{notation}:[/bold] {result.total}\n{result.rolls}")

        self._add_narrative(f"\n[dim]Rolled {notation}: [bold]{result.total}[/bold] ({result.rolls})[/dim]")

    def _handle_command(self, command: str) -> None:
        """Handle slash commands."""
        cmd = command.lower().split()[0]
        args = command.split()[1:]

        if cmd == "/help":
            self._add_narrative(
                "\n[bold yellow]Available Commands:[/bold yellow]\n"
                "/roll <dice> - Roll dice (e.g., /roll 2d6+3)\n"
                "/look - Look around the current location\n"
                "/talk <npc> - Talk to an NPC\n"
                "/inventory - Check your inventory\n"
                "/rest - Take a rest\n"
                "/combat - Enter combat mode\n"
                "/save - Save the game\n"
                "/quit - Return to main menu\n"
            )
        elif cmd == "/roll" and args:
            self._roll_dice(" ".join(args))
        elif cmd == "/look":
            self._add_narrative("\n[italic]You look around...[/italic]\n")
        elif cmd == "/quit":
            self.app.pop_screen()
        else:
            self._add_narrative(f"\n[red]Unknown command: {cmd}[/red]\n")

    def _handle_rest(self) -> None:
        """Handle rest action."""
        self._add_narrative(
            "\n[bold]You take a moment to rest...[/bold]\n"
            "Time passes as you recover your strength.\n"
        )

    def _update_location(self, name: str, description: str) -> None:
        """Update the location display."""
        location = self.query_one("#location-display", Static)
        location.update(f"[bold]{name}[/bold]\n\n{description}")

    def _add_narrative(self, text: str) -> None:
        """Add text to the narrative log."""
        log = self.query_one("#narrative-log", RichLog)
        log.write(text)
