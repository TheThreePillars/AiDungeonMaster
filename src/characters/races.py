"""Race definitions and trait application for Pathfinder 1e."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RacialTrait:
    """A racial trait or ability."""

    name: str
    description: str
    mechanical_effects: dict[str, Any] = field(default_factory=dict)


@dataclass
class Race:
    """A playable race with all its features."""

    name: str
    size: str = "Medium"
    speed: int = 30
    ability_modifiers: dict[str, int] = field(default_factory=dict)
    traits: list[RacialTrait] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    bonus_languages: list[str] = field(default_factory=list)
    vision: str = "normal"
    description: str = ""

    def get_ability_modifier(self, ability: str) -> int:
        """Get the racial modifier for an ability."""
        return self.ability_modifiers.get(ability.lower(), 0)

    def has_darkvision(self) -> bool:
        """Check if race has darkvision."""
        return "darkvision" in self.vision.lower()

    def has_low_light_vision(self) -> bool:
        """Check if race has low-light vision."""
        return "low-light" in self.vision.lower()


class RaceManager:
    """Manager for loading and applying race data."""

    def __init__(self, srd_data: Any = None):
        """Initialize race manager.

        Args:
            srd_data: SRD data loader
        """
        if srd_data is None:
            from .creator import SRDData
            srd_data = SRDData()
        self.srd = srd_data
        self._cache: dict[str, Race] = {}

    def get_race(self, name: str) -> Race | None:
        """Get a race by name.

        Args:
            name: Race name

        Returns:
            Race object or None
        """
        if name.lower() in self._cache:
            return self._cache[name.lower()]

        race_data = self.srd.get_race(name)
        if not race_data:
            return None

        race = self._parse_race_data(race_data)
        self._cache[name.lower()] = race
        return race

    def get_all_races(self) -> list[Race]:
        """Get all available races."""
        races = []
        for race_data in self.srd.get_races():
            race = self._parse_race_data(race_data)
            races.append(race)
            self._cache[race.name.lower()] = race
        return races

    def _parse_race_data(self, data: dict[str, Any]) -> Race:
        """Parse race data from SRD format.

        Args:
            data: Raw race data

        Returns:
            Race object
        """
        # Parse ability modifiers
        ability_mods = {}
        for ability, mod in data.get("ability_modifiers", {}).items():
            if ability != "any":  # 'any' is handled separately
                ability_mods[ability.lower()] = mod

        # Parse traits
        traits = []
        for trait_data in data.get("traits", []):
            trait = RacialTrait(
                name=trait_data.get("name", ""),
                description=trait_data.get("description", ""),
            )
            traits.append(trait)

        # Determine vision type from traits
        vision = "normal"
        for trait in traits:
            if "darkvision" in trait.name.lower():
                vision = "darkvision 60 ft."
            elif "low-light" in trait.name.lower():
                vision = "low-light vision"

        return Race(
            name=data.get("name", "Unknown"),
            size=data.get("size", "Medium"),
            speed=data.get("speed", 30),
            ability_modifiers=ability_mods,
            traits=traits,
            languages=data.get("languages", ["Common"]),
            bonus_languages=data.get("bonus_languages", []),
            vision=vision,
            description=data.get("description", ""),
        )

    def apply_racial_traits(self, character_sheet: Any, race_name: str) -> None:
        """Apply racial traits to a character sheet.

        Args:
            character_sheet: CharacterSheet to modify
            race_name: Name of the race to apply
        """
        race = self.get_race(race_name)
        if not race:
            return

        # Set basic race info
        character_sheet.race = race.name
        character_sheet.size = race.size
        character_sheet.combat.speed = race.speed

        # Apply ability modifiers (handled in creator, but can be re-applied)

        # Set languages
        character_sheet.languages = race.languages.copy()

        # Store racial traits for reference
        character_sheet.racial_traits = [
            {"name": t.name, "description": t.description}
            for t in race.traits
        ]

        # Apply specific mechanical effects
        for trait in race.traits:
            self._apply_trait_effects(character_sheet, trait)

    def _apply_trait_effects(self, sheet: Any, trait: RacialTrait) -> None:
        """Apply mechanical effects of a racial trait.

        Args:
            sheet: CharacterSheet to modify
            trait: Trait to apply
        """
        name_lower = trait.name.lower()

        # Skill bonuses
        if "keen senses" in name_lower:
            if "Perception" in sheet.skills:
                sheet.skills["Perception"].misc_modifier += 2

        # Save bonuses
        if "hardy" in name_lower:  # Dwarf
            sheet.saves.fortitude_misc += 2
            sheet.saves.reflex_misc += 2
            sheet.saves.will_misc += 2

        if "halfling luck" in name_lower:
            sheet.saves.fortitude_misc += 1
            sheet.saves.reflex_misc += 1
            sheet.saves.will_misc += 1

        if "fearless" in name_lower:
            # +2 vs fear (tracked separately, but add to misc for now)
            pass

        # AC bonuses
        if "small" in name_lower:
            # Size bonus to AC is handled by size modifier calculation
            pass

        # Other effects can be added as needed


# Pre-defined races for quick access (used by UI)
RACES: dict[str, Race] = {
    "Human": Race(
        name="Human",
        size="Medium",
        speed=30,
        ability_modifiers={"any": 2},
        traits=["Bonus Feat", "Skilled"],
        languages=["Common"],
        description="Humans are the most adaptable of the common races.",
    ),
    "Elf": Race(
        name="Elf",
        size="Medium",
        speed=30,
        ability_modifiers={"dexterity": 2, "intelligence": 2, "constitution": -2},
        traits=["Elven Immunities", "Keen Senses", "Low-Light Vision"],
        languages=["Common", "Elven"],
        vision="low-light vision",
        description="Elves are a race of long-lived, graceful beings.",
    ),
    "Dwarf": Race(
        name="Dwarf",
        size="Medium",
        speed=20,
        ability_modifiers={"constitution": 2, "wisdom": 2, "charisma": -2},
        traits=["Darkvision", "Defensive Training", "Hardy", "Stonecunning"],
        languages=["Common", "Dwarven"],
        vision="darkvision 60 ft.",
        description="Dwarves are a stoic and stern race.",
    ),
    "Halfling": Race(
        name="Halfling",
        size="Small",
        speed=20,
        ability_modifiers={"dexterity": 2, "charisma": 2, "strength": -2},
        traits=["Fearless", "Halfling Luck", "Keen Senses", "Sure-Footed"],
        languages=["Common", "Halfling"],
        description="Halflings are optimistic and cheerful.",
    ),
    "Gnome": Race(
        name="Gnome",
        size="Small",
        speed=20,
        ability_modifiers={"constitution": 2, "charisma": 2, "strength": -2},
        traits=["Defensive Training", "Gnome Magic", "Keen Senses", "Low-Light Vision"],
        languages=["Common", "Gnome", "Sylvan"],
        vision="low-light vision",
        description="Gnomes are a race of eccentric tinkerers.",
    ),
    "Half-Elf": Race(
        name="Half-Elf",
        size="Medium",
        speed=30,
        ability_modifiers={"any": 2},
        traits=["Adaptability", "Elf Blood", "Keen Senses", "Low-Light Vision"],
        languages=["Common", "Elven"],
        vision="low-light vision",
        description="Half-elves stand between the worlds of their parents.",
    ),
    "Half-Orc": Race(
        name="Half-Orc",
        size="Medium",
        speed=30,
        ability_modifiers={"any": 2},
        traits=["Darkvision", "Intimidating", "Orc Blood", "Orc Ferocity"],
        languages=["Common", "Orc"],
        vision="darkvision 60 ft.",
        description="Half-orcs are often shunned by both parent races.",
    ),
}
