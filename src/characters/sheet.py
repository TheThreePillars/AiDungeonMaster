"""Character sheet data model and operations for Pathfinder 1e."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..game.dice import DiceRoller


@dataclass
class AbilityScores:
    """Character ability scores with modifiers."""

    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    # Temporary adjustments (enhancement, penalties, etc.)
    adjustments: dict[str, int] = field(default_factory=dict)

    def get_score(self, ability: str) -> int:
        """Get the total score for an ability including adjustments."""
        base = getattr(self, ability.lower(), 10)
        adjustment = self.adjustments.get(ability.lower(), 0)
        return base + adjustment

    def get_modifier(self, ability: str) -> int:
        """Get the modifier for an ability score."""
        return (self.get_score(ability) - 10) // 2

    def __getitem__(self, key: str) -> int:
        """Allow dictionary-style access to ability scores."""
        return self.get_score(key)


@dataclass
class SavingThrows:
    """Character saving throws."""

    fortitude_base: int = 0
    reflex_base: int = 0
    will_base: int = 0

    # Miscellaneous modifiers
    fortitude_misc: int = 0
    reflex_misc: int = 0
    will_misc: int = 0

    def get_total(self, save: str, abilities: AbilityScores) -> int:
        """Calculate total saving throw bonus."""
        if save == "fortitude":
            return self.fortitude_base + abilities.get_modifier("constitution") + self.fortitude_misc
        elif save == "reflex":
            return self.reflex_base + abilities.get_modifier("dexterity") + self.reflex_misc
        elif save == "will":
            return self.will_base + abilities.get_modifier("wisdom") + self.will_misc
        return 0


@dataclass
class CombatStats:
    """Combat-related statistics."""

    base_attack_bonus: int = 0
    armor_class: int = 10
    touch_ac: int = 10
    flat_footed_ac: int = 10
    cmb: int = 0  # Combat Maneuver Bonus
    cmd: int = 10  # Combat Maneuver Defense
    initiative_misc: int = 0
    speed: int = 30

    def get_initiative(self, abilities: AbilityScores) -> int:
        """Calculate initiative modifier."""
        return abilities.get_modifier("dexterity") + self.initiative_misc


@dataclass
class HitPoints:
    """Character hit point tracking."""

    maximum: int = 1
    current: int = 1
    temporary: int = 0
    nonlethal: int = 0

    @property
    def effective(self) -> int:
        """Get effective HP (current + temp - nonlethal)."""
        return self.current + self.temporary - self.nonlethal

    @property
    def is_conscious(self) -> bool:
        """Check if character is conscious."""
        return self.effective > 0

    @property
    def is_disabled(self) -> bool:
        """Check if character is disabled (at exactly 0 HP)."""
        return self.effective == 0

    @property
    def is_dying(self) -> bool:
        """Check if character is dying (negative HP)."""
        return self.effective < 0 and self.effective > -self.maximum

    @property
    def is_dead(self) -> bool:
        """Check if character is dead (negative HP >= max)."""
        return self.effective <= -self.maximum

    def take_damage(self, amount: int, nonlethal: bool = False) -> None:
        """Apply damage to the character."""
        if nonlethal:
            self.nonlethal += amount
        else:
            # Temp HP absorbs damage first
            if self.temporary > 0:
                absorbed = min(self.temporary, amount)
                self.temporary -= absorbed
                amount -= absorbed
            self.current -= amount

    def heal(self, amount: int) -> int:
        """Heal the character, returning actual amount healed."""
        old_hp = self.current
        self.current = min(self.current + amount, self.maximum)
        return self.current - old_hp


@dataclass
class Skill:
    """A single skill with ranks and modifiers."""

    name: str
    ability: str  # Governing ability
    ranks: int = 0
    class_skill: bool = False
    misc_modifier: int = 0
    armor_check_penalty_applies: bool = False

    def get_total(self, abilities: AbilityScores, armor_check: int = 0) -> int:
        """Calculate total skill bonus."""
        total = abilities.get_modifier(self.ability) + self.ranks + self.misc_modifier
        if self.class_skill and self.ranks > 0:
            total += 3  # Class skill bonus
        if self.armor_check_penalty_applies:
            total += armor_check  # armor_check is typically negative
        return total


class CharacterSheet:
    """Complete Pathfinder 1e character sheet."""

    # Standard PF1e skills
    SKILLS = {
        "Acrobatics": ("dexterity", True),
        "Appraise": ("intelligence", False),
        "Bluff": ("charisma", False),
        "Climb": ("strength", True),
        "Craft": ("intelligence", False),
        "Diplomacy": ("charisma", False),
        "Disable Device": ("dexterity", True),
        "Disguise": ("charisma", False),
        "Escape Artist": ("dexterity", True),
        "Fly": ("dexterity", True),
        "Handle Animal": ("charisma", False),
        "Heal": ("wisdom", False),
        "Intimidate": ("charisma", False),
        "Knowledge (arcana)": ("intelligence", False),
        "Knowledge (dungeoneering)": ("intelligence", False),
        "Knowledge (engineering)": ("intelligence", False),
        "Knowledge (geography)": ("intelligence", False),
        "Knowledge (history)": ("intelligence", False),
        "Knowledge (local)": ("intelligence", False),
        "Knowledge (nature)": ("intelligence", False),
        "Knowledge (nobility)": ("intelligence", False),
        "Knowledge (planes)": ("intelligence", False),
        "Knowledge (religion)": ("intelligence", False),
        "Linguistics": ("intelligence", False),
        "Perception": ("wisdom", False),
        "Perform": ("charisma", False),
        "Profession": ("wisdom", False),
        "Ride": ("dexterity", True),
        "Sense Motive": ("wisdom", False),
        "Sleight of Hand": ("dexterity", True),
        "Spellcraft": ("intelligence", False),
        "Stealth": ("dexterity", True),
        "Survival": ("wisdom", False),
        "Swim": ("strength", True),
        "Use Magic Device": ("charisma", False),
    }

    def __init__(self):
        """Initialize a new character sheet."""
        # Basic info
        self.name: str = ""
        self.player_name: str = ""
        self.race: str = ""
        self.character_class: str = ""
        self.classes: dict[str, int] = {}  # For multiclassing
        self.level: int = 1
        self.experience: int = 0
        self.alignment: str = ""
        self.deity: str = ""
        self.size: str = "Medium"
        self.gender: str = ""
        self.age: int = 0
        self.height: str = ""
        self.weight: str = ""

        # Core stats
        self.abilities = AbilityScores()
        self.saves = SavingThrows()
        self.combat = CombatStats()
        self.hp = HitPoints()

        # Skills
        self.skills: dict[str, Skill] = {}
        self._init_skills()
        self.skill_points_remaining: int = 0

        # Features
        self.feats: list[str] = []
        self.traits: list[str] = []
        self.special_abilities: list[dict[str, Any]] = []
        self.racial_traits: list[dict[str, Any]] = []

        # Spellcasting
        self.is_spellcaster: bool = False
        self.caster_level: int = 0
        self.spell_slots: dict[int, dict[str, int]] = {}  # {level: {"max": X, "used": Y}}
        self.spells_known: list[str] = []
        self.spells_prepared: list[str] = []
        self.concentration_bonus: int = 0

        # Background and roleplay
        self.background: str = ""
        self.backstory: str = ""
        self.personality_traits: str = ""
        self.ideals: str = ""
        self.bonds: str = ""
        self.flaws: str = ""
        self.languages: list[str] = ["Common"]

        # Wealth
        self.platinum: int = 0
        self.gold: int = 0
        self.silver: int = 0
        self.copper: int = 0

        # Equipment (tracked separately but referenced here)
        self.equipped_armor: str = ""
        self.equipped_shield: str = ""
        self.equipped_weapons: list[str] = []
        self.armor_check_penalty: int = 0

        # Conditions
        self.conditions: list[str] = []

    def _init_skills(self) -> None:
        """Initialize all skills."""
        for name, (ability, acp) in self.SKILLS.items():
            self.skills[name] = Skill(
                name=name,
                ability=ability,
                armor_check_penalty_applies=acp,
            )

    def set_class_skills(self, class_skills: list[str]) -> None:
        """Mark skills as class skills."""
        for skill_name in class_skills:
            if skill_name in self.skills:
                self.skills[skill_name].class_skill = True

    def get_attack_bonus(self, is_melee: bool = True, size_mod: int = 0) -> int:
        """Calculate attack bonus."""
        ability = "strength" if is_melee else "dexterity"
        return self.combat.base_attack_bonus + self.abilities.get_modifier(ability) + size_mod

    def calculate_ac(
        self,
        armor_bonus: int = 0,
        shield_bonus: int = 0,
        natural_armor: int = 0,
        deflection: int = 0,
        dodge: int = 0,
        size_mod: int = 0,
    ) -> dict[str, int]:
        """Calculate all AC values."""
        dex_mod = self.abilities.get_modifier("dexterity")

        base = 10 + dex_mod + size_mod + dodge + deflection

        return {
            "ac": base + armor_bonus + shield_bonus + natural_armor,
            "touch": base,
            "flat_footed": base - dex_mod - dodge + armor_bonus + shield_bonus + natural_armor,
        }

    def calculate_cmb(self, size_mod: int = 0) -> int:
        """Calculate Combat Maneuver Bonus."""
        return (
            self.combat.base_attack_bonus
            + self.abilities.get_modifier("strength")
            + size_mod
        )

    def calculate_cmd(self, size_mod: int = 0) -> int:
        """Calculate Combat Maneuver Defense."""
        return (
            10
            + self.combat.base_attack_bonus
            + self.abilities.get_modifier("strength")
            + self.abilities.get_modifier("dexterity")
            + size_mod
        )

    def add_condition(self, condition: str) -> None:
        """Add a condition to the character."""
        if condition not in self.conditions:
            self.conditions.append(condition)

    def remove_condition(self, condition: str) -> None:
        """Remove a condition from the character."""
        if condition in self.conditions:
            self.conditions.remove(condition)

    def get_total_wealth_in_gold(self) -> float:
        """Calculate total wealth in gold pieces."""
        return self.platinum * 10 + self.gold + self.silver / 10 + self.copper / 100

    def add_wealth(self, platinum: int = 0, gold: int = 0, silver: int = 0, copper: int = 0) -> None:
        """Add wealth to the character."""
        self.platinum += platinum
        self.gold += gold
        self.silver += silver
        self.copper += copper

    def to_dict(self) -> dict[str, Any]:
        """Convert character sheet to dictionary for serialization."""
        return {
            "name": self.name,
            "player_name": self.player_name,
            "race": self.race,
            "character_class": self.character_class,
            "classes": self.classes,
            "level": self.level,
            "experience": self.experience,
            "alignment": self.alignment,
            "deity": self.deity,
            "size": self.size,
            "gender": self.gender,
            "age": self.age,
            "height": self.height,
            "weight": self.weight,
            "abilities": {
                "strength": self.abilities.strength,
                "dexterity": self.abilities.dexterity,
                "constitution": self.abilities.constitution,
                "intelligence": self.abilities.intelligence,
                "wisdom": self.abilities.wisdom,
                "charisma": self.abilities.charisma,
                "adjustments": self.abilities.adjustments,
            },
            "saves": {
                "fortitude_base": self.saves.fortitude_base,
                "reflex_base": self.saves.reflex_base,
                "will_base": self.saves.will_base,
                "fortitude_misc": self.saves.fortitude_misc,
                "reflex_misc": self.saves.reflex_misc,
                "will_misc": self.saves.will_misc,
            },
            "combat": {
                "base_attack_bonus": self.combat.base_attack_bonus,
                "armor_class": self.combat.armor_class,
                "touch_ac": self.combat.touch_ac,
                "flat_footed_ac": self.combat.flat_footed_ac,
                "cmb": self.combat.cmb,
                "cmd": self.combat.cmd,
                "initiative_misc": self.combat.initiative_misc,
                "speed": self.combat.speed,
            },
            "hp": {
                "maximum": self.hp.maximum,
                "current": self.hp.current,
                "temporary": self.hp.temporary,
                "nonlethal": self.hp.nonlethal,
            },
            "skills": {
                name: {
                    "ranks": skill.ranks,
                    "class_skill": skill.class_skill,
                    "misc_modifier": skill.misc_modifier,
                }
                for name, skill in self.skills.items()
                if skill.ranks > 0 or skill.misc_modifier != 0
            },
            "feats": self.feats,
            "traits": self.traits,
            "special_abilities": self.special_abilities,
            "is_spellcaster": self.is_spellcaster,
            "caster_level": self.caster_level,
            "spell_slots": self.spell_slots,
            "spells_known": self.spells_known,
            "spells_prepared": self.spells_prepared,
            "background": self.background,
            "backstory": self.backstory,
            "personality_traits": self.personality_traits,
            "ideals": self.ideals,
            "bonds": self.bonds,
            "flaws": self.flaws,
            "languages": self.languages,
            "wealth": {
                "platinum": self.platinum,
                "gold": self.gold,
                "silver": self.silver,
                "copper": self.copper,
            },
            "conditions": self.conditions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CharacterSheet":
        """Create a character sheet from dictionary data."""
        sheet = cls()

        # Basic info
        sheet.name = data.get("name", "")
        sheet.player_name = data.get("player_name", "")
        sheet.race = data.get("race", "")
        sheet.character_class = data.get("character_class", "")
        sheet.classes = data.get("classes", {})
        sheet.level = data.get("level", 1)
        sheet.experience = data.get("experience", 0)
        sheet.alignment = data.get("alignment", "")
        sheet.deity = data.get("deity", "")
        sheet.size = data.get("size", "Medium")
        sheet.gender = data.get("gender", "")
        sheet.age = data.get("age", 0)
        sheet.height = data.get("height", "")
        sheet.weight = data.get("weight", "")

        # Abilities
        if "abilities" in data:
            ab = data["abilities"]
            sheet.abilities.strength = ab.get("strength", 10)
            sheet.abilities.dexterity = ab.get("dexterity", 10)
            sheet.abilities.constitution = ab.get("constitution", 10)
            sheet.abilities.intelligence = ab.get("intelligence", 10)
            sheet.abilities.wisdom = ab.get("wisdom", 10)
            sheet.abilities.charisma = ab.get("charisma", 10)
            sheet.abilities.adjustments = ab.get("adjustments", {})

        # Saves
        if "saves" in data:
            sv = data["saves"]
            sheet.saves.fortitude_base = sv.get("fortitude_base", 0)
            sheet.saves.reflex_base = sv.get("reflex_base", 0)
            sheet.saves.will_base = sv.get("will_base", 0)
            sheet.saves.fortitude_misc = sv.get("fortitude_misc", 0)
            sheet.saves.reflex_misc = sv.get("reflex_misc", 0)
            sheet.saves.will_misc = sv.get("will_misc", 0)

        # Combat
        if "combat" in data:
            cb = data["combat"]
            sheet.combat.base_attack_bonus = cb.get("base_attack_bonus", 0)
            sheet.combat.armor_class = cb.get("armor_class", 10)
            sheet.combat.touch_ac = cb.get("touch_ac", 10)
            sheet.combat.flat_footed_ac = cb.get("flat_footed_ac", 10)
            sheet.combat.cmb = cb.get("cmb", 0)
            sheet.combat.cmd = cb.get("cmd", 10)
            sheet.combat.initiative_misc = cb.get("initiative_misc", 0)
            sheet.combat.speed = cb.get("speed", 30)

        # HP
        if "hp" in data:
            hp = data["hp"]
            sheet.hp.maximum = hp.get("maximum", 1)
            sheet.hp.current = hp.get("current", 1)
            sheet.hp.temporary = hp.get("temporary", 0)
            sheet.hp.nonlethal = hp.get("nonlethal", 0)

        # Skills
        if "skills" in data:
            for name, skill_data in data["skills"].items():
                if name in sheet.skills:
                    sheet.skills[name].ranks = skill_data.get("ranks", 0)
                    sheet.skills[name].class_skill = skill_data.get("class_skill", False)
                    sheet.skills[name].misc_modifier = skill_data.get("misc_modifier", 0)

        # Features
        sheet.feats = data.get("feats", [])
        sheet.traits = data.get("traits", [])
        sheet.special_abilities = data.get("special_abilities", [])

        # Spellcasting
        sheet.is_spellcaster = data.get("is_spellcaster", False)
        sheet.caster_level = data.get("caster_level", 0)
        sheet.spell_slots = data.get("spell_slots", {})
        sheet.spells_known = data.get("spells_known", [])
        sheet.spells_prepared = data.get("spells_prepared", [])

        # Background
        sheet.background = data.get("background", "")
        sheet.backstory = data.get("backstory", "")
        sheet.personality_traits = data.get("personality_traits", "")
        sheet.ideals = data.get("ideals", "")
        sheet.bonds = data.get("bonds", "")
        sheet.flaws = data.get("flaws", "")
        sheet.languages = data.get("languages", ["Common"])

        # Wealth
        if "wealth" in data:
            w = data["wealth"]
            sheet.platinum = w.get("platinum", 0)
            sheet.gold = w.get("gold", 0)
            sheet.silver = w.get("silver", 0)
            sheet.copper = w.get("copper", 0)

        # Conditions
        sheet.conditions = data.get("conditions", [])

        return sheet

    def get_summary(self) -> str:
        """Get a brief summary of the character for display."""
        hp_status = f"{self.hp.current}/{self.hp.maximum}"
        if self.hp.temporary > 0:
            hp_status += f" (+{self.hp.temporary} temp)"

        return (
            f"{self.name} - {self.race} {self.character_class} {self.level}\n"
            f"HP: {hp_status} | AC: {self.combat.armor_class} | "
            f"Fort +{self.saves.get_total('fortitude', self.abilities)} "
            f"Ref +{self.saves.get_total('reflex', self.abilities)} "
            f"Will +{self.saves.get_total('will', self.abilities)}"
        )
