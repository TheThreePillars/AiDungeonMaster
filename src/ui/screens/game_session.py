"""Game session screen for AI Dungeon Master."""

import asyncio
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

from ...llm.client import GenerationConfig, Message
from ...llm.prompts import DEFAULT_DM_SYSTEM_PROMPT
from .save_load import SaveGameScreen


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
    """

    def compose(self) -> ComposeResult:
        """Compose the party status display."""
        yield Label("Party Status", classes="party-header")
        yield Static("No active party.", id="party-list")

    def update_party(self, characters: list) -> None:
        """Update the party display with current characters."""
        party_list = self.query_one("#party-list", Static)

        if not characters:
            party_list.update("No active party.")
            return

        text = ""
        for char in characters:
            hp_current = char.get("current_hp", 0)
            hp_max = char.get("max_hp", 1)
            hp_pct = (hp_current / hp_max) * 100 if hp_max else 0

            if hp_pct > 50:
                hp_style = "[green]"
            elif hp_pct > 25:
                hp_style = "[yellow]"
            else:
                hp_style = "[red]"

            name = char.get("name", "Unknown")
            race = char.get("race", "")
            cls = char.get("class", "")
            level = char.get("level", 1)
            ac = char.get("ac", 10)

            text += f"{name}\n"
            text += f"  {race} {cls} {level}\n"
            text += f"  HP: {hp_style}{hp_current}/{hp_max}[/]\n"
            text += f"  AC: {ac}\n"

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

    #ai-status {
        text-align: center;
        margin-bottom: 1;
    }
    """

    def __init__(self):
        """Initialize the game session screen."""
        super().__init__()
        self._processing = False

    def compose(self) -> ComposeResult:
        """Compose the game session screen."""
        # Left sidebar - Party and quick actions
        with Container(id="left-sidebar"):
            yield PartyStatusWidget()
            yield Label("Quick Actions", classes="sidebar-header")
            yield Button("Roll d20", id="btn-d20", classes="quick-action")
            yield Button("Look Around", id="btn-look", classes="quick-action")
            yield Button("Rest", id="btn-rest", classes="quick-action")
            yield Button("Inventory", id="btn-inventory", classes="quick-action")
            yield Button("Combat Mode", id="btn-combat", classes="quick-action", variant="warning")

        # Main area - Narrative and input
        with Container(id="main-area"):
            with TabbedContent():
                with TabPane("Narrative", id="tab-narrative"):
                    yield RichLog(id="narrative-log", highlight=True, markup=True, wrap=True)
                with TabPane("Map", id="tab-map"):
                    yield Static("Map view coming soon...", id="map-static")
                    yield Button("Open Map", id="btn-map")
                with TabPane("Quest Log", id="tab-quests"):
                    yield Static("No active quests.", id="quest-view")
                    yield Button("Open Quest Log", id="btn-quest-log")

            with Container(id="input-area"):
                yield Input(
                    placeholder="What do you do? (or type /help for commands)",
                    id="action-input",
                )

        # Right sidebar - Location and dice
        with Container(id="right-sidebar"):
            yield Static(id="location-display")
            yield Static("", id="ai-status")
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
            yield Button("View All NPCs", id="btn-npcs")

    def on_mount(self) -> None:
        """Handle screen mount."""
        # Update location display
        game_state = self.app.game_state
        self._update_location(game_state.current_location, game_state.location_description)

        # Update party display
        party_widget = self.query_one(PartyStatusWidget)
        party_widget.update_party(game_state.characters)

        # Update AI status
        ai_status = self.query_one("#ai-status", Static)
        if self.app._llm_available:
            ai_status.update("[green]AI: Online[/green]")
        else:
            ai_status.update("[yellow]AI: Offline[/yellow]")

        # Show welcome message
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

        # Don't process if already processing
        if self._processing:
            return

        # Handle commands
        if action.startswith("/"):
            self._handle_command(action)
            return

        # Add player action to narrative
        self._add_narrative(f"\n[bold cyan]> {action}[/bold cyan]\n")

        # Send to AI for response
        self._processing = True
        self.run_worker(self._get_ai_response(action), exclusive=True)

    async def _get_ai_response(self, player_action: str) -> None:
        """Get AI response for player action."""
        try:
            if not self.app._llm_available or not self.app.llm_client:
                # Offline mode - simple response
                self._add_narrative(
                    "\n[dim italic](AI offline - using basic responses)[/dim italic]\n"
                )
                self._generate_offline_response(player_action)
                return

            # Build context and messages
            game_state = self.app.game_state
            context = game_state.get_context_for_ai()

            # Build system prompt with context
            system_prompt = DEFAULT_DM_SYSTEM_PROMPT + "\n\n" + context

            # Add to memory
            self.app.memory.system_prompt = system_prompt
            self.app.memory.add_user_message(player_action)

            # Get messages for LLM
            messages = self.app.memory.get_messages_for_llm()

            # Show thinking indicator
            self._add_narrative("\n[dim italic]The GM considers your action...[/dim italic]\n")

            # Call LLM
            config = GenerationConfig(temperature=0.8, max_tokens=500)
            result = await self.app.llm_client.achat(messages, config=config)

            # Add response to memory and display
            response = result.content.strip()
            self.app.memory.add_assistant_message(response)

            self._add_narrative(f"\n{response}\n")

        except Exception as e:
            self._add_narrative(f"\n[red]Error getting AI response: {e}[/red]\n")
            self._generate_offline_response(player_action)
        finally:
            self._processing = False

    def _generate_offline_response(self, action: str) -> None:
        """Generate a simple offline response."""
        action_lower = action.lower()

        if "look" in action_lower or "examine" in action_lower:
            self._add_narrative(
                "\nYou take a moment to observe your surroundings. "
                "The tavern is warm and inviting, filled with the sounds of merriment. "
                "Several patrons sit at wooden tables, enjoying their drinks.\n"
            )
        elif "talk" in action_lower or "speak" in action_lower:
            self._add_narrative(
                "\nYou approach someone nearby. They look up at you with curiosity. "
                "\"Well met, traveler. What brings you to Sandpoint?\"\n"
            )
        elif "attack" in action_lower or "fight" in action_lower:
            self._add_narrative(
                "\nThis is a peaceful establishment. Perhaps save the fighting "
                "for when you encounter actual threats!\n"
            )
        elif "drink" in action_lower or "order" in action_lower:
            self._add_narrative(
                "\nYou signal the barkeep, who brings you a frothy mug of ale. "
                "\"Three coppers,\" they say with a friendly smile.\n"
            )
        else:
            self._add_narrative(
                f"\nYou attempt to {action}. The results are... uncertain. "
                "Perhaps try being more specific, or enable the AI for richer responses.\n"
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
        elif button_id == "btn-look":
            self._handle_look()
        elif button_id == "btn-rest":
            self._handle_rest()
        elif button_id == "btn-inventory":
            self.app.push_screen("inventory")
        elif button_id == "btn-combat":
            self.app.push_screen("combat_view")
        elif button_id == "btn-quest-log":
            self.app.push_screen("quest_log")
        elif button_id == "btn-map":
            self.app.push_screen("map_view")
        elif button_id == "btn-npcs":
            self.app.push_screen("npc_screen")

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
        parts = command.lower().split()
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        if cmd == "/help":
            self._add_narrative(
                "\n[bold yellow]Available Commands:[/bold yellow]\n"
                "/roll <dice> - Roll dice (e.g., /roll 2d6+3)\n"
                "/look - Look around the current location\n"
                "/status - Show party status\n"
                "/rest - Take a rest\n"
                "/save - Save the game\n"
                "/quit - Return to main menu\n"
            )
        elif cmd == "/roll" and args:
            self._roll_dice(" ".join(args))
        elif cmd == "/look":
            self._handle_look()
        elif cmd == "/status":
            self._show_status()
        elif cmd == "/rest":
            self._handle_rest()
        elif cmd == "/save":
            self._open_save_game()
        elif cmd == "/quit":
            self.app.pop_screen()
        else:
            self._add_narrative(f"\n[red]Unknown command: {cmd}[/red]\n")

    def _open_save_game(self) -> None:
        """Open the save game screen."""
        self.app.push_screen(SaveGameScreen(), self._handle_save_result)

    def _handle_save_result(self, saved: bool) -> None:
        """Handle the result from save game screen."""
        if saved:
            self._add_narrative("\n[green]Game saved successfully![/green]\n")

    def _handle_look(self) -> None:
        """Handle look action - sends to AI if available."""
        if not self._processing:
            self._add_narrative("\n[bold cyan]> look around[/bold cyan]\n")
            self._processing = True
            self.run_worker(self._get_ai_response("I look around and examine my surroundings carefully."), exclusive=True)

    def _handle_rest(self) -> None:
        """Handle rest action - heal HP and restore spell slots."""
        self._add_narrative("\n[bold]You take a moment to rest...[/bold]\n")

        game_state = self.app.game_state
        healed_any = False

        for char in game_state.characters:
            current_hp = char.get("current_hp", 0)
            max_hp = char.get("max_hp", 1)

            if current_hp < max_hp:
                # Rest heals 1 HP per level (short rest)
                level = char.get("level", 1)
                heal_amount = min(level, max_hp - current_hp)
                char["current_hp"] = current_hp + heal_amount
                healed_any = True
                self._add_narrative(
                    f"  {char['name']} recovers [green]{heal_amount} HP[/green] "
                    f"({char['current_hp']}/{max_hp})\n"
                )

        if not healed_any:
            self._add_narrative("  Everyone is already at full health.\n")

        self._add_narrative("\nYou feel refreshed and ready to continue.\n")

        # Update party display
        party_widget = self.query_one(PartyStatusWidget)
        party_widget.update_party(game_state.characters)

        # Save HP changes to database
        self._save_character_hp()

    def _show_status(self) -> None:
        """Show party status in narrative."""
        game_state = self.app.game_state
        if game_state.characters:
            self._add_narrative("\n[bold]Party Status:[/bold]\n")
            for char in game_state.characters:
                self._add_narrative(
                    f"  {char['name']} - {char['race']} {char['class']} {char['level']}\n"
                    f"    HP: {char['current_hp']}/{char['max_hp']} | AC: {char['ac']}\n"
                )
        else:
            self._add_narrative("\n[yellow]No party members. Create a character first![/yellow]\n")

    def _update_location(self, name: str, description: str) -> None:
        """Update the location display."""
        location = self.query_one("#location-display", Static)
        location.update(f"[bold]{name}[/bold]\n\n{description}")

    def _add_narrative(self, text: str) -> None:
        """Add text to the narrative log."""
        log = self.query_one("#narrative-log", RichLog)
        log.write(text)

    def _save_character_hp(self) -> None:
        """Save character HP changes to database."""
        from ...database.session import session_scope
        from ...database.models import Character

        try:
            with session_scope() as session:
                for char in self.app.game_state.characters:
                    char_id = char.get("id")
                    if char_id:
                        db_char = session.query(Character).filter_by(id=char_id).first()
                        if db_char:
                            db_char.current_hp = char.get("current_hp", db_char.current_hp)
        except Exception:
            pass  # Silently fail on save errors
