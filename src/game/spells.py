"""Spell definitions and casting mechanics for Pathfinder 1e."""

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from typing import Any

from .dice import DiceRoller


class SpellSchool(Enum):
    """Schools of magic."""
    ABJURATION = "Abjuration"
    CONJURATION = "Conjuration"
    DIVINATION = "Divination"
    ENCHANTMENT = "Enchantment"
    EVOCATION = "Evocation"
    ILLUSION = "Illusion"
    NECROMANCY = "Necromancy"
    TRANSMUTATION = "Transmutation"
    UNIVERSAL = "Universal"


class SpellRange(Enum):
    """Spell range categories."""
    PERSONAL = "Personal"
    TOUCH = "Touch"
    CLOSE = "Close (25 ft + 5 ft/2 levels)"
    MEDIUM = "Medium (100 ft + 10 ft/level)"
    LONG = "Long (400 ft + 40 ft/level)"
    UNLIMITED = "Unlimited"


class SpellDuration(Enum):
    """Spell duration types."""
    INSTANTANEOUS = "Instantaneous"
    ROUNDS_PER_LEVEL = "1 round/level"
    MINUTES_PER_LEVEL = "1 min/level"
    HOURS_PER_LEVEL = "1 hour/level"
    CONCENTRATION = "Concentration"
    PERMANENT = "Permanent"


@dataclass
class Spell:
    """A spell with all its properties."""
    name: str
    level: dict[str, int]  # {"wizard": 1, "sorcerer": 1, "cleric": 1}
    school: SpellSchool
    description: str
    casting_time: str = "1 standard action"
    components: list[str] = field(default_factory=lambda: ["V", "S"])
    range: str = "Close"
    target: str = ""
    duration: str = "Instantaneous"
    saving_throw: str = "None"
    spell_resistance: bool = False
    damage_dice: str | None = None  # e.g., "1d6" per level
    damage_type: str | None = None
    heal_dice: str | None = None
    effect: str = ""

    def get_level_for_class(self, class_name: str) -> int | None:
        """Get spell level for a specific class."""
        return self.level.get(class_name.lower())


def _school_from_text(text: str) -> SpellSchool:
    text = text.strip().upper()
    for school in SpellSchool:
        if school.name == text or school.value.upper() == text:
            return school
    return SpellSchool.UNIVERSAL


def load_spells_from_srd(srd_path: Path | None = None) -> dict[str, Spell]:
    """Load spells from SRD JSON if available."""
    path = srd_path or Path("data/srd/spells.json")
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    spells: dict[str, Spell] = {}
    for bucket in ("cantrips", "spells"):
        for entry in raw.get(bucket, []):
            name = entry.get("name", "").strip()
            if not name:
                continue
            level = entry.get("level", {})
            if not isinstance(level, dict) or not level:
                continue
            components = entry.get("components", ["V", "S"])
            if isinstance(components, str):
                components = [c.strip() for c in components.split(",") if c.strip()]
            spell = Spell(
                name=name,
                level={k.lower(): int(v) for k, v in level.items()},
                school=_school_from_text(entry.get("school", "Universal")),
                description=entry.get("description", ""),
                casting_time=entry.get("casting_time", "1 standard action"),
                components=components,
                range=entry.get("range", "Close"),
                target=entry.get("target", ""),
                duration=entry.get("duration", "Instantaneous"),
                saving_throw=entry.get("saving_throw", "None"),
                spell_resistance=entry.get("spell_resistance", "") in ("yes", "true", True),
                damage_dice=entry.get("damage_dice"),
                damage_type=entry.get("damage_type"),
                heal_dice=entry.get("heal_dice"),
            )
            spells[name.lower()] = spell
    return spells


# Core spell list - common spells for each level (fallback if SRD data missing)
DEFAULT_SPELLS: dict[str, Spell] = {
    # Cantrips/Orisons (Level 0)
    "acid splash": Spell(
        name="Acid Splash",
        level={"wizard": 0, "sorcerer": 0},
        school=SpellSchool.CONJURATION,
        description="You fire a small orb of acid at the target.",
        range="Close",
        damage_dice="1d3",
        damage_type="acid",
        saving_throw="None",
    ),
    "detect magic": Spell(
        name="Detect Magic",
        level={"wizard": 0, "sorcerer": 0, "cleric": 0, "druid": 0, "bard": 0},
        school=SpellSchool.DIVINATION,
        description="Detect magical auras within 60 feet.",
        range="60 ft cone",
        duration="Concentration, up to 1 min/level",
    ),
    "light": Spell(
        name="Light",
        level={"wizard": 0, "sorcerer": 0, "cleric": 0, "druid": 0, "bard": 0},
        school=SpellSchool.EVOCATION,
        description="Object shines like a torch.",
        range="Touch",
        duration="10 min/level",
    ),
    "mage hand": Spell(
        name="Mage Hand",
        level={"wizard": 0, "sorcerer": 0, "bard": 0},
        school=SpellSchool.TRANSMUTATION,
        description="5-pound telekinesis.",
        range="Close",
        duration="Concentration",
    ),
    "ray of frost": Spell(
        name="Ray of Frost",
        level={"wizard": 0, "sorcerer": 0},
        school=SpellSchool.EVOCATION,
        description="Ray deals 1d3 cold damage.",
        range="Close",
        damage_dice="1d3",
        damage_type="cold",
    ),
    "guidance": Spell(
        name="Guidance",
        level={"cleric": 0, "druid": 0},
        school=SpellSchool.DIVINATION,
        description="+1 on one attack roll, saving throw, or skill check.",
        range="Touch",
        duration="1 minute or until discharged",
    ),
    "stabilize": Spell(
        name="Stabilize",
        level={"cleric": 0, "druid": 0},
        school=SpellSchool.CONJURATION,
        description="Cause a dying creature to stabilize.",
        range="Close",
    ),

    # 1st Level Spells
    "magic missile": Spell(
        name="Magic Missile",
        level={"wizard": 1, "sorcerer": 1},
        school=SpellSchool.EVOCATION,
        description="1d4+1 force damage per missile; +1 missile per 2 levels (max 5).",
        range="Medium",
        damage_dice="1d4+1",
        damage_type="force",
        saving_throw="None",
    ),
    "burning hands": Spell(
        name="Burning Hands",
        level={"wizard": 1, "sorcerer": 1},
        school=SpellSchool.EVOCATION,
        description="1d4 fire damage per level (max 5d4) in 15-ft cone.",
        range="15 ft cone",
        damage_dice="1d4",
        damage_type="fire",
        saving_throw="Reflex half",
    ),
    "sleep": Spell(
        name="Sleep",
        level={"wizard": 1, "sorcerer": 1, "bard": 1},
        school=SpellSchool.ENCHANTMENT,
        description="Puts 4 HD of creatures into magical slumber.",
        range="Medium",
        duration="1 min/level",
        saving_throw="Will negates",
    ),
    "mage armor": Spell(
        name="Mage Armor",
        level={"wizard": 1, "sorcerer": 1},
        school=SpellSchool.CONJURATION,
        description="Gives subject +4 armor bonus.",
        range="Touch",
        duration="1 hour/level",
    ),
    "shield": Spell(
        name="Shield",
        level={"wizard": 1, "sorcerer": 1},
        school=SpellSchool.ABJURATION,
        description="Invisible disc gives +4 to AC, blocks magic missiles.",
        range="Personal",
        duration="1 min/level",
    ),
    "cure light wounds": Spell(
        name="Cure Light Wounds",
        level={"cleric": 1, "druid": 1, "bard": 1, "paladin": 1, "ranger": 2},
        school=SpellSchool.CONJURATION,
        description="Cures 1d8+1/level damage (max +5).",
        range="Touch",
        heal_dice="1d8",
    ),
    "bless": Spell(
        name="Bless",
        level={"cleric": 1, "paladin": 1},
        school=SpellSchool.ENCHANTMENT,
        description="Allies gain +1 on attack rolls and saves vs fear.",
        range="50 ft",
        duration="1 min/level",
    ),
    "cause fear": Spell(
        name="Cause Fear",
        level={"cleric": 1, "wizard": 1, "sorcerer": 1, "bard": 1},
        school=SpellSchool.NECROMANCY,
        description="One creature of 5 HD or less flees for 1d4 rounds.",
        range="Close",
        duration="1d4 rounds",
        saving_throw="Will partial",
    ),

    # 2nd Level Spells
    "scorching ray": Spell(
        name="Scorching Ray",
        level={"wizard": 2, "sorcerer": 2},
        school=SpellSchool.EVOCATION,
        description="Ranged touch attack deals 4d6 fire; +1 ray/4 levels (max 3).",
        range="Close",
        damage_dice="4d6",
        damage_type="fire",
    ),
    "invisibility": Spell(
        name="Invisibility",
        level={"wizard": 2, "sorcerer": 2, "bard": 2},
        school=SpellSchool.ILLUSION,
        description="Subject is invisible for 1 min/level or until it attacks.",
        range="Touch",
        duration="1 min/level",
    ),
    "mirror image": Spell(
        name="Mirror Image",
        level={"wizard": 2, "sorcerer": 2, "bard": 2},
        school=SpellSchool.ILLUSION,
        description="Creates 1d4+1 decoys of yourself.",
        range="Personal",
        duration="1 min/level",
    ),
    "web": Spell(
        name="Web",
        level={"wizard": 2, "sorcerer": 2},
        school=SpellSchool.CONJURATION,
        description="Fills 20-ft-radius spread with sticky spider webs.",
        range="Medium",
        duration="10 min/level",
        saving_throw="Reflex negates",
    ),
    "cure moderate wounds": Spell(
        name="Cure Moderate Wounds",
        level={"cleric": 2, "druid": 3, "bard": 2, "paladin": 3, "ranger": 3},
        school=SpellSchool.CONJURATION,
        description="Cures 2d8+1/level damage (max +10).",
        range="Touch",
        heal_dice="2d8",
    ),
    "hold person": Spell(
        name="Hold Person",
        level={"cleric": 2, "wizard": 3, "sorcerer": 3, "bard": 2},
        school=SpellSchool.ENCHANTMENT,
        description="Paralyzes one humanoid for 1 round/level.",
        range="Medium",
        duration="1 round/level",
        saving_throw="Will negates",
    ),

    # 3rd Level Spells
    "fireball": Spell(
        name="Fireball",
        level={"wizard": 3, "sorcerer": 3},
        school=SpellSchool.EVOCATION,
        description="1d6 fire damage per level (max 10d6) in 20-ft radius.",
        range="Long",
        damage_dice="1d6",
        damage_type="fire",
        saving_throw="Reflex half",
    ),
    "lightning bolt": Spell(
        name="Lightning Bolt",
        level={"wizard": 3, "sorcerer": 3},
        school=SpellSchool.EVOCATION,
        description="1d6 electricity damage per level (max 10d6) in 120-ft line.",
        range="120 ft line",
        damage_dice="1d6",
        damage_type="electricity",
        saving_throw="Reflex half",
    ),
    "haste": Spell(
        name="Haste",
        level={"wizard": 3, "sorcerer": 3, "bard": 3},
        school=SpellSchool.TRANSMUTATION,
        description="One creature/level gains +1 attack, +1 AC, +30 ft speed.",
        range="Close",
        duration="1 round/level",
    ),
    "fly": Spell(
        name="Fly",
        level={"wizard": 3, "sorcerer": 3},
        school=SpellSchool.TRANSMUTATION,
        description="Subject flies at speed of 60 ft.",
        range="Touch",
        duration="1 min/level",
    ),
    "dispel magic": Spell(
        name="Dispel Magic",
        level={"wizard": 3, "sorcerer": 3, "cleric": 3, "druid": 4, "bard": 3, "paladin": 3},
        school=SpellSchool.ABJURATION,
        description="Cancels one magical spell or effect.",
        range="Medium",
    ),
    "cure serious wounds": Spell(
        name="Cure Serious Wounds",
        level={"cleric": 3, "druid": 4, "bard": 3, "paladin": 4, "ranger": 4},
        school=SpellSchool.CONJURATION,
        description="Cures 3d8+1/level damage (max +15).",
        range="Touch",
        heal_dice="3d8",
    ),
}


SPELLS = load_spells_from_srd() or DEFAULT_SPELLS


@dataclass
class SpellSlots:
    """Track spell slots for a character."""
    max_slots: dict[int, int] = field(default_factory=dict)  # {level: count}
    used_slots: dict[int, int] = field(default_factory=dict)

    def get_remaining(self, level: int) -> int:
        """Get remaining slots at a spell level."""
        max_s = self.max_slots.get(level, 0)
        used = self.used_slots.get(level, 0)
        return max(0, max_s - used)

    def use_slot(self, level: int) -> bool:
        """Use a spell slot. Returns True if successful."""
        if self.get_remaining(level) > 0:
            self.used_slots[level] = self.used_slots.get(level, 0) + 1
            return True
        return False

    def restore_slot(self, level: int) -> None:
        """Restore a spell slot."""
        if self.used_slots.get(level, 0) > 0:
            self.used_slots[level] -= 1

    def restore_all(self) -> None:
        """Restore all spell slots (after rest)."""
        self.used_slots = {}

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "max_slots": self.max_slots,
            "used_slots": self.used_slots,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SpellSlots":
        """Create from dictionary."""
        slots = cls()
        slots.max_slots = data.get("max_slots", {})
        slots.used_slots = data.get("used_slots", {})
        return slots


# Spell slots per day by class level (simplified - full casters only)
# Format: {level: {spell_level: slots}}
WIZARD_SLOTS = {
    1: {0: 3, 1: 1},
    2: {0: 4, 1: 2},
    3: {0: 4, 1: 2, 2: 1},
    4: {0: 4, 1: 3, 2: 2},
    5: {0: 4, 1: 3, 2: 2, 3: 1},
    6: {0: 4, 1: 3, 2: 3, 3: 2},
    7: {0: 4, 1: 4, 2: 3, 3: 2, 4: 1},
    8: {0: 4, 1: 4, 2: 3, 3: 3, 4: 2},
    9: {0: 4, 1: 4, 2: 4, 3: 3, 4: 2, 5: 1},
    10: {0: 4, 1: 4, 2: 4, 3: 3, 4: 3, 5: 2},
}

CLERIC_SLOTS = WIZARD_SLOTS.copy()  # Same progression

SORCERER_SLOTS = {
    1: {0: 4, 1: 2},
    2: {0: 5, 1: 3},
    3: {0: 5, 1: 4, 2: 2},
    4: {0: 6, 1: 5, 2: 3},
    5: {0: 6, 1: 5, 2: 4, 3: 2},
    6: {0: 6, 1: 6, 2: 5, 3: 3},
    7: {0: 6, 1: 6, 2: 5, 3: 4, 4: 2},
    8: {0: 6, 1: 6, 2: 6, 3: 5, 4: 3},
    9: {0: 6, 1: 6, 2: 6, 3: 5, 4: 4, 5: 2},
    10: {0: 6, 1: 6, 2: 6, 3: 6, 4: 5, 5: 3},
}

BARD_SLOTS = {
    1: {0: 4, 1: 1},
    2: {0: 5, 1: 2},
    3: {0: 5, 1: 3},
    4: {0: 6, 1: 3, 2: 1},
    5: {0: 6, 1: 4, 2: 2},
    6: {0: 6, 1: 4, 2: 3},
    7: {0: 6, 1: 4, 2: 3, 3: 1},
    8: {0: 6, 1: 4, 2: 4, 3: 2},
    9: {0: 6, 1: 5, 2: 4, 3: 3},
    10: {0: 6, 1: 5, 2: 4, 3: 3, 4: 1},
}


def get_spell_slots_for_class(class_name: str, level: int) -> dict[int, int]:
    """Get spell slots for a class at a given level."""
    class_lower = class_name.lower()

    if class_lower in ["wizard", "druid"]:
        return WIZARD_SLOTS.get(min(level, 10), {})
    elif class_lower == "cleric":
        return CLERIC_SLOTS.get(min(level, 10), {})
    elif class_lower == "sorcerer":
        return SORCERER_SLOTS.get(min(level, 10), {})
    elif class_lower == "bard":
        return BARD_SLOTS.get(min(level, 10), {})
    elif class_lower in ["paladin", "ranger"]:
        # Half-casters: start casting at level 4
        if level < 4:
            return {}
        effective_level = (level - 3) // 2 + 1
        return {1: effective_level, 2: max(0, effective_level - 2)}

    return {}


def get_spells_for_class(class_name: str, max_level: int | None = None) -> list[Spell]:
    """Get all spells available to a class up to a certain level."""
    class_lower = class_name.lower()
    spells = []

    for spell in SPELLS.values():
        spell_level = spell.get_level_for_class(class_lower)
        if spell_level is not None:
            if max_level is None or spell_level <= max_level:
                spells.append(spell)

    return sorted(spells, key=lambda s: (s.get_level_for_class(class_lower) or 0, s.name))


class SpellCaster:
    """Manages spellcasting for a character."""

    def __init__(
        self,
        class_name: str,
        caster_level: int,
        casting_ability_score: int,
        known_spells: list[str] | None = None,
    ):
        self.class_name = class_name
        self.caster_level = caster_level
        self.casting_ability_score = casting_ability_score
        self.casting_ability_mod = (casting_ability_score - 10) // 2

        # Initialize spell slots
        base_slots = get_spell_slots_for_class(class_name, caster_level)
        self.spell_slots = SpellSlots(max_slots=base_slots.copy())

        # Add bonus slots from high ability score
        for spell_level in range(1, 10):
            if spell_level <= self.casting_ability_mod:
                bonus = (self.casting_ability_mod - spell_level) // 4 + 1
                if spell_level in self.spell_slots.max_slots:
                    self.spell_slots.max_slots[spell_level] += bonus

        # Known spells (for spontaneous casters) or prepared spells
        self.known_spells = known_spells or []
        self.prepared_spells: list[str] = []

        self.roller = DiceRoller()

    def get_spell_dc(self, spell_level: int) -> int:
        """Calculate save DC for a spell."""
        return 10 + spell_level + self.casting_ability_mod

    def can_cast(self, spell_name: str) -> tuple[bool, str]:
        """Check if character can cast a spell."""
        spell_key = spell_name.lower()
        if spell_key not in SPELLS:
            return False, "Unknown spell"

        spell = SPELLS[spell_key]
        spell_level = spell.get_level_for_class(self.class_name.lower())

        if spell_level is None:
            return False, f"{spell.name} is not on your spell list"

        if self.spell_slots.get_remaining(spell_level) <= 0:
            return False, f"No {spell_level}-level spell slots remaining"

        return True, "OK"

    def cast_spell(
        self,
        spell_name: str,
        target_name: str = "",
    ) -> dict[str, Any]:
        """Cast a spell and return the result."""
        spell_key = spell_name.lower()
        can_cast, reason = self.can_cast(spell_key)

        if not can_cast:
            return {"success": False, "message": reason}

        spell = SPELLS[spell_key]
        spell_level = spell.get_level_for_class(self.class_name.lower())

        # Use the spell slot
        self.spell_slots.use_slot(spell_level)

        result = {
            "success": True,
            "spell": spell.name,
            "level": spell_level,
            "target": target_name,
            "save_dc": self.get_spell_dc(spell_level) if spell.saving_throw != "None" else None,
            "save_type": spell.saving_throw,
            "damage": 0,
            "healing": 0,
            "message": f"Cast {spell.name}",
        }

        # Calculate damage if applicable
        if spell.damage_dice:
            # Most damage spells scale with caster level
            if "per level" in spell.description.lower() or spell_level > 0:
                num_dice = min(self.caster_level, 10)  # Usually capped at 10
            else:
                num_dice = 1

            damage_roll = self.roller.roll(f"{num_dice}{spell.damage_dice.lstrip('0123456789')}")
            result["damage"] = damage_roll.total
            result["damage_type"] = spell.damage_type
            result["message"] = f"Cast {spell.name} for {damage_roll.total} {spell.damage_type} damage"

        # Calculate healing if applicable
        if spell.heal_dice:
            max_bonus = 5 + (spell_level - 1) * 5  # +5/+10/+15 etc
            bonus = min(self.caster_level, max_bonus)
            heal_roll = self.roller.roll(spell.heal_dice)
            result["healing"] = heal_roll.total + bonus
            result["message"] = f"Cast {spell.name} healing {result['healing']} HP"

        return result

    def get_available_spells(self) -> dict[int, list[Spell]]:
        """Get spells available to cast, organized by level."""
        available = {}

        for spell in SPELLS.values():
            spell_level = spell.get_level_for_class(self.class_name.lower())
            if spell_level is not None:
                if self.spell_slots.get_remaining(spell_level) > 0:
                    if spell_level not in available:
                        available[spell_level] = []
                    available[spell_level].append(spell)

        return available

    def get_slots_display(self) -> str:
        """Get a display string for current spell slots."""
        parts = []
        for level in sorted(self.spell_slots.max_slots.keys()):
            remaining = self.spell_slots.get_remaining(level)
            max_s = self.spell_slots.max_slots[level]
            parts.append(f"L{level}: {remaining}/{max_s}")
        return " | ".join(parts)
