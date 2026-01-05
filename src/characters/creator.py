"""AI-guided character creation wizard for Pathfinder 1e."""

import json
from pathlib import Path
from typing import Any, Callable

from ..game.dice import DiceRoller
from ..llm.client import GenerationConfig, Message, OllamaClient
from .sheet import CharacterSheet


class SRDData:
    """Loader for SRD reference data."""

    def __init__(self, srd_path: Path | str | None = None):
        """Initialize SRD data loader.

        Args:
            srd_path: Path to SRD data directory
        """
        if srd_path:
            self.srd_path = Path(srd_path)
        else:
            self.srd_path = Path("data/srd")

        self._cache: dict[str, Any] = {}

    def _load_file(self, filename: str) -> dict[str, Any]:
        """Load a JSON file from the SRD directory."""
        if filename in self._cache:
            return self._cache[filename]

        file_path = self.srd_path / filename
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cache[filename] = data
                return data
        return {}

    def get_races(self) -> list[dict[str, Any]]:
        """Get all available races."""
        data = self._load_file("races.json")
        return data.get("races", [])

    def get_race(self, name: str) -> dict[str, Any] | None:
        """Get a specific race by name."""
        races = self.get_races()
        for race in races:
            if race["name"].lower() == name.lower():
                return race
        return None

    def get_classes(self) -> list[dict[str, Any]]:
        """Get all available classes."""
        data = self._load_file("classes.json")
        return data.get("classes", [])

    def get_class(self, name: str) -> dict[str, Any] | None:
        """Get a specific class by name."""
        classes = self.get_classes()
        for cls in classes:
            if cls["name"].lower() == name.lower():
                return cls
        return None

    def get_equipment(self) -> dict[str, Any]:
        """Get equipment data."""
        return self._load_file("equipment.json")

    def get_spells(self) -> dict[str, Any]:
        """Get spell data."""
        return self._load_file("spells.json")

    def get_feats(self) -> dict[str, Any]:
        """Get feat data."""
        return self._load_file("feats.json")

    def get_magic_items(self) -> dict[str, Any]:
        """Get magic item data."""
        return self._load_file("magic_items.json")

    def get_artifacts(self) -> dict[str, Any]:
        """Get artifact data."""
        return self._load_file("artifacts.json")

    def get_treasure_tables(self) -> dict[str, Any]:
        """Get treasure table data."""
        return self._load_file("treasure_tables.json")


class CharacterCreator:
    """AI-guided character creation wizard."""

    # Experience required for each level (medium progression)
    XP_TABLE = {
        1: 0, 2: 2000, 3: 5000, 4: 9000, 5: 15000,
        6: 23000, 7: 35000, 8: 51000, 9: 75000, 10: 105000,
        11: 155000, 12: 220000, 13: 315000, 14: 445000, 15: 635000,
        16: 890000, 17: 1300000, 18: 1800000, 19: 2550000, 20: 3600000,
    }

    # BAB progression rates
    BAB_FULL = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    BAB_THREE_QUARTERS = [0, 1, 2, 3, 3, 4, 5, 6, 6, 7, 8, 9, 9, 10, 11, 12, 12, 13, 14, 15]
    BAB_HALF = [0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10]

    # Save progression (good/poor)
    SAVE_GOOD = [2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12]
    SAVE_POOR = [0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6]

    def __init__(
        self,
        llm_client: OllamaClient | None = None,
        srd_data: SRDData | None = None,
    ):
        """Initialize character creator.

        Args:
            llm_client: Ollama client for AI-guided creation
            srd_data: SRD data loader
        """
        self.llm = llm_client
        self.srd = srd_data or SRDData()
        self.roller = DiceRoller()

    def roll_ability_scores(self, method: str = "4d6_drop_lowest") -> dict[str, int]:
        """Roll ability scores using the specified method.

        Args:
            method: Rolling method (4d6_drop_lowest, 3d6, standard_array, point_buy)

        Returns:
            Dictionary of ability scores
        """
        abilities = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]

        if method == "standard_array":
            return dict(zip(abilities, [15, 14, 13, 12, 10, 8]))

        if method == "point_buy":
            # Return base scores for point buy (all 10s, 20 points to spend)
            return dict(zip(abilities, [10, 10, 10, 10, 10, 10]))

        # Roll scores
        results = self.roller.roll_ability_scores(method)
        scores = [r.total for r in results]

        return dict(zip(abilities, scores))

    def apply_racial_modifiers(
        self,
        base_scores: dict[str, int],
        race_name: str,
        chosen_ability: str | None = None,
    ) -> dict[str, int]:
        """Apply racial ability score modifiers.

        Args:
            base_scores: Base ability scores
            race_name: Name of the race
            chosen_ability: For races with flexible bonus, which ability to boost

        Returns:
            Modified ability scores
        """
        race = self.srd.get_race(race_name)
        if not race:
            return base_scores

        scores = base_scores.copy()
        modifiers = race.get("ability_modifiers", {})

        for ability, modifier in modifiers.items():
            if ability == "any":
                # Human, half-elf, half-orc - choose one ability
                if chosen_ability and chosen_ability.lower() in scores:
                    scores[chosen_ability.lower()] += modifier
            elif ability.lower() in scores:
                scores[ability.lower()] += modifier

        return scores

    def calculate_starting_hp(self, character_class: str, con_modifier: int) -> int:
        """Calculate starting HP for a level 1 character.

        Args:
            character_class: Class name
            con_modifier: Constitution modifier

        Returns:
            Starting hit points (max at level 1)
        """
        cls = self.srd.get_class(character_class)
        if not cls:
            return 8 + con_modifier  # Default d8

        hit_die = cls.get("hit_die", 8)
        return max(1, hit_die + con_modifier)  # Max HP at level 1

    def get_bab_for_level(self, character_class: str, level: int) -> int:
        """Get BAB for a class at a given level.

        Args:
            character_class: Class name
            level: Character level

        Returns:
            Base Attack Bonus
        """
        cls = self.srd.get_class(character_class)
        if not cls:
            return self.BAB_THREE_QUARTERS[level - 1]

        progression = cls.get("bab_progression", "three_quarters")
        if progression == "full":
            return self.BAB_FULL[level - 1]
        elif progression == "half":
            return self.BAB_HALF[level - 1]
        else:
            return self.BAB_THREE_QUARTERS[level - 1]

    def get_saves_for_level(self, character_class: str, level: int) -> dict[str, int]:
        """Get base save bonuses for a class at a given level.

        Args:
            character_class: Class name
            level: Character level

        Returns:
            Dictionary with fortitude, reflex, will base saves
        """
        cls = self.srd.get_class(character_class)
        good_saves = cls.get("good_saves", []) if cls else []

        return {
            "fortitude": self.SAVE_GOOD[level - 1] if "fortitude" in good_saves else self.SAVE_POOR[level - 1],
            "reflex": self.SAVE_GOOD[level - 1] if "reflex" in good_saves else self.SAVE_POOR[level - 1],
            "will": self.SAVE_GOOD[level - 1] if "will" in good_saves else self.SAVE_POOR[level - 1],
        }

    def get_skill_points(self, character_class: str, int_modifier: int, is_human: bool = False) -> int:
        """Calculate skill points per level.

        Args:
            character_class: Class name
            int_modifier: Intelligence modifier
            is_human: Whether character is human (bonus skill point)

        Returns:
            Skill points per level
        """
        cls = self.srd.get_class(character_class)
        base = cls.get("skill_ranks_per_level", 2) if cls else 2

        total = base + int_modifier
        if is_human:
            total += 1

        return max(1, total)  # Minimum 1 skill point per level

    def create_character(
        self,
        name: str,
        race: str,
        character_class: str,
        ability_scores: dict[str, int],
        chosen_ability: str | None = None,
    ) -> CharacterSheet:
        """Create a new character with the given parameters.

        Args:
            name: Character name
            race: Race name
            character_class: Class name
            ability_scores: Base ability scores (before racial modifiers)
            chosen_ability: For flexible racial bonus

        Returns:
            Populated CharacterSheet
        """
        sheet = CharacterSheet()

        # Basic info
        sheet.name = name
        sheet.race = race
        sheet.character_class = character_class
        sheet.classes = {character_class: 1}
        sheet.level = 1

        # Apply racial modifiers to abilities
        modified_scores = self.apply_racial_modifiers(ability_scores, race, chosen_ability)
        sheet.abilities.strength = modified_scores["strength"]
        sheet.abilities.dexterity = modified_scores["dexterity"]
        sheet.abilities.constitution = modified_scores["constitution"]
        sheet.abilities.intelligence = modified_scores["intelligence"]
        sheet.abilities.wisdom = modified_scores["wisdom"]
        sheet.abilities.charisma = modified_scores["charisma"]

        # Race data
        race_data = self.srd.get_race(race)
        if race_data:
            sheet.size = race_data.get("size", "Medium")
            sheet.combat.speed = race_data.get("speed", 30)
            sheet.languages = race_data.get("languages", ["Common"]).copy()

            # Add racial traits
            for trait in race_data.get("traits", []):
                sheet.racial_traits.append(trait)

        # Class data
        cls_data = self.srd.get_class(character_class)
        if cls_data:
            # Set class skills
            sheet.set_class_skills(cls_data.get("class_skills", []))

            # Check if spellcaster
            if "spellcasting" in cls_data:
                sheet.is_spellcaster = True

        # Calculate derived stats
        con_mod = sheet.abilities.get_modifier("constitution")
        dex_mod = sheet.abilities.get_modifier("dexterity")

        # HP
        sheet.hp.maximum = self.calculate_starting_hp(character_class, con_mod)
        sheet.hp.current = sheet.hp.maximum

        # BAB
        sheet.combat.base_attack_bonus = self.get_bab_for_level(character_class, 1)

        # Saves
        saves = self.get_saves_for_level(character_class, 1)
        sheet.saves.fortitude_base = saves["fortitude"]
        sheet.saves.reflex_base = saves["reflex"]
        sheet.saves.will_base = saves["will"]

        # CMB/CMD
        size_mod = 0  # Adjust for size if needed
        sheet.combat.cmb = sheet.calculate_cmb(size_mod)
        sheet.combat.cmd = sheet.calculate_cmd(size_mod)

        # AC (base, no armor)
        sheet.combat.armor_class = 10 + dex_mod
        sheet.combat.touch_ac = 10 + dex_mod
        sheet.combat.flat_footed_ac = 10

        # Skill points
        is_human = race.lower() == "human"
        sheet.skill_points_remaining = self.get_skill_points(
            character_class,
            sheet.abilities.get_modifier("intelligence"),
            is_human,
        )

        # Humans get bonus feat
        if is_human:
            # Mark that they need to choose a bonus feat
            pass

        # Starting wealth (average for class)
        starting_gold = self._get_starting_wealth(character_class)
        sheet.gold = starting_gold

        return sheet

    def _get_starting_wealth(self, character_class: str) -> int:
        """Get average starting wealth for a class.

        Args:
            character_class: Class name

        Returns:
            Starting gold pieces
        """
        # Average starting wealth by class
        wealth_table = {
            "barbarian": 105,
            "bard": 105,
            "cleric": 140,
            "druid": 70,
            "fighter": 175,
            "monk": 35,
            "paladin": 175,
            "ranger": 175,
            "rogue": 140,
            "sorcerer": 70,
            "wizard": 70,
        }
        return wealth_table.get(character_class.lower(), 105)

    async def ai_guided_creation(
        self,
        on_message: Callable[[str], None] | None = None,
        get_input: Callable[[str], str] | None = None,
    ) -> CharacterSheet | None:
        """Run AI-guided character creation conversation.

        Args:
            on_message: Callback for displaying AI messages
            get_input: Callback for getting user input

        Returns:
            Created CharacterSheet or None if cancelled
        """
        if not self.llm:
            raise ValueError("LLM client required for AI-guided creation")

        # System prompt for character creation
        system_prompt = """You are helping a player create their Pathfinder 1e character through friendly conversation.

Ask questions one at a time to understand:
1. What fantasy archetype excites them (warrior, mage, rogue, healer, etc.)
2. Preferred combat style (melee, ranged, magic, support)
3. A brief character concept or inspiration

Based on their answers, suggest 2-3 race/class combinations that fit.

Available races: Human, Elf, Dwarf, Halfling, Gnome, Half-Elf, Half-Orc
Available classes: Fighter, Rogue, Wizard, Cleric, Barbarian, Bard, Paladin, Ranger, Sorcerer, Monk, Druid

After they choose, ask for:
- Character name
- Brief personality description

Keep responses concise (2-4 sentences). One question at a time.

When you have all the information needed, respond with a JSON block in this format:
```json
{
  "ready": true,
  "name": "Character Name",
  "race": "Race",
  "class": "Class",
  "personality": "Brief personality"
}
```"""

        messages = [Message(role="system", content=system_prompt)]

        # Start conversation
        intro = "Welcome, adventurer! I'm excited to help you create a character. What kind of hero do you imagine yourself playing? Are you drawn to mighty warriors, cunning rogues, powerful spellcasters, or something else?"

        if on_message:
            on_message(intro)

        messages.append(Message(role="assistant", content=intro))

        # Conversation loop
        while True:
            # Get user input
            if get_input:
                user_input = get_input("> ")
            else:
                user_input = input("> ")

            if not user_input or user_input.lower() in ("quit", "exit", "cancel"):
                return None

            messages.append(Message(role="user", content=user_input))

            # Get AI response
            result = await self.llm.achat(
                messages,
                config=GenerationConfig(temperature=0.7, max_tokens=500),
            )

            response = result.content

            # Check if we have a final JSON response
            if "```json" in response and '"ready": true' in response:
                # Extract JSON
                try:
                    json_start = response.index("```json") + 7
                    json_end = response.index("```", json_start)
                    json_str = response[json_start:json_end].strip()
                    char_data = json.loads(json_str)

                    if char_data.get("ready"):
                        # Create the character
                        ability_scores = self.roll_ability_scores("4d6_drop_lowest")

                        sheet = self.create_character(
                            name=char_data.get("name", "Unnamed"),
                            race=char_data.get("race", "Human"),
                            character_class=char_data.get("class", "Fighter"),
                            ability_scores=ability_scores,
                        )

                        sheet.personality_traits = char_data.get("personality", "")

                        if on_message:
                            on_message(f"\nCharacter created: {sheet.get_summary()}")

                        return sheet

                except (json.JSONDecodeError, ValueError):
                    pass  # Continue conversation if JSON parsing fails

            messages.append(Message(role="assistant", content=response))

            if on_message:
                on_message(response)

    def quick_create(
        self,
        name: str,
        race: str,
        character_class: str,
        method: str = "4d6_drop_lowest",
    ) -> CharacterSheet:
        """Quickly create a character with random stats.

        Args:
            name: Character name
            race: Race name
            character_class: Class name
            method: Ability score rolling method

        Returns:
            Created CharacterSheet
        """
        ability_scores = self.roll_ability_scores(method)

        # For races with flexible bonus, choose highest base score
        chosen = None
        if race.lower() in ("human", "half-elf", "half-orc"):
            chosen = max(ability_scores, key=ability_scores.get)

        return self.create_character(
            name=name,
            race=race,
            character_class=character_class,
            ability_scores=ability_scores,
            chosen_ability=chosen,
        )
