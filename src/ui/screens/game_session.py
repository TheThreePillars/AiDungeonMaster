"""Game session screen for AI Dungeon Master."""

import asyncio
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
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

from ..icons import Icons
from ...llm.client import GenerationConfig, Message
from ...llm.prompts import DEFAULT_DM_SYSTEM_PROMPT
from .save_load import SaveGameScreen


class PartyStatusWidget(Static):
    """Display current party status."""

    CSS = """
    PartyStatusWidget {
        height: auto;
        background: $surface-darken-1;
        border: round $primary 50%;
        padding: 1;
        margin-bottom: 1;
    }

    .party-header {
        text-style: bold;
        color: $primary;
        border-bottom: solid $primary 30%;
        padding-bottom: 1;
        margin-bottom: 1;
    }

    .party-member {
        margin-bottom: 1;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the party status display."""
        yield Label(f"{Icons.PARTY}  Party", classes="party-header")
        yield Static("No active party.", id="party-list")

    def update_party(self, characters: list) -> None:
        """Update the party display with current characters."""
        party_list = self.query_one("#party-list", Static)

        if not characters:
            party_list.update("[dim]No active party.[/dim]")
            return

        text = ""
        for char in characters:
            hp_current = char.get("current_hp", 0)
            hp_max = char.get("max_hp", 1)
            hp_pct = (hp_current / hp_max) * 100 if hp_max else 0

            if hp_pct > 50:
                hp_color = "green"
                hp_icon = Icons.HEART
            elif hp_pct > 25:
                hp_color = "yellow"
                hp_icon = Icons.HEART
            else:
                hp_color = "red"
                hp_icon = Icons.SKULL

            name = char.get("name", "Unknown")
            race = char.get("race", "")
            cls = char.get("class", "")
            level = char.get("level", 1)
            ac = char.get("ac", 10)

            # HP bar
            bar_width = 10
            filled = int((hp_pct / 100) * bar_width)
            hp_bar = "█" * filled + "░" * (bar_width - filled)

            text += f"[bold]{Icons.CHARACTER} {name}[/bold]\n"
            text += f"  [dim]{race} {cls} {level}[/dim]\n"
            text += f"  {hp_icon} [{hp_color}]{hp_bar}[/] {hp_current}/{hp_max}\n"
            text += f"  {Icons.SHIELD} AC {ac}\n"

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
        background: $surface-darken-1;
        border-right: solid $primary 30%;
        padding: 1;
    }

    #main-area {
        height: 100%;
        background: $surface;
    }

    #right-sidebar {
        height: 100%;
        background: $surface-darken-1;
        border-left: solid $primary 30%;
        padding: 1;
    }

    #narrative-log {
        height: 1fr;
        background: $surface-darken-2;
        border: none;
        padding: 1;
    }

    #input-area {
        dock: bottom;
        height: 5;
        padding: 1;
        background: $surface-darken-1;
        border-top: solid $primary 30%;
    }

    #action-input {
        width: 100%;
    }

    .sidebar-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
        padding-bottom: 1;
        border-bottom: solid $primary 30%;
    }

    .quick-action {
        width: 100%;
        margin-bottom: 1;
    }

    #dice-result {
        height: auto;
        min-height: 3;
        background: $surface-darken-2;
        border: round $success 50%;
        padding: 1;
        margin-top: 1;
        text-align: center;
    }

    #location-display {
        background: $surface-darken-2;
        border: round $warning 50%;
        padding: 1;
        margin-bottom: 1;
    }

    #ai-status {
        text-align: center;
        margin-bottom: 1;
        padding: 1;
    }

    .dice-row {
        height: 4;
        margin-bottom: 1;
    }

    .dice-row Button {
        min-width: 6;
        margin: 0 1;
    }

    #npc-section {
        margin-top: 1;
    }
    """

    def __init__(self):
        """Initialize the game session screen."""
        super().__init__()
        self._processing = False

    def compose(self) -> ComposeResult:
        """Compose the game session screen."""
        i = Icons

        # Left sidebar - Party and quick actions
        with Container(id="left-sidebar"):
            yield PartyStatusWidget()

            yield Label(f"{i.SWORD}  Quick Actions", classes="sidebar-header")
            yield Button(f"{i.DICE}  Roll d20", id="btn-d20", classes="quick-action")
            yield Button(f"{i.COMPASS}  Look Around", id="btn-look", classes="quick-action")
            yield Button(f"{i.REST}  Rest", id="btn-rest", classes="quick-action")
            yield Button(f"{i.CHEST}  Inventory", id="btn-inventory", classes="quick-action")
            yield Button(f"{i.SWORD}  Combat", id="btn-combat", classes="quick-action", variant="warning")

        # Main area - Narrative and input
        with Container(id="main-area"):
            with TabbedContent():
                with TabPane(f"{i.BOOK} Narrative", id="tab-narrative"):
                    yield RichLog(id="narrative-log", highlight=True, markup=True, wrap=True)
                with TabPane(f"{i.MAP} Map", id="tab-map"):
                    yield Static("Map view - press the button to open full map.", id="map-static")
                    yield Button(f"{i.MAP}  Open World Map", id="btn-map")
                with TabPane(f"{i.QUEST} Quests", id="tab-quests"):
                    yield Static("No active quests.", id="quest-view")
                    yield Button(f"{i.QUEST}  Open Quest Log", id="btn-quest-log")

            with Container(id="input-area"):
                yield Input(
                    placeholder="What do you do? (type /help for commands)",
                    id="action-input",
                )

        # Right sidebar - Location and dice
        with Container(id="right-sidebar"):
            yield Static(id="location-display")
            yield Static("", id="ai-status")

            yield Label(f"{i.DICE}  Dice Roller", classes="sidebar-header")
            with Horizontal(classes="dice-row"):
                yield Button("d4", id="btn-d4")
                yield Button("d6", id="btn-d6")
                yield Button("d8", id="btn-d8")
            with Horizontal(classes="dice-row"):
                yield Button("d10", id="btn-d10")
                yield Button("d12", id="btn-d12")
                yield Button("d20", id="btn-d20-2")
            yield Static(f"[dim]Click to roll[/dim]", id="dice-result")

            with Container(id="npc-section"):
                yield Label(f"{i.NPC}  NPCs Nearby", classes="sidebar-header")
                yield Static("[dim]None visible[/dim]", id="npc-list")
                yield Button(f"{i.NPC}  View All NPCs", id="btn-npcs", classes="quick-action")

    def on_mount(self) -> None:
        """Handle screen mount."""
        i = Icons

        # Update location display
        game_state = self.app.game_state
        self._update_location(game_state.current_location, game_state.location_description)

        # Update party display
        party_widget = self.query_one(PartyStatusWidget)
        party_widget.update_party(game_state.characters)

        # Update AI status
        ai_status = self.query_one("#ai-status", Static)
        if self.app._llm_available:
            ai_status.update(f"[green]{i.SUCCESS} AI Online[/green]")
        else:
            ai_status.update(f"[yellow]{i.WARNING} AI Offline[/yellow]")

        # Show welcome message
        self._add_narrative(
            f"[bold]{i.STAR} Welcome, adventurer! {i.STAR}[/bold]\n\n"
            f"{i.LOCATION} You find yourself in the common room of the Rusty Dragon Inn. "
            "The smell of roasting meat and fresh bread fills the air. "
            "Patrons laugh and chat at nearby tables while a bard strums a lute in the corner.\n\n"
            "[bold cyan]What would you like to do?[/bold cyan]"
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
        self._add_narrative(f"\n[bold cyan]▶ {action}[/bold cyan]\n")

        # Send to AI for response
        self._processing = True
        self.run_worker(self._get_ai_response(action), exclusive=True)

    async def _get_ai_response(self, player_action: str) -> None:
        """Get AI response for player action."""
        i = Icons
        try:
            if not self.app._llm_available or not self.app.llm_client:
                # Offline mode - simple response
                self._add_narrative(
                    f"\n[dim italic]{i.WARNING} AI offline - using basic responses[/dim italic]\n"
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
            self._add_narrative(f"\n[dim italic]{i.TIME} The GM considers your action...[/dim italic]\n")

            # Call LLM
            config = GenerationConfig(temperature=0.8, max_tokens=500)
            result = await self.app.llm_client.achat(messages, config=config)

            # Add response to memory and display
            response = result.content.strip()
            self.app.memory.add_assistant_message(response)

            self._add_narrative(f"\n{response}\n")

        except Exception as e:
            self._add_narrative(f"\n[red]{i.ERROR} Error getting AI response: {e}[/red]\n")
            self._generate_offline_response(player_action)
        finally:
            self._processing = False

    def _generate_offline_response(self, action: str) -> None:
        """Generate a simple offline response."""
        i = Icons
        action_lower = action.lower()

        if "look" in action_lower or "examine" in action_lower:
            self._add_narrative(
                f"\n{i.COMPASS} You take a moment to observe your surroundings. "
                "The tavern is warm and inviting, filled with the sounds of merriment. "
                "Several patrons sit at wooden tables, enjoying their drinks.\n"
            )
        elif "talk" in action_lower or "speak" in action_lower:
            self._add_narrative(
                f"\n{i.CHAT} You approach someone nearby. They look up at you with curiosity. "
                "\"Well met, traveler. What brings you to Sandpoint?\"\n"
            )
        elif "attack" in action_lower or "fight" in action_lower:
            self._add_narrative(
                f"\n{i.WARNING} This is a peaceful establishment. Perhaps save the fighting "
                "for when you encounter actual threats!\n"
            )
        elif "drink" in action_lower or "order" in action_lower:
            self._add_narrative(
                f"\n{i.POTION} You signal the barkeep, who brings you a frothy mug of ale. "
                "\"Three coppers,\" they say with a friendly smile.\n"
            )
        else:
            self._add_narrative(
                f"\n{i.INFO} You attempt to {action}. The results are... uncertain. "
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
        i = Icons

        roller = DiceRoller()
        result = roller.roll(notation)

        # Check for critical or fumble on d20
        is_d20 = "d20" in notation
        is_crit = is_d20 and result.total == 20
        is_fumble = is_d20 and result.total == 1

        dice_result = self.query_one("#dice-result", Static)

        if is_crit:
            dice_result.update(f"[bold green]{i.STAR} CRITICAL! {i.STAR}\n{notation}: {result.total}[/bold green]")
        elif is_fumble:
            dice_result.update(f"[bold red]{i.SKULL} FUMBLE!\n{notation}: {result.total}[/bold red]")
        else:
            dice_result.update(f"[bold]{i.DICE} {notation}[/bold]\nResult: [cyan]{result.total}[/cyan]\n[dim]({result.rolls})[/dim]")

        self._add_narrative(f"\n[dim]{i.DICE} Rolled {notation}: [bold]{result.total}[/bold] ({result.rolls})[/dim]")

    def _handle_command(self, command: str) -> None:
        """Handle slash commands."""
        i = Icons
        parts = command.lower().split()
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        if cmd == "/help":
            self._add_narrative(
                f"\n[bold yellow]{i.HELP} Available Commands:[/bold yellow]\n"
                f"  /roll <dice> - Roll dice (e.g., /roll 2d6+3)\n"
                f"  /look - Look around the current location\n"
                f"  /status - Show party status\n"
                f"  /rest - Take a rest\n"
                f"  /save - Save the game\n"
                f"  /quit - Return to main menu\n"
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
            self._add_narrative(f"\n[red]{i.ERROR} Unknown command: {cmd}[/red]\n")

    def _open_save_game(self) -> None:
        """Open the save game screen."""
        self.app.push_screen(SaveGameScreen(), self._handle_save_result)

    def _handle_save_result(self, saved: bool) -> None:
        """Handle the result from save game screen."""
        i = Icons
        if saved:
            self._add_narrative(f"\n[green]{i.SUCCESS} Game saved successfully![/green]\n")

    def _handle_look(self) -> None:
        """Handle look action - sends to AI if available."""
        if not self._processing:
            self._add_narrative(f"\n[bold cyan]▶ look around[/bold cyan]\n")
            self._processing = True
            self.run_worker(self._get_ai_response("I look around and examine my surroundings carefully."), exclusive=True)

    def _handle_rest(self) -> None:
        """Handle rest action - heal HP and restore spell slots."""
        i = Icons
        self._add_narrative(f"\n[bold]{i.REST} You take a moment to rest...[/bold]\n")

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
                    f"  {i.HEART} {char['name']} recovers [green]+{heal_amount} HP[/green] "
                    f"({char['current_hp']}/{max_hp})\n"
                )

        if not healed_any:
            self._add_narrative(f"  {i.SUCCESS} Everyone is already at full health.\n")

        self._add_narrative(f"\n{i.SUCCESS} You feel refreshed and ready to continue.\n")

        # Update party display
        party_widget = self.query_one(PartyStatusWidget)
        party_widget.update_party(game_state.characters)

        # Save HP changes to database
        self._save_character_hp()

    def _show_status(self) -> None:
        """Show party status in narrative."""
        i = Icons
        game_state = self.app.game_state
        if game_state.characters:
            self._add_narrative(f"\n[bold]{i.PARTY} Party Status:[/bold]\n")
            for char in game_state.characters:
                self._add_narrative(
                    f"  {i.CHARACTER} {char['name']} - {char['race']} {char['class']} {char['level']}\n"
                    f"    {i.HEART} HP: {char['current_hp']}/{char['max_hp']} | {i.SHIELD} AC: {char['ac']}\n"
                )
        else:
            self._add_narrative(f"\n[yellow]{i.WARNING} No party members. Create a character first![/yellow]\n")

    def _update_location(self, name: str, description: str) -> None:
        """Update the location display."""
        i = Icons
        location = self.query_one("#location-display", Static)
        location.update(f"[bold]{i.LOCATION} {name}[/bold]\n\n{description}")

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
