"""AI-powered campaign and adventure generation for Pathfinder 1e."""

import json
import random
from dataclasses import dataclass, field
from typing import Any

from ..llm.client import GenerationConfig, Message, OllamaClient


@dataclass
class PlotHook:
    """A plot hook or adventure seed."""

    title: str
    description: str
    hook_type: str  # mystery, combat, exploration, social, rescue
    difficulty: str  # easy, medium, hard, deadly
    estimated_sessions: int
    locations: list[str] = field(default_factory=list)
    npcs_involved: list[str] = field(default_factory=list)
    rewards: dict[str, Any] = field(default_factory=dict)


@dataclass
class Encounter:
    """A generated encounter."""

    name: str
    description: str
    encounter_type: str  # combat, social, puzzle, trap, exploration
    difficulty: str
    enemies: list[dict[str, Any]] = field(default_factory=list)
    environment: str = ""
    tactics: str = ""
    treasure: list[str] = field(default_factory=list)
    xp_reward: int = 0


@dataclass
class Location:
    """A generated location."""

    name: str
    location_type: str  # town, dungeon, wilderness, building
    description: str
    atmosphere: str
    notable_features: list[str] = field(default_factory=list)
    npcs: list[str] = field(default_factory=list)
    encounters: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    connections: list[str] = field(default_factory=list)


class CampaignGenerator:
    """Generates campaign content using AI."""

    # Encounter difficulty XP budgets by party level (4 players)
    XP_BUDGETS = {
        1: {"easy": 400, "medium": 600, "hard": 800, "deadly": 1200},
        2: {"easy": 600, "medium": 900, "hard": 1200, "deadly": 1800},
        3: {"easy": 800, "medium": 1200, "hard": 1600, "deadly": 2400},
        4: {"easy": 1000, "medium": 1500, "hard": 2000, "deadly": 3000},
        5: {"easy": 1400, "medium": 2100, "hard": 2800, "deadly": 4200},
    }

    def __init__(self, llm_client: OllamaClient | None = None):
        """Initialize the campaign generator.

        Args:
            llm_client: Ollama client for AI generation
        """
        self.llm = llm_client

    async def generate_plot_hook(
        self,
        party_level: int = 1,
        setting: str = "fantasy",
        themes: list[str] | None = None,
        exclude_types: list[str] | None = None,
    ) -> PlotHook | None:
        """Generate a plot hook for an adventure.

        Args:
            party_level: Average party level
            setting: Campaign setting
            themes: Preferred themes (mystery, horror, heroic, etc.)
            exclude_types: Hook types to exclude

        Returns:
            Generated PlotHook or None if generation fails
        """
        if not self.llm:
            return self._generate_random_plot_hook(party_level)

        themes_str = ", ".join(themes) if themes else "varied"
        exclude_str = ", ".join(exclude_types) if exclude_types else "none"

        prompt = f"""Generate a plot hook for a Pathfinder 1e adventure.

Party Level: {party_level}
Setting: {setting}
Preferred Themes: {themes_str}
Exclude Types: {exclude_str}

Respond with a JSON object:
```json
{{
  "title": "Adventure Title",
  "description": "2-3 sentence hook that draws players in",
  "hook_type": "mystery|combat|exploration|social|rescue",
  "difficulty": "easy|medium|hard|deadly",
  "estimated_sessions": 1-5,
  "locations": ["Location 1", "Location 2"],
  "npcs_involved": ["NPC Name 1", "NPC Name 2"],
  "rewards": {{"gold": 500, "items": ["Item 1"], "xp": 1000}}
}}
```"""

        try:
            result = await self.llm.agenerate(
                prompt,
                config=GenerationConfig(temperature=0.8, max_tokens=600),
            )

            # Parse JSON from response
            json_str = self._extract_json(result.content)
            if json_str:
                data = json.loads(json_str)
                return PlotHook(
                    title=data.get("title", "Untitled Adventure"),
                    description=data.get("description", ""),
                    hook_type=data.get("hook_type", "mystery"),
                    difficulty=data.get("difficulty", "medium"),
                    estimated_sessions=data.get("estimated_sessions", 1),
                    locations=data.get("locations", []),
                    npcs_involved=data.get("npcs_involved", []),
                    rewards=data.get("rewards", {}),
                )
        except Exception:
            pass

        return self._generate_random_plot_hook(party_level)

    async def generate_encounter(
        self,
        party_level: int,
        party_size: int = 4,
        difficulty: str = "medium",
        environment: str = "dungeon",
        encounter_type: str = "combat",
    ) -> Encounter | None:
        """Generate an encounter appropriate for the party.

        Args:
            party_level: Average party level
            party_size: Number of party members
            difficulty: Encounter difficulty
            environment: Environment type
            encounter_type: Type of encounter

        Returns:
            Generated Encounter or None
        """
        if not self.llm:
            return self._generate_random_encounter(party_level, difficulty)

        prompt = f"""Generate a {difficulty} {encounter_type} encounter for Pathfinder 1e.

Party: {party_size} level {party_level} characters
Environment: {environment}
Difficulty: {difficulty}

For combat encounters, use appropriate CR creatures.
Level {party_level} party can handle CR {party_level} as medium difficulty.

Respond with JSON:
```json
{{
  "name": "Encounter Name",
  "description": "2-3 sentences setting the scene",
  "encounter_type": "{encounter_type}",
  "difficulty": "{difficulty}",
  "enemies": [
    {{"name": "Creature", "count": 2, "cr": 1, "hp": 15, "ac": 14, "attack": "+3 (1d6+2)"}}
  ],
  "environment": "Description of terrain and features",
  "tactics": "How enemies fight",
  "treasure": ["Item 1", "50 gp"],
  "xp_reward": 600
}}
```"""

        try:
            result = await self.llm.agenerate(
                prompt,
                config=GenerationConfig(temperature=0.7, max_tokens=700),
            )

            json_str = self._extract_json(result.content)
            if json_str:
                data = json.loads(json_str)
                return Encounter(
                    name=data.get("name", "Encounter"),
                    description=data.get("description", ""),
                    encounter_type=data.get("encounter_type", encounter_type),
                    difficulty=data.get("difficulty", difficulty),
                    enemies=data.get("enemies", []),
                    environment=data.get("environment", ""),
                    tactics=data.get("tactics", ""),
                    treasure=data.get("treasure", []),
                    xp_reward=data.get("xp_reward", 0),
                )
        except Exception:
            pass

        return self._generate_random_encounter(party_level, difficulty)

    async def generate_location(
        self,
        location_type: str = "dungeon",
        theme: str = "ancient ruins",
        size: str = "medium",
    ) -> Location | None:
        """Generate a location for exploration.

        Args:
            location_type: Type of location
            theme: Theme or style
            size: small, medium, large

        Returns:
            Generated Location or None
        """
        if not self.llm:
            return self._generate_random_location(location_type)

        prompt = f"""Generate a {size} {location_type} location for Pathfinder 1e.

Type: {location_type}
Theme: {theme}
Size: {size}

Respond with JSON:
```json
{{
  "name": "Location Name",
  "location_type": "{location_type}",
  "description": "2-3 sentences describing the location",
  "atmosphere": "The mood and feeling",
  "notable_features": ["Feature 1", "Feature 2", "Feature 3"],
  "npcs": ["NPC who might be here"],
  "encounters": ["Possible encounter"],
  "secrets": ["Hidden thing to discover"],
  "connections": ["Where this connects to"]
}}
```"""

        try:
            result = await self.llm.agenerate(
                prompt,
                config=GenerationConfig(temperature=0.8, max_tokens=600),
            )

            json_str = self._extract_json(result.content)
            if json_str:
                data = json.loads(json_str)
                return Location(
                    name=data.get("name", "Unknown Location"),
                    location_type=data.get("location_type", location_type),
                    description=data.get("description", ""),
                    atmosphere=data.get("atmosphere", ""),
                    notable_features=data.get("notable_features", []),
                    npcs=data.get("npcs", []),
                    encounters=data.get("encounters", []),
                    secrets=data.get("secrets", []),
                    connections=data.get("connections", []),
                )
        except Exception:
            pass

        return self._generate_random_location(location_type)

    async def generate_session_recap(
        self,
        events: list[str],
        npcs_met: list[str],
        locations_visited: list[str],
        combat_summary: str = "",
    ) -> str:
        """Generate a narrative recap of a session.

        Args:
            events: List of significant events
            npcs_met: NPCs encountered
            locations_visited: Places visited
            combat_summary: Brief combat summary

        Returns:
            Narrative recap string
        """
        if not self.llm:
            return self._generate_simple_recap(events, npcs_met, locations_visited)

        prompt = f"""Write a brief "Previously on..." style recap for a Pathfinder session.

Events:
{chr(10).join(f"- {e}" for e in events)}

NPCs Met: {", ".join(npcs_met) if npcs_met else "None"}
Locations: {", ".join(locations_visited) if locations_visited else "None"}
Combat: {combat_summary if combat_summary else "No major battles"}

Write 2-3 paragraphs in dramatic narrative style, suitable for reading aloud at the start of the next session."""

        try:
            result = await self.llm.agenerate(
                prompt,
                config=GenerationConfig(temperature=0.7, max_tokens=500),
            )
            return result.content.strip()
        except Exception:
            return self._generate_simple_recap(events, npcs_met, locations_visited)

    def _extract_json(self, text: str) -> str | None:
        """Extract JSON from text that may contain markdown code blocks."""
        # Try to find JSON in code blocks
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            return text[start:end].strip()
        elif "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            return text[start:end].strip()
        elif "{" in text and "}" in text:
            # Try to find raw JSON
            start = text.index("{")
            end = text.rindex("}") + 1
            return text[start:end]
        return None

    def _generate_random_plot_hook(self, party_level: int) -> PlotHook:
        """Generate a random plot hook without AI."""
        hooks = [
            PlotHook(
                title="The Missing Caravan",
                description="A merchant caravan has vanished on the road between towns. The guild is offering a reward for information or rescue.",
                hook_type="mystery",
                difficulty="medium",
                estimated_sessions=2,
                locations=["Trade Road", "Bandit Camp"],
                npcs_involved=["Merchant Guildmaster"],
                rewards={"gold": 200 * party_level, "xp": 400 * party_level},
            ),
            PlotHook(
                title="Shadows in the Ruins",
                description="Strange lights have been seen in the old temple ruins. Locals fear the dead are rising.",
                hook_type="exploration",
                difficulty="medium",
                estimated_sessions=3,
                locations=["Ancient Temple", "Catacombs"],
                npcs_involved=["Village Elder", "Local Priest"],
                rewards={"gold": 300 * party_level, "xp": 600 * party_level},
            ),
            PlotHook(
                title="The Baron's Request",
                description="The local baron needs adventurers to escort his daughter to the capital. But someone doesn't want her to arrive.",
                hook_type="social",
                difficulty="hard",
                estimated_sessions=4,
                locations=["Baron's Manor", "King's Road", "Capital City"],
                npcs_involved=["Baron Aldric", "Lady Elara"],
                rewards={"gold": 500 * party_level, "xp": 800 * party_level},
            ),
        ]
        return random.choice(hooks)

    def _generate_random_encounter(self, party_level: int, difficulty: str) -> Encounter:
        """Generate a random encounter without AI."""
        encounters = [
            Encounter(
                name="Goblin Ambush",
                description="A group of goblins springs from the bushes, weapons drawn!",
                encounter_type="combat",
                difficulty=difficulty,
                enemies=[{"name": "Goblin", "count": 3 + party_level, "cr": 0.33, "hp": 6, "ac": 16}],
                environment="Wooded road with thick underbrush",
                tactics="Goblins try to flank and use hit-and-run tactics",
                treasure=["15 gp", "Short sword"],
                xp_reward=135 * (3 + party_level),
            ),
            Encounter(
                name="Wolf Pack",
                description="Hungry wolves circle the party, growling menacingly.",
                encounter_type="combat",
                difficulty=difficulty,
                enemies=[{"name": "Wolf", "count": 2 + party_level // 2, "cr": 1, "hp": 13, "ac": 14}],
                environment="Forest clearing",
                tactics="Wolves try to trip and isolate weak targets",
                treasure=[],
                xp_reward=400 * (2 + party_level // 2),
            ),
        ]
        return random.choice(encounters)

    def _generate_random_location(self, location_type: str) -> Location:
        """Generate a random location without AI."""
        return Location(
            name="The Old Mill",
            location_type=location_type,
            description="An abandoned watermill sits beside a slow-moving stream. The wheel has long since stopped turning.",
            atmosphere="Eerie and quiet, with the occasional creak of old wood",
            notable_features=["Broken waterwheel", "Dusty grain stores", "Hidden cellar"],
            npcs=["Ghost of the Miller (optional)"],
            encounters=["Rat swarm", "Bandits using it as a hideout"],
            secrets=["Hidden cache of coins in the cellar"],
            connections=["Stream leads to the village", "Path through the woods"],
        )

    def _generate_simple_recap(
        self,
        events: list[str],
        npcs_met: list[str],
        locations_visited: list[str],
    ) -> str:
        """Generate a simple recap without AI."""
        recap = "When last we left our heroes...\n\n"

        if locations_visited:
            recap += f"The party traveled to {', '.join(locations_visited)}. "

        if events:
            recap += "They " + "; ".join(events).lower() + ". "

        if npcs_met:
            recap += f"Along the way, they encountered {', '.join(npcs_met)}."

        return recap
