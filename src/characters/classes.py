"""Class definitions and feature application for Pathfinder 1e."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClassFeature:
    """A class feature or ability."""

    name: str
    level: int
    description: str
    mechanical_effects: dict[str, Any] = field(default_factory=dict)


@dataclass
class CharacterClass:
    """A character class with all its features."""

    name: str
    hit_die: int = 8
    bab_progression: str = "three_quarters"  # full, three_quarters, half
    good_saves: list[str] = field(default_factory=list)
    skill_ranks_per_level: int = 2
    class_skills: list[str] = field(default_factory=list)
    weapon_proficiency: list[str] = field(default_factory=list)
    armor_proficiency: list[str] = field(default_factory=list)
    features: list[ClassFeature] = field(default_factory=list)
    spellcasting: dict[str, Any] | None = None
    description: str = ""
    role: str = ""

    def get_features_at_level(self, level: int) -> list[ClassFeature]:
        """Get features gained at a specific level."""
        return [f for f in self.features if f.level == level]

    def get_features_up_to_level(self, level: int) -> list[ClassFeature]:
        """Get all features gained up to and including a level."""
        return [f for f in self.features if f.level <= level]

    def is_spellcaster(self) -> bool:
        """Check if class has spellcasting."""
        return self.spellcasting is not None

    def get_caster_ability(self) -> str | None:
        """Get the spellcasting ability for this class."""
        if self.spellcasting:
            return self.spellcasting.get("ability")
        return None


class ClassManager:
    """Manager for loading and applying class data."""

    # BAB progression tables
    BAB_FULL = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    BAB_THREE_QUARTERS = [0, 1, 2, 3, 3, 4, 5, 6, 6, 7, 8, 9, 9, 10, 11, 12, 12, 13, 14, 15]
    BAB_HALF = [0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10]

    # Save progression tables
    SAVE_GOOD = [2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12]
    SAVE_POOR = [0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6]

    def __init__(self, srd_data: Any = None):
        """Initialize class manager.

        Args:
            srd_data: SRD data loader
        """
        if srd_data is None:
            from .creator import SRDData
            srd_data = SRDData()
        self.srd = srd_data
        self._cache: dict[str, CharacterClass] = {}

    def get_class(self, name: str) -> CharacterClass | None:
        """Get a class by name.

        Args:
            name: Class name

        Returns:
            CharacterClass object or None
        """
        if name.lower() in self._cache:
            return self._cache[name.lower()]

        class_data = self.srd.get_class(name)
        if not class_data:
            return None

        char_class = self._parse_class_data(class_data)
        self._cache[name.lower()] = char_class
        return char_class

    def get_all_classes(self) -> list[CharacterClass]:
        """Get all available classes."""
        classes = []
        for class_data in self.srd.get_classes():
            char_class = self._parse_class_data(class_data)
            classes.append(char_class)
            self._cache[char_class.name.lower()] = char_class
        return classes

    def _parse_class_data(self, data: dict[str, Any]) -> CharacterClass:
        """Parse class data from SRD format.

        Args:
            data: Raw class data

        Returns:
            CharacterClass object
        """
        # Parse features
        features = []
        for feature_data in data.get("features", []):
            feature = ClassFeature(
                name=feature_data.get("name", ""),
                level=feature_data.get("level", 1),
                description=feature_data.get("description", ""),
            )
            features.append(feature)

        return CharacterClass(
            name=data.get("name", "Unknown"),
            hit_die=data.get("hit_die", 8),
            bab_progression=data.get("bab_progression", "three_quarters"),
            good_saves=data.get("good_saves", []),
            skill_ranks_per_level=data.get("skill_ranks_per_level", 2),
            class_skills=data.get("class_skills", []),
            weapon_proficiency=data.get("weapon_proficiency", []),
            armor_proficiency=data.get("armor_proficiency", []),
            features=features,
            spellcasting=data.get("spellcasting"),
            description=data.get("description", ""),
            role=data.get("role", ""),
        )

    def get_bab_at_level(self, class_name: str, level: int) -> int:
        """Get BAB for a class at a given level.

        Args:
            class_name: Class name
            level: Character level

        Returns:
            Base Attack Bonus
        """
        char_class = self.get_class(class_name)
        if not char_class:
            return self.BAB_THREE_QUARTERS[level - 1]

        if char_class.bab_progression == "full":
            return self.BAB_FULL[level - 1]
        elif char_class.bab_progression == "half":
            return self.BAB_HALF[level - 1]
        else:
            return self.BAB_THREE_QUARTERS[level - 1]

    def get_saves_at_level(self, class_name: str, level: int) -> dict[str, int]:
        """Get base saves for a class at a given level.

        Args:
            class_name: Class name
            level: Character level

        Returns:
            Dict with fortitude, reflex, will base saves
        """
        char_class = self.get_class(class_name)
        good_saves = char_class.good_saves if char_class else []

        return {
            "fortitude": self.SAVE_GOOD[level - 1] if "fortitude" in good_saves else self.SAVE_POOR[level - 1],
            "reflex": self.SAVE_GOOD[level - 1] if "reflex" in good_saves else self.SAVE_POOR[level - 1],
            "will": self.SAVE_GOOD[level - 1] if "will" in good_saves else self.SAVE_POOR[level - 1],
        }

    def apply_class_features(self, character_sheet: Any, class_name: str, level: int = 1) -> None:
        """Apply class features to a character sheet.

        Args:
            character_sheet: CharacterSheet to modify
            class_name: Name of the class
            level: Character level
        """
        char_class = self.get_class(class_name)
        if not char_class:
            return

        # Set basic class info
        character_sheet.character_class = char_class.name

        # Set class skills
        character_sheet.set_class_skills(char_class.class_skills)

        # Calculate BAB
        character_sheet.combat.base_attack_bonus = self.get_bab_at_level(class_name, level)

        # Calculate saves
        saves = self.get_saves_at_level(class_name, level)
        character_sheet.saves.fortitude_base = saves["fortitude"]
        character_sheet.saves.reflex_base = saves["reflex"]
        character_sheet.saves.will_base = saves["will"]

        # Set spellcasting if applicable
        if char_class.is_spellcaster():
            character_sheet.is_spellcaster = True
            character_sheet.caster_level = level

        # Store class features for reference
        features = char_class.get_features_up_to_level(level)
        character_sheet.special_abilities = [
            {"name": f.name, "level": f.level, "description": f.description}
            for f in features
        ]

    def get_hp_at_level(self, class_name: str, level: int, con_modifier: int) -> int:
        """Calculate HP for a class at a given level.

        Args:
            class_name: Class name
            level: Character level
            con_modifier: Constitution modifier

        Returns:
            Total hit points
        """
        char_class = self.get_class(class_name)
        hit_die = char_class.hit_die if char_class else 8

        # Level 1 gets max HP
        hp = hit_die + con_modifier

        # Subsequent levels get average + 1 (standard PFS rule)
        if level > 1:
            avg_roll = (hit_die // 2) + 1
            hp += (avg_roll + con_modifier) * (level - 1)

        return max(1, hp)  # Minimum 1 HP

    def get_skill_points(
        self,
        class_name: str,
        int_modifier: int,
        is_human: bool = False,
        level: int = 1,
    ) -> int:
        """Calculate total skill points for a character.

        Args:
            class_name: Class name
            int_modifier: Intelligence modifier
            is_human: Whether character is human
            level: Character level

        Returns:
            Total skill points
        """
        char_class = self.get_class(class_name)
        base = char_class.skill_ranks_per_level if char_class else 2

        per_level = max(1, base + int_modifier)
        if is_human:
            per_level += 1

        return per_level * level


# Pre-defined classes for quick access (used by UI)
CLASSES: dict[str, CharacterClass] = {
    "Fighter": CharacterClass(
        name="Fighter",
        hit_die=10,
        bab_progression="full",
        good_saves=["fortitude"],
        skill_ranks_per_level=2,
        class_skills=["Climb", "Craft", "Handle Animal", "Intimidate", "Knowledge (dungeoneering)",
                      "Knowledge (engineering)", "Profession", "Ride", "Survival", "Swim"],
        description="Masters of combat and martial prowess.",
    ),
    "Rogue": CharacterClass(
        name="Rogue",
        hit_die=8,
        bab_progression="three_quarters",
        good_saves=["reflex"],
        skill_ranks_per_level=8,
        class_skills=["Acrobatics", "Appraise", "Bluff", "Climb", "Craft", "Diplomacy",
                      "Disable Device", "Disguise", "Escape Artist", "Intimidate",
                      "Knowledge (dungeoneering)", "Knowledge (local)", "Linguistics",
                      "Perception", "Perform", "Profession", "Sense Motive", "Sleight of Hand",
                      "Stealth", "Swim", "Use Magic Device"],
        description="Skilled in stealth, traps, and precision attacks.",
    ),
    "Wizard": CharacterClass(
        name="Wizard",
        hit_die=6,
        bab_progression="half",
        good_saves=["will"],
        skill_ranks_per_level=2,
        class_skills=["Appraise", "Craft", "Fly", "Knowledge (all)", "Linguistics",
                      "Profession", "Spellcraft"],
        spellcasting={"ability": "intelligence", "type": "arcane", "prepared": True},
        description="Masters of arcane magic through study.",
    ),
    "Cleric": CharacterClass(
        name="Cleric",
        hit_die=8,
        bab_progression="three_quarters",
        good_saves=["fortitude", "will"],
        skill_ranks_per_level=2,
        class_skills=["Appraise", "Craft", "Diplomacy", "Heal", "Knowledge (arcana)",
                      "Knowledge (history)", "Knowledge (nobility)", "Knowledge (planes)",
                      "Knowledge (religion)", "Linguistics", "Profession", "Sense Motive",
                      "Spellcraft"],
        spellcasting={"ability": "wisdom", "type": "divine", "prepared": True},
        description="Divine spellcasters who serve their deity.",
    ),
    "Barbarian": CharacterClass(
        name="Barbarian",
        hit_die=12,
        bab_progression="full",
        good_saves=["fortitude"],
        skill_ranks_per_level=4,
        class_skills=["Acrobatics", "Climb", "Craft", "Handle Animal", "Intimidate",
                      "Knowledge (nature)", "Perception", "Ride", "Survival", "Swim"],
        description="Fierce warriors driven by rage.",
    ),
    "Bard": CharacterClass(
        name="Bard",
        hit_die=8,
        bab_progression="three_quarters",
        good_saves=["reflex", "will"],
        skill_ranks_per_level=6,
        class_skills=["Acrobatics", "Appraise", "Bluff", "Climb", "Craft", "Diplomacy",
                      "Disguise", "Escape Artist", "Intimidate", "Knowledge (all)",
                      "Linguistics", "Perception", "Perform", "Profession", "Sense Motive",
                      "Sleight of Hand", "Spellcraft", "Stealth", "Use Magic Device"],
        spellcasting={"ability": "charisma", "type": "arcane", "prepared": False},
        description="Versatile performers who weave magic into their art.",
    ),
    "Paladin": CharacterClass(
        name="Paladin",
        hit_die=10,
        bab_progression="full",
        good_saves=["fortitude", "will"],
        skill_ranks_per_level=2,
        class_skills=["Craft", "Diplomacy", "Handle Animal", "Heal", "Knowledge (nobility)",
                      "Knowledge (religion)", "Profession", "Ride", "Sense Motive", "Spellcraft"],
        spellcasting={"ability": "charisma", "type": "divine", "prepared": True},
        description="Holy warriors bound by sacred oaths.",
    ),
    "Ranger": CharacterClass(
        name="Ranger",
        hit_die=10,
        bab_progression="full",
        good_saves=["fortitude", "reflex"],
        skill_ranks_per_level=6,
        class_skills=["Climb", "Craft", "Handle Animal", "Heal", "Intimidate",
                      "Knowledge (dungeoneering)", "Knowledge (geography)", "Knowledge (nature)",
                      "Perception", "Profession", "Ride", "Spellcraft", "Stealth",
                      "Survival", "Swim"],
        spellcasting={"ability": "wisdom", "type": "divine", "prepared": True},
        description="Skilled hunters and trackers of the wilderness.",
    ),
    "Sorcerer": CharacterClass(
        name="Sorcerer",
        hit_die=6,
        bab_progression="half",
        good_saves=["will"],
        skill_ranks_per_level=2,
        class_skills=["Appraise", "Bluff", "Craft", "Fly", "Intimidate",
                      "Knowledge (arcana)", "Profession", "Spellcraft", "Use Magic Device"],
        spellcasting={"ability": "charisma", "type": "arcane", "prepared": False},
        description="Spellcasters with innate magical power.",
    ),
    "Monk": CharacterClass(
        name="Monk",
        hit_die=8,
        bab_progression="three_quarters",
        good_saves=["fortitude", "reflex", "will"],
        skill_ranks_per_level=4,
        class_skills=["Acrobatics", "Climb", "Craft", "Escape Artist", "Intimidate",
                      "Knowledge (history)", "Knowledge (religion)", "Perception",
                      "Perform", "Profession", "Ride", "Sense Motive", "Stealth", "Swim"],
        description="Masters of martial arts and inner ki.",
    ),
    "Druid": CharacterClass(
        name="Druid",
        hit_die=8,
        bab_progression="three_quarters",
        good_saves=["fortitude", "will"],
        skill_ranks_per_level=4,
        class_skills=["Climb", "Craft", "Fly", "Handle Animal", "Heal",
                      "Knowledge (geography)", "Knowledge (nature)", "Perception",
                      "Profession", "Ride", "Spellcraft", "Survival", "Swim"],
        spellcasting={"ability": "wisdom", "type": "divine", "prepared": True},
        description="Guardians of nature with primal magic.",
    ),
}
