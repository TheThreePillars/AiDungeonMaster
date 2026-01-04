"""NPC generation and management for campaigns."""

import json
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..llm.client import GenerationConfig, OllamaClient


class NPCDisposition(Enum):
    """NPC disposition toward the party."""

    HOSTILE = "hostile"
    UNFRIENDLY = "unfriendly"
    INDIFFERENT = "indifferent"
    FRIENDLY = "friendly"
    HELPFUL = "helpful"


class NPCRole(Enum):
    """Common NPC roles."""

    QUEST_GIVER = "quest_giver"
    MERCHANT = "merchant"
    ALLY = "ally"
    ENEMY = "enemy"
    NEUTRAL = "neutral"
    INFORMANT = "informant"
    AUTHORITY = "authority"
    COMMONER = "commoner"


@dataclass
class NPCPersonality:
    """NPC personality traits."""

    trait1: str = ""
    trait2: str = ""
    ideal: str = ""
    bond: str = ""
    flaw: str = ""
    mannerism: str = ""
    voice_notes: str = ""


@dataclass
class NPCStats:
    """Combat stats for an NPC (if needed)."""

    cr: float = 0.5
    hp: int = 10
    ac: int = 10
    attack_bonus: int = 0
    damage: str = "1d4"
    special_abilities: list[str] = field(default_factory=list)


@dataclass
class NPC:
    """A non-player character."""

    name: str
    race: str = "Human"
    gender: str = ""
    age: str = ""  # young, adult, middle-aged, elderly
    occupation: str = ""
    description: str = ""
    role: NPCRole = NPCRole.NEUTRAL
    disposition: NPCDisposition = NPCDisposition.INDIFFERENT

    # Location
    location: str = ""
    faction: str = ""

    # Personality
    personality: NPCPersonality = field(default_factory=NPCPersonality)

    # Relationship with party
    relationship: str = ""
    trust_level: int = 0  # -100 to 100
    met_before: bool = False
    interactions: list[str] = field(default_factory=list)

    # Knowledge and secrets
    knowledge: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    rumors: list[str] = field(default_factory=list)

    # Quest hooks this NPC can provide
    quest_hooks: list[str] = field(default_factory=list)

    # Combat stats (optional)
    is_combatant: bool = False
    stats: NPCStats | None = None
    is_alive: bool = True

    # Notes
    notes: str = ""

    def modify_trust(self, amount: int) -> None:
        """Modify trust level with the party."""
        self.trust_level = max(-100, min(100, self.trust_level + amount))
        self._update_disposition()

    def _update_disposition(self) -> None:
        """Update disposition based on trust level."""
        if self.trust_level <= -50:
            self.disposition = NPCDisposition.HOSTILE
        elif self.trust_level <= -20:
            self.disposition = NPCDisposition.UNFRIENDLY
        elif self.trust_level <= 20:
            self.disposition = NPCDisposition.INDIFFERENT
        elif self.trust_level <= 50:
            self.disposition = NPCDisposition.FRIENDLY
        else:
            self.disposition = NPCDisposition.HELPFUL

    def add_interaction(self, description: str) -> None:
        """Record an interaction with the party."""
        self.interactions.append(description)
        self.met_before = True

    def get_greeting(self) -> str:
        """Get an appropriate greeting based on disposition."""
        greetings = {
            NPCDisposition.HOSTILE: "What do YOU want?",
            NPCDisposition.UNFRIENDLY: "*eyes you suspiciously* Yes?",
            NPCDisposition.INDIFFERENT: "Can I help you?",
            NPCDisposition.FRIENDLY: "Ah, good to see you! What can I do for you?",
            NPCDisposition.HELPFUL: "My friends! How wonderful! What do you need?",
        }
        return greetings.get(self.disposition, "Hello.")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "race": self.race,
            "gender": self.gender,
            "age": self.age,
            "occupation": self.occupation,
            "description": self.description,
            "role": self.role.value,
            "disposition": self.disposition.value,
            "location": self.location,
            "faction": self.faction,
            "personality": {
                "trait1": self.personality.trait1,
                "trait2": self.personality.trait2,
                "ideal": self.personality.ideal,
                "bond": self.personality.bond,
                "flaw": self.personality.flaw,
                "mannerism": self.personality.mannerism,
                "voice_notes": self.personality.voice_notes,
            },
            "trust_level": self.trust_level,
            "met_before": self.met_before,
            "interactions": self.interactions,
            "knowledge": self.knowledge,
            "secrets": self.secrets,
            "quest_hooks": self.quest_hooks,
            "is_combatant": self.is_combatant,
            "is_alive": self.is_alive,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NPC":
        """Create NPC from dictionary."""
        personality = NPCPersonality(
            trait1=data.get("personality", {}).get("trait1", ""),
            trait2=data.get("personality", {}).get("trait2", ""),
            ideal=data.get("personality", {}).get("ideal", ""),
            bond=data.get("personality", {}).get("bond", ""),
            flaw=data.get("personality", {}).get("flaw", ""),
            mannerism=data.get("personality", {}).get("mannerism", ""),
            voice_notes=data.get("personality", {}).get("voice_notes", ""),
        )

        return cls(
            name=data.get("name", "Unknown"),
            race=data.get("race", "Human"),
            gender=data.get("gender", ""),
            age=data.get("age", ""),
            occupation=data.get("occupation", ""),
            description=data.get("description", ""),
            role=NPCRole(data.get("role", "neutral")),
            disposition=NPCDisposition(data.get("disposition", "indifferent")),
            location=data.get("location", ""),
            faction=data.get("faction", ""),
            personality=personality,
            trust_level=data.get("trust_level", 0),
            met_before=data.get("met_before", False),
            interactions=data.get("interactions", []),
            knowledge=data.get("knowledge", []),
            secrets=data.get("secrets", []),
            quest_hooks=data.get("quest_hooks", []),
            is_combatant=data.get("is_combatant", False),
            is_alive=data.get("is_alive", True),
            notes=data.get("notes", ""),
        )


class NPCManager:
    """Manages NPCs for a campaign."""

    # Random generation tables
    MALE_NAMES = [
        "Aldric", "Bram", "Cedric", "Dorian", "Edmund", "Felix", "Gareth",
        "Henrik", "Ivan", "Jasper", "Klaus", "Lucius", "Magnus", "Nolan",
        "Osric", "Pavel", "Quinn", "Roland", "Stefan", "Theron", "Ulric",
        "Viktor", "Wilhelm", "Xavier", "Yorick", "Zephyr",
    ]

    FEMALE_NAMES = [
        "Adriana", "Beatrix", "Celeste", "Diana", "Elena", "Freya", "Gwendolyn",
        "Helena", "Iris", "Juliana", "Katarina", "Lydia", "Miranda", "Nadia",
        "Ophelia", "Petra", "Rosalind", "Seraphina", "Tatiana", "Ursula",
        "Vivienne", "Willow", "Xena", "Yolanda", "Zara",
    ]

    OCCUPATIONS = [
        "blacksmith", "innkeeper", "merchant", "guard", "farmer", "priest",
        "scholar", "noble", "beggar", "thief", "hunter", "herbalist",
        "baker", "tailor", "jeweler", "scribe", "sailor", "soldier",
        "entertainer", "healer", "wizard's apprentice", "stable hand",
    ]

    TRAITS = [
        "friendly", "suspicious", "greedy", "generous", "cowardly", "brave",
        "honest", "deceitful", "calm", "nervous", "proud", "humble",
        "curious", "indifferent", "ambitious", "content", "witty", "slow",
        "kind", "cruel", "patient", "impatient", "wise", "foolish",
    ]

    MANNERISMS = [
        "speaks slowly and deliberately",
        "gestures wildly when talking",
        "avoids eye contact",
        "laughs nervously",
        "strokes their chin thoughtfully",
        "taps fingers impatiently",
        "speaks in a whisper",
        "speaks too loudly",
        "uses big words incorrectly",
        "peppers speech with foreign words",
        "constantly looks over their shoulder",
        "fidgets with jewelry or clothing",
    ]

    def __init__(self, llm_client: OllamaClient | None = None):
        """Initialize NPC manager.

        Args:
            llm_client: Optional LLM client for AI generation
        """
        self.llm = llm_client
        self.npcs: dict[str, NPC] = {}

    def add_npc(self, npc: NPC) -> None:
        """Add an NPC to the manager.

        Args:
            npc: NPC to add
        """
        self.npcs[npc.name.lower()] = npc

    def get_npc(self, name: str) -> NPC | None:
        """Get an NPC by name.

        Args:
            name: NPC name

        Returns:
            NPC or None
        """
        return self.npcs.get(name.lower())

    def remove_npc(self, name: str) -> bool:
        """Remove an NPC.

        Args:
            name: NPC name

        Returns:
            True if removed
        """
        if name.lower() in self.npcs:
            del self.npcs[name.lower()]
            return True
        return False

    def get_npcs_at_location(self, location: str) -> list[NPC]:
        """Get all NPCs at a location.

        Args:
            location: Location name

        Returns:
            List of NPCs at that location
        """
        return [
            npc for npc in self.npcs.values()
            if npc.location.lower() == location.lower() and npc.is_alive
        ]

    def get_npcs_by_faction(self, faction: str) -> list[NPC]:
        """Get all NPCs in a faction.

        Args:
            faction: Faction name

        Returns:
            List of NPCs in that faction
        """
        return [
            npc for npc in self.npcs.values()
            if npc.faction.lower() == faction.lower()
        ]

    def get_quest_givers(self) -> list[NPC]:
        """Get all NPCs who can give quests.

        Returns:
            List of quest-giving NPCs
        """
        return [
            npc for npc in self.npcs.values()
            if npc.quest_hooks and npc.is_alive
        ]

    async def generate_npc(
        self,
        role: NPCRole = NPCRole.NEUTRAL,
        location: str = "",
        occupation: str = "",
        race: str = "",
    ) -> NPC:
        """Generate a new NPC.

        Args:
            role: NPC role
            location: Location where NPC is found
            occupation: Specific occupation (random if empty)
            race: Specific race (random if empty)

        Returns:
            Generated NPC
        """
        if self.llm:
            return await self._generate_npc_with_ai(role, location, occupation, race)
        return self._generate_random_npc(role, location, occupation, race)

    async def _generate_npc_with_ai(
        self,
        role: NPCRole,
        location: str,
        occupation: str,
        race: str,
    ) -> NPC:
        """Generate NPC using AI."""
        prompt = f"""Generate an NPC for a Pathfinder 1e campaign.

Role: {role.value}
Location: {location if location else "unspecified"}
Occupation: {occupation if occupation else "any"}
Race: {race if race else "any common race"}

Respond with JSON:
```json
{{
  "name": "Full Name",
  "race": "Race",
  "gender": "male/female",
  "age": "young/adult/middle-aged/elderly",
  "occupation": "their job",
  "description": "Physical description in 1-2 sentences",
  "personality": {{
    "trait1": "primary trait",
    "trait2": "secondary trait",
    "ideal": "what they believe in",
    "bond": "what they care about",
    "flaw": "their weakness",
    "mannerism": "how they act",
    "voice_notes": "how to voice them"
  }},
  "knowledge": ["something they know"],
  "secrets": ["something hidden"],
  "quest_hooks": ["potential quest they could give"]
}}
```"""

        try:
            result = await self.llm.agenerate(
                prompt,
                config=GenerationConfig(temperature=0.9, max_tokens=600),
            )

            # Parse JSON
            content = result.content
            if "```json" in content:
                start = content.index("```json") + 7
                end = content.index("```", start)
                json_str = content[start:end].strip()
            elif "{" in content:
                start = content.index("{")
                end = content.rindex("}") + 1
                json_str = content[start:end]
            else:
                raise ValueError("No JSON found")

            data = json.loads(json_str)

            personality = NPCPersonality(
                trait1=data.get("personality", {}).get("trait1", ""),
                trait2=data.get("personality", {}).get("trait2", ""),
                ideal=data.get("personality", {}).get("ideal", ""),
                bond=data.get("personality", {}).get("bond", ""),
                flaw=data.get("personality", {}).get("flaw", ""),
                mannerism=data.get("personality", {}).get("mannerism", ""),
                voice_notes=data.get("personality", {}).get("voice_notes", ""),
            )

            return NPC(
                name=data.get("name", "Unknown"),
                race=data.get("race", race or "Human"),
                gender=data.get("gender", ""),
                age=data.get("age", "adult"),
                occupation=data.get("occupation", occupation),
                description=data.get("description", ""),
                role=role,
                location=location,
                personality=personality,
                knowledge=data.get("knowledge", []),
                secrets=data.get("secrets", []),
                quest_hooks=data.get("quest_hooks", []) if role == NPCRole.QUEST_GIVER else [],
            )

        except Exception:
            return self._generate_random_npc(role, location, occupation, race)

    def _generate_random_npc(
        self,
        role: NPCRole,
        location: str,
        occupation: str,
        race: str,
    ) -> NPC:
        """Generate a random NPC without AI."""
        gender = random.choice(["male", "female"])
        name = random.choice(self.MALE_NAMES if gender == "male" else self.FEMALE_NAMES)

        if not race:
            race = random.choice(["Human", "Human", "Human", "Elf", "Dwarf", "Halfling"])

        if not occupation:
            occupation = random.choice(self.OCCUPATIONS)

        trait1, trait2 = random.sample(self.TRAITS, 2)
        mannerism = random.choice(self.MANNERISMS)

        personality = NPCPersonality(
            trait1=trait1,
            trait2=trait2,
            mannerism=mannerism,
            voice_notes=f"Speaks in a {trait1} manner",
        )

        return NPC(
            name=name,
            race=race,
            gender=gender,
            age=random.choice(["young", "adult", "adult", "middle-aged", "elderly"]),
            occupation=occupation,
            description=f"A {trait1} {race.lower()} {occupation}.",
            role=role,
            location=location,
            personality=personality,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert all NPCs to dictionary."""
        return {
            name: npc.to_dict()
            for name, npc in self.npcs.items()
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], llm_client: OllamaClient | None = None) -> "NPCManager":
        """Create NPCManager from dictionary."""
        manager = cls(llm_client)
        for name, npc_data in data.items():
            npc = NPC.from_dict(npc_data)
            manager.npcs[name] = npc
        return manager
