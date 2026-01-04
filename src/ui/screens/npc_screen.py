"""NPC interaction screen for managing non-player characters."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Label, Select, Static

from ...database.session import session_scope
from ...database.models import NPC


# Pre-defined NPCs for Sandpoint
DEFAULT_NPCS = [
    {
        "name": "Ameiko Kaijitsu",
        "description": "A beautiful Tian woman with an easy smile and confident demeanor.",
        "personality": "Friendly, adventurous, and charismatic. Former adventurer turned innkeeper.",
        "role": "innkeeper",
        "disposition": "friendly",
        "location": "The Rusty Dragon Inn",
        "voice_notes": "Speaks with warmth but has a sharp wit.",
    },
    {
        "name": "Father Zantus",
        "description": "A kind-looking man in simple robes, with gentle eyes.",
        "personality": "Patient, devout, and helpful. Always willing to offer guidance.",
        "role": "priest",
        "disposition": "friendly",
        "location": "Sandpoint Cathedral",
        "voice_notes": "Soft-spoken with a calming presence.",
    },
    {
        "name": "Sheriff Hemlock",
        "description": "A stern Shoanti man with weathered features and watchful eyes.",
        "personality": "Serious, dedicated, and protective. Takes his duty very seriously.",
        "role": "guard",
        "disposition": "neutral",
        "location": "Sandpoint Garrison",
        "voice_notes": "Gruff but fair. Respects action over words.",
    },
    {
        "name": "Mayor Deverin",
        "description": "A well-dressed woman with a warm smile and keen political sense.",
        "personality": "Diplomatic, caring, and shrewd. Genuinely cares for Sandpoint.",
        "role": "noble",
        "disposition": "friendly",
        "location": "Sandpoint Town Square",
        "voice_notes": "Professional but personable. Excellent at reading people.",
    },
    {
        "name": "Ven Vinder",
        "description": "A large, barrel-chested man with a thick beard.",
        "personality": "Protective of his family, especially his daughters. Quick to anger.",
        "role": "merchant",
        "disposition": "neutral",
        "location": "Sandpoint General Store",
        "voice_notes": "Loud and boisterous. Suspicious of strangers near his daughters.",
    },
]


class NPCScreen(Screen):
    """Screen for viewing and interacting with NPCs."""

    CSS = """
    NPCScreen {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 2fr;
    }

    #npc-list-panel {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    #npc-detail-panel {
        height: 100%;
        border: solid $secondary;
        padding: 1;
    }

    .section-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #npc-table {
        height: 1fr;
    }

    #location-filter {
        margin-bottom: 1;
    }

    #button-row {
        dock: bottom;
        height: 3;
    }

    Button {
        margin-right: 1;
    }

    #npc-name {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #npc-portrait {
        height: 5;
        border: solid $accent;
        padding: 1;
        margin-bottom: 1;
    }

    #npc-info {
        height: auto;
        margin-bottom: 1;
    }

    #npc-personality {
        border: solid $warning;
        padding: 1;
        margin-bottom: 1;
    }

    #interaction-buttons {
        margin-bottom: 1;
    }

    #conversation-area {
        height: 1fr;
        border: solid $success;
        padding: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self._npcs: dict[str, dict] = {}
        self.selected_npc_id = None
        self.filter_location = "all"

    def compose(self) -> ComposeResult:
        with Container(id="npc-list-panel"):
            yield Label("NPCs", classes="section-header")

            yield Select(
                [
                    ("All Locations", "all"),
                    ("The Rusty Dragon Inn", "The Rusty Dragon Inn"),
                    ("Sandpoint Cathedral", "Sandpoint Cathedral"),
                    ("Sandpoint Garrison", "Sandpoint Garrison"),
                    ("Sandpoint Town Square", "Sandpoint Town Square"),
                    ("Sandpoint General Store", "Sandpoint General Store"),
                ],
                id="location-filter",
                value="all",
            )

            yield DataTable(id="npc-table")

            with Horizontal(id="button-row"):
                yield Button("Initialize NPCs", id="btn-init", variant="success")
                yield Button("Back", id="btn-back")

        with Container(id="npc-detail-panel"):
            yield Label("NPC Details", classes="section-header")

            with VerticalScroll():
                yield Static("Select an NPC.", id="npc-name")

                yield Static(self._get_default_portrait(), id="npc-portrait")

                yield Static("", id="npc-info")

                with Container(id="npc-personality"):
                    yield Label("Personality & Voice", classes="section-header")
                    yield Static("", id="personality-text")

                with Horizontal(id="interaction-buttons"):
                    yield Button("Talk", id="btn-talk", variant="primary")
                    yield Button("Trade", id="btn-trade")
                    yield Button("Improve Relations", id="btn-relations", variant="success")

                with Container(id="conversation-area"):
                    yield Label("Recent Interaction", classes="section-header")
                    yield Static("No recent conversations.", id="conversation-log")

    def _get_default_portrait(self) -> str:
        """Get default ASCII portrait."""
        return """
   .-"-.
  /     \\
 |  O O  |
 |   >   |
  \\ --- /
   '---'
"""

    def on_mount(self) -> None:
        """Set up the NPC table."""
        table = self.query_one("#npc-table", DataTable)
        table.add_columns("Name", "Role", "Attitude")
        table.cursor_type = "row"

        self._load_npcs()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle filter change."""
        if event.select.id == "location-filter":
            self.filter_location = str(event.value)
            self._load_npcs()

    def _load_npcs(self) -> None:
        """Load NPCs from database."""
        table = self.query_one("#npc-table", DataTable)
        table.clear()
        self._npcs.clear()

        try:
            with session_scope() as session:
                query = session.query(NPC)

                if self.filter_location != "all":
                    query = query.filter_by(location=self.filter_location)

                # Filter by campaign if set
                game_state = self.app.game_state
                if game_state.campaign_id:
                    query = query.filter_by(campaign_id=game_state.campaign_id)

                npcs = query.all()

                for npc in npcs:
                    # Disposition display
                    disp_display = {
                        "friendly": "[green]Friendly[/green]",
                        "neutral": "[yellow]Neutral[/yellow]",
                        "hostile": "[red]Hostile[/red]",
                    }.get(npc.disposition, npc.disposition)

                    row_key = table.add_row(
                        npc.name,
                        npc.role or "unknown",
                        disp_display,
                    )

                    self._npcs[str(row_key)] = {
                        "id": npc.id,
                        "name": npc.name,
                        "description": npc.description or "",
                        "personality": npc.personality or "",
                        "voice_notes": npc.voice_notes or "",
                        "role": npc.role or "unknown",
                        "disposition": npc.disposition or "neutral",
                        "location": npc.location or "Unknown",
                        "trust_level": npc.trust_level or 0,
                        "relationship": npc.relationship_to_party or "",
                        "secrets": npc.secrets or [],
                        "quest_hooks": npc.quest_hooks or [],
                    }

                if not npcs:
                    name_display = self.query_one("#npc-name", Static)
                    name_display.update("No NPCs found. Click 'Initialize NPCs' to populate.")

        except Exception as e:
            self.app.notify(f"Error loading NPCs: {e}", title="Error", severity="error")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle NPC selection."""
        row_key = event.row_key
        if row_key is not None:
            npc_data = self._npcs.get(str(row_key))
            if npc_data:
                self.selected_npc_id = npc_data["id"]
                self._show_npc_details(npc_data)

    def _show_npc_details(self, npc: dict) -> None:
        """Show details for an NPC."""
        # Name
        name_display = self.query_one("#npc-name", Static)
        disp_color = {
            "friendly": "green",
            "neutral": "yellow",
            "hostile": "red",
        }.get(npc["disposition"], "white")
        name_display.update(
            f"[bold]{npc['name']}[/bold] [{disp_color}]({npc['disposition']})[/{disp_color}]"
        )

        # Info
        info = self.query_one("#npc-info", Static)
        info.update(
            f"[bold]Role:[/bold] {npc['role'].title()}\n"
            f"[bold]Location:[/bold] {npc['location']}\n"
            f"[bold]Trust Level:[/bold] {npc['trust_level']}\n\n"
            f"{npc['description']}"
        )

        # Personality
        personality = self.query_one("#personality-text", Static)
        personality.update(
            f"{npc['personality']}\n\n"
            f"[bold]Voice Notes:[/bold] {npc['voice_notes']}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-back":
            self.app.pop_screen()
        elif button_id == "btn-init":
            self._initialize_npcs()
        elif button_id == "btn-talk":
            self._talk_to_npc()
        elif button_id == "btn-trade":
            self._trade_with_npc()
        elif button_id == "btn-relations":
            self._improve_relations()

    def _initialize_npcs(self) -> None:
        """Initialize default NPCs in database."""
        try:
            with session_scope() as session:
                # Check if NPCs already exist
                existing = session.query(NPC).count()
                if existing > 0:
                    self.app.notify("NPCs already initialized.", title="NPCs")
                    return

                # Create default NPCs
                for npc_data in DEFAULT_NPCS:
                    npc = NPC(
                        campaign_id=self.app.game_state.campaign_id or 1,
                        name=npc_data["name"],
                        description=npc_data["description"],
                        personality=npc_data["personality"],
                        voice_notes=npc_data["voice_notes"],
                        role=npc_data["role"],
                        disposition=npc_data["disposition"],
                        location=npc_data["location"],
                        trust_level=0,
                    )
                    session.add(npc)

                self.app.notify(f"Created {len(DEFAULT_NPCS)} NPCs!", title="NPCs")

            self._load_npcs()

        except Exception as e:
            self.app.notify(f"Error initializing NPCs: {e}", title="Error", severity="error")

    def _talk_to_npc(self) -> None:
        """Initiate conversation with selected NPC."""
        if not self.selected_npc_id:
            self.app.notify("Select an NPC first.", title="Talk")
            return

        # Get NPC data
        npc_data = None
        for data in self._npcs.values():
            if data["id"] == self.selected_npc_id:
                npc_data = data
                break

        if not npc_data:
            return

        # Simple conversation simulation
        conversation = self.query_one("#conversation-log", Static)
        greeting = self._get_greeting(npc_data)
        conversation.update(
            f"[bold]{npc_data['name']}:[/bold]\n\n\"{greeting}\""
        )

        self.app.notify(f"Speaking with {npc_data['name']}...", title="Talk")

    def _get_greeting(self, npc: dict) -> str:
        """Get appropriate greeting based on disposition."""
        greetings = {
            "friendly": [
                "Ah, welcome friend! It's good to see you!",
                "Hello there! How can I help you today?",
                "Greetings, adventurer! What brings you my way?",
            ],
            "neutral": [
                "Yes? What do you need?",
                "Can I help you with something?",
                "Hmm? What is it?",
            ],
            "hostile": [
                "What do you want?",
                "Make it quick. I don't have time for this.",
                "You again? This better be important.",
            ],
        }

        import random
        disposition = npc.get("disposition", "neutral")
        return random.choice(greetings.get(disposition, greetings["neutral"]))

    def _trade_with_npc(self) -> None:
        """Open trade with selected NPC."""
        if not self.selected_npc_id:
            self.app.notify("Select an NPC first.", title="Trade")
            return

        # Get NPC data
        npc_data = None
        for data in self._npcs.values():
            if data["id"] == self.selected_npc_id:
                npc_data = data
                break

        if not npc_data:
            return

        if npc_data["role"] != "merchant":
            self.app.notify(f"{npc_data['name']} doesn't trade.", title="Trade")
            return

        self.app.notify(f"Trading with {npc_data['name']}...", title="Trade")
        # Could open inventory/shop screen here

    def _improve_relations(self) -> None:
        """Attempt to improve relations with NPC."""
        if not self.selected_npc_id:
            self.app.notify("Select an NPC first.", title="Relations")
            return

        try:
            with session_scope() as session:
                npc = session.query(NPC).filter_by(id=self.selected_npc_id).first()
                if npc:
                    old_trust = npc.trust_level or 0
                    new_trust = min(100, old_trust + 10)
                    npc.trust_level = new_trust

                    # Update disposition based on trust
                    if new_trust >= 50 and npc.disposition != "hostile":
                        npc.disposition = "friendly"
                    elif new_trust >= 0:
                        npc.disposition = "neutral"

                    self.app.notify(
                        f"Trust with {npc.name}: {old_trust} -> {new_trust}",
                        title="Relations"
                    )

            self._load_npcs()

        except Exception as e:
            self.app.notify(f"Error: {e}", title="Error", severity="error")
