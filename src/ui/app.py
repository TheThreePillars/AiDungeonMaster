"""Main Textual application for AI Dungeon Master."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from ..config import get_config
from ..llm.client import OllamaClient
from ..llm.memory import ConversationMemory
from ..database.session import get_session
from ..game.combat import CombatTracker
from ..database.models import Party, Character, Campaign
from .screens.main_menu import MainMenuScreen
from .screens.character_creation import CharacterCreationScreen
from .screens.game_session import GameSessionScreen
from .screens.combat_view import CombatViewScreen
from .screens.party_manager import PartyManagerScreen
from .screens.inventory_screen import InventoryScreen
from .screens.quest_log import QuestLogScreen
from .screens.map_view import MapViewScreen
from .screens.npc_screen import NPCScreen
from .screens.settings_screen import SettingsScreen
from .screens.bestiary_screen import BestiaryScreen


class GameState:
    """Manages the current game state."""

    def __init__(self):
        """Initialize game state."""
        self.party_id: int | None = None
        self.campaign_id: int | None = None
        self.current_location: str = "The Rusty Dragon Inn"
        self.location_description: str = "A warm and inviting tavern in the town of Sandpoint."
        self.in_combat: bool = False
        self.time_of_day: str = "morning"
        self.characters: list[dict] = []

    def load_party(self, party_id: int) -> bool:
        """Load a party from the database."""
        with get_session() as session:
            party = session.query(Party).filter_by(id=party_id).first()
            if party:
                self.party_id = party_id
                self.characters = []
                for char in party.characters:
                    self.characters.append({
                        "id": char.id,
                        "name": char.name,
                        "race": char.race,
                        "class": char.character_class,
                        "level": char.level,
                        "current_hp": char.current_hp,
                        "max_hp": char.max_hp,
                        "ac": char.armor_class,
                    })
                return True
        return False

    def get_party_summary(self) -> str:
        """Get a summary of the current party."""
        if not self.characters:
            return "No party members."
        lines = []
        for char in self.characters:
            lines.append(f"- {char['name']} ({char['race']} {char['class']} {char['level']}): HP {char['current_hp']}/{char['max_hp']}")
        return "\n".join(lines)

    def get_context_for_ai(self) -> str:
        """Build context string for AI prompts."""
        context = f"""CURRENT SITUATION:
Location: {self.current_location}
{self.location_description}
Time: {self.time_of_day}
In Combat: {"Yes" if self.in_combat else "No"}

PARTY:
{self.get_party_summary()}
"""
        return context


class AIDungeonMasterApp(App):
    """The main AI Dungeon Master application."""

    TITLE = "AI Dungeon Master"
    SUB_TITLE = "Pathfinder 1e"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "back", "Back", show=True),
        Binding("f1", "help", "Help", show=True),
        Binding("ctrl+s", "save", "Save", show=False),
    ]

    SCREENS = {
        "main_menu": MainMenuScreen,
        "character_creation": CharacterCreationScreen,
        "game_session": GameSessionScreen,
        "combat_view": CombatViewScreen,
        "party_manager": PartyManagerScreen,
        "inventory": InventoryScreen,
        "quest_log": QuestLogScreen,
        "map_view": MapViewScreen,
        "npc_screen": NPCScreen,
        "settings": SettingsScreen,
        "bestiary": BestiaryScreen,
    }

    def __init__(self):
        """Initialize the application."""
        super().__init__()
        self.game_state = GameState()
        self.memory = ConversationMemory()
        self.llm_client: OllamaClient | None = None
        self._llm_available = False
        self.combat_tracker: CombatTracker | None = None

    def on_mount(self) -> None:
        """Handle app mount - initialize LLM and show main menu."""
        self._init_llm()
        self.push_screen("main_menu")

    def _init_llm(self) -> None:
        """Initialize the LLM client."""
        try:
            config = get_config()
            self.llm_client = OllamaClient(
                model=config.llm.model,
                base_url=config.llm.base_url,
            )
            self._llm_available = self.llm_client.is_available()
            if self._llm_available:
                self.notify("AI connected!", title="Status", timeout=2)
            else:
                self.notify("AI model not found. Running in offline mode.", title="Warning", timeout=3)
        except Exception as e:
            self.notify(f"Could not connect to Ollama: {e}", title="Warning", timeout=3)
            self._llm_available = False

    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount - show main menu."""
        self.push_screen("main_menu")

    def action_back(self) -> None:
        """Go back to previous screen."""
        if len(self.screen_stack) > 1:
            self.pop_screen()

    def action_help(self) -> None:
        """Show help screen."""
        self.notify(
            "AI Dungeon Master - Pathfinder 1e\n"
            "Use arrow keys to navigate, Enter to select.\n"
            "Press ESC to go back, Q to quit.",
            title="Help",
            timeout=5,
        )

    def action_save(self) -> None:
        """Save current game state."""
        if self.game_state.party_id or self.game_state.campaign_id:
            self.notify("Game saved!", title="Save")
        else:
            self.notify("Nothing to save.", title="Save")


def run_app() -> None:
    """Run the AI Dungeon Master application."""
    app = AIDungeonMasterApp()
    app.run()


if __name__ == "__main__":
    run_app()
