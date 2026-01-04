"""Condition and status effect management for Pathfinder 1e."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConditionCategory(Enum):
    """Categories of conditions."""

    PHYSICAL = "physical"
    MENTAL = "mental"
    MAGICAL = "magical"
    MOVEMENT = "movement"
    COMBAT = "combat"


@dataclass
class ConditionEffect:
    """Effects of a condition on a character."""

    # Ability score modifiers
    str_modifier: int = 0
    dex_modifier: int = 0
    con_modifier: int = 0
    int_modifier: int = 0
    wis_modifier: int = 0
    cha_modifier: int = 0

    # Combat modifiers
    attack_modifier: int = 0
    damage_modifier: int = 0
    ac_modifier: int = 0
    touch_ac_modifier: int = 0
    flat_footed_ac_modifier: int = 0

    # Save modifiers
    fortitude_modifier: int = 0
    reflex_modifier: int = 0
    will_modifier: int = 0
    all_saves_modifier: int = 0

    # Skill modifiers
    all_skills_modifier: int = 0
    specific_skills: dict[str, int] = field(default_factory=dict)

    # Speed modifiers
    speed_modifier: int = 0
    speed_multiplier: float = 1.0
    cannot_run: bool = False
    cannot_charge: bool = False

    # Special flags
    loses_dex_to_ac: bool = False
    cannot_act: bool = False
    helpless: bool = False
    flat_footed: bool = False
    invisible: bool = False
    can_only_take_move_action: bool = False
    can_only_take_standard_action: bool = False


@dataclass
class Condition:
    """A status condition with all its effects."""

    name: str
    category: ConditionCategory
    description: str
    effects: ConditionEffect
    duration: int | None = None  # Rounds, None = permanent until removed
    save_to_end: str | None = None  # Save type to end condition each round
    save_dc: int | None = None
    stackable: bool = False
    ends_on_damage: bool = False
    source: str = ""


class ConditionManager:
    """Manages conditions for a character or combat encounter."""

    # Standard PF1e conditions
    STANDARD_CONDITIONS: dict[str, Condition] = {
        "blinded": Condition(
            name="Blinded",
            category=ConditionCategory.PHYSICAL,
            description="Cannot see. -2 to AC, loses Dex to AC. All checks and activities that rely on vision fail. Opponents have total concealment.",
            effects=ConditionEffect(
                ac_modifier=-2,
                loses_dex_to_ac=True,
            ),
        ),
        "confused": Condition(
            name="Confused",
            category=ConditionCategory.MENTAL,
            description="Cannot determine actions. Roll d% each round to determine behavior.",
            effects=ConditionEffect(),
        ),
        "cowering": Condition(
            name="Cowering",
            category=ConditionCategory.MENTAL,
            description="Frozen in fear. Loses Dex to AC, -2 AC.",
            effects=ConditionEffect(
                ac_modifier=-2,
                loses_dex_to_ac=True,
                cannot_act=True,
            ),
        ),
        "dazed": Condition(
            name="Dazed",
            category=ConditionCategory.MENTAL,
            description="Unable to act normally. Can take no actions but has no penalty to AC.",
            effects=ConditionEffect(cannot_act=True),
        ),
        "dazzled": Condition(
            name="Dazzled",
            category=ConditionCategory.PHYSICAL,
            description="Unable to see well because of overstimulation of the eyes. -1 attack, -1 sight-based Perception.",
            effects=ConditionEffect(
                attack_modifier=-1,
                specific_skills={"Perception": -1},
            ),
        ),
        "deafened": Condition(
            name="Deafened",
            category=ConditionCategory.PHYSICAL,
            description="Cannot hear. -4 initiative, 20% spell failure for verbal spells.",
            effects=ConditionEffect(
                specific_skills={"Perception": -4},
            ),
        ),
        "disabled": Condition(
            name="Disabled",
            category=ConditionCategory.PHYSICAL,
            description="At exactly 0 HP. Can only take a single move or standard action.",
            effects=ConditionEffect(can_only_take_standard_action=True),
        ),
        "dying": Condition(
            name="Dying",
            category=ConditionCategory.PHYSICAL,
            description="At negative HP and not stabilized. Unconscious and dying.",
            effects=ConditionEffect(
                helpless=True,
                cannot_act=True,
            ),
        ),
        "energy_drained": Condition(
            name="Energy Drained",
            category=ConditionCategory.MAGICAL,
            description="One or more negative levels. -1 per level to attacks, saves, skills, and effective level.",
            effects=ConditionEffect(),
            stackable=True,
        ),
        "entangled": Condition(
            name="Entangled",
            category=ConditionCategory.MOVEMENT,
            description="Ensnared. -2 attack, -4 Dex. Cannot run or charge.",
            effects=ConditionEffect(
                attack_modifier=-2,
                dex_modifier=-4,
                cannot_run=True,
                cannot_charge=True,
            ),
        ),
        "exhausted": Condition(
            name="Exhausted",
            category=ConditionCategory.PHYSICAL,
            description="Severe fatigue. -6 Str, -6 Dex. Cannot run or charge. Rest 1 hour to become fatigued.",
            effects=ConditionEffect(
                str_modifier=-6,
                dex_modifier=-6,
                cannot_run=True,
                cannot_charge=True,
            ),
        ),
        "fascinated": Condition(
            name="Fascinated",
            category=ConditionCategory.MENTAL,
            description="Entranced by something. -4 skill checks made as reactions. Threats end condition.",
            effects=ConditionEffect(all_skills_modifier=-4),
            ends_on_damage=True,
        ),
        "fatigued": Condition(
            name="Fatigued",
            category=ConditionCategory.PHYSICAL,
            description="Tired. -2 Str, -2 Dex. Cannot run or charge.",
            effects=ConditionEffect(
                str_modifier=-2,
                dex_modifier=-2,
                cannot_run=True,
                cannot_charge=True,
            ),
        ),
        "flat-footed": Condition(
            name="Flat-Footed",
            category=ConditionCategory.COMBAT,
            description="Not yet acted in combat. Cannot use Dex bonus to AC, cannot make AoO.",
            effects=ConditionEffect(
                flat_footed=True,
                loses_dex_to_ac=True,
            ),
        ),
        "frightened": Condition(
            name="Frightened",
            category=ConditionCategory.MENTAL,
            description="Fear. -2 attacks, saves, skills. Must flee from fear source.",
            effects=ConditionEffect(
                attack_modifier=-2,
                all_saves_modifier=-2,
                all_skills_modifier=-2,
            ),
        ),
        "grappled": Condition(
            name="Grappled",
            category=ConditionCategory.MOVEMENT,
            description="Held by an opponent. Cannot move, -4 Dex, -2 attack. Cannot cast with somatic components.",
            effects=ConditionEffect(
                dex_modifier=-4,
                attack_modifier=-2,
            ),
        ),
        "helpless": Condition(
            name="Helpless",
            category=ConditionCategory.COMBAT,
            description="Paralyzed, held, bound, sleeping, unconscious, or otherwise immobile. Effective Dex 0.",
            effects=ConditionEffect(
                helpless=True,
                dex_modifier=-100,  # Effectively 0
            ),
        ),
        "incorporeal": Condition(
            name="Incorporeal",
            category=ConditionCategory.MAGICAL,
            description="No physical body. Immune to nonmagical attacks. 50% chance to ignore magic damage.",
            effects=ConditionEffect(),
        ),
        "invisible": Condition(
            name="Invisible",
            category=ConditionCategory.MAGICAL,
            description="Cannot be seen. +2 attack, target loses Dex to AC. 50% miss chance against you.",
            effects=ConditionEffect(
                attack_modifier=2,
                invisible=True,
            ),
        ),
        "nauseated": Condition(
            name="Nauseated",
            category=ConditionCategory.PHYSICAL,
            description="Experiencing stomach distress. Can only take a single move action.",
            effects=ConditionEffect(can_only_take_move_action=True),
        ),
        "panicked": Condition(
            name="Panicked",
            category=ConditionCategory.MENTAL,
            description="Extreme fear. -2 saves. Must drop held items and flee. Cowers if cornered.",
            effects=ConditionEffect(
                all_saves_modifier=-2,
            ),
        ),
        "paralyzed": Condition(
            name="Paralyzed",
            category=ConditionCategory.PHYSICAL,
            description="Frozen, unable to move or act. Effective Str and Dex 0. Helpless.",
            effects=ConditionEffect(
                helpless=True,
                cannot_act=True,
            ),
        ),
        "petrified": Condition(
            name="Petrified",
            category=ConditionCategory.MAGICAL,
            description="Turned to stone. Considered unconscious. Weight x10.",
            effects=ConditionEffect(
                helpless=True,
                cannot_act=True,
            ),
        ),
        "pinned": Condition(
            name="Pinned",
            category=ConditionCategory.MOVEMENT,
            description="Held immobile. Flat-footed, -4 AC against melee, no Dex to AC.",
            effects=ConditionEffect(
                ac_modifier=-4,
                flat_footed=True,
                loses_dex_to_ac=True,
            ),
        ),
        "prone": Condition(
            name="Prone",
            category=ConditionCategory.MOVEMENT,
            description="Lying on the ground. -4 melee attack. -4 AC vs melee, +4 AC vs ranged.",
            effects=ConditionEffect(
                attack_modifier=-4,  # Melee only
                ac_modifier=-4,  # vs melee
            ),
        ),
        "shaken": Condition(
            name="Shaken",
            category=ConditionCategory.MENTAL,
            description="Minor fear. -2 attacks, saves, and skill checks.",
            effects=ConditionEffect(
                attack_modifier=-2,
                all_saves_modifier=-2,
                all_skills_modifier=-2,
            ),
        ),
        "sickened": Condition(
            name="Sickened",
            category=ConditionCategory.PHYSICAL,
            description="Mildly ill. -2 attacks, damage, saves, skills, and ability checks.",
            effects=ConditionEffect(
                attack_modifier=-2,
                damage_modifier=-2,
                all_saves_modifier=-2,
                all_skills_modifier=-2,
            ),
        ),
        "stable": Condition(
            name="Stable",
            category=ConditionCategory.PHYSICAL,
            description="No longer dying, but still unconscious.",
            effects=ConditionEffect(
                helpless=True,
                cannot_act=True,
            ),
        ),
        "staggered": Condition(
            name="Staggered",
            category=ConditionCategory.PHYSICAL,
            description="Barely able to act. Can only take a single move or standard action.",
            effects=ConditionEffect(can_only_take_standard_action=True),
        ),
        "stunned": Condition(
            name="Stunned",
            category=ConditionCategory.COMBAT,
            description="Reeling. Cannot act, drops held items, -2 AC, loses Dex to AC.",
            effects=ConditionEffect(
                cannot_act=True,
                ac_modifier=-2,
                loses_dex_to_ac=True,
            ),
        ),
        "unconscious": Condition(
            name="Unconscious",
            category=ConditionCategory.PHYSICAL,
            description="Knocked out. Helpless.",
            effects=ConditionEffect(
                helpless=True,
                cannot_act=True,
            ),
        ),
    }

    def __init__(self):
        """Initialize condition manager."""
        self.active_conditions: dict[str, Condition] = {}
        self.condition_durations: dict[str, int] = {}  # Remaining rounds

    def add_condition(
        self,
        condition_name: str,
        duration: int | None = None,
        source: str = "",
    ) -> Condition | None:
        """Add a condition.

        Args:
            condition_name: Name of condition to add
            duration: Duration in rounds (None = permanent)
            source: Source of the condition

        Returns:
            The Condition added, or None if not found
        """
        condition_key = condition_name.lower().replace(" ", "_").replace("-", "_")

        if condition_key not in self.STANDARD_CONDITIONS:
            return None

        condition = self.STANDARD_CONDITIONS[condition_key]

        # Check if already present and not stackable
        if condition_key in self.active_conditions and not condition.stackable:
            # Refresh duration if new duration is longer
            if duration is not None:
                current = self.condition_durations.get(condition_key, 0)
                if duration > current:
                    self.condition_durations[condition_key] = duration
            return condition

        self.active_conditions[condition_key] = condition
        if duration is not None:
            self.condition_durations[condition_key] = duration

        return condition

    def remove_condition(self, condition_name: str) -> bool:
        """Remove a condition.

        Args:
            condition_name: Name of condition to remove

        Returns:
            True if removed, False if not present
        """
        condition_key = condition_name.lower().replace(" ", "_").replace("-", "_")

        if condition_key in self.active_conditions:
            del self.active_conditions[condition_key]
            if condition_key in self.condition_durations:
                del self.condition_durations[condition_key]
            return True

        return False

    def has_condition(self, condition_name: str) -> bool:
        """Check if a condition is active.

        Args:
            condition_name: Name of condition

        Returns:
            True if condition is active
        """
        condition_key = condition_name.lower().replace(" ", "_").replace("-", "_")
        return condition_key in self.active_conditions

    def advance_round(self) -> list[str]:
        """Advance time by one round, reducing durations.

        Returns:
            List of conditions that expired
        """
        expired = []

        for condition_key in list(self.condition_durations.keys()):
            self.condition_durations[condition_key] -= 1
            if self.condition_durations[condition_key] <= 0:
                expired.append(condition_key)
                self.remove_condition(condition_key)

        return expired

    def get_total_effects(self) -> ConditionEffect:
        """Calculate combined effects of all active conditions.

        Returns:
            Combined ConditionEffect
        """
        combined = ConditionEffect()

        for condition in self.active_conditions.values():
            effects = condition.effects

            combined.str_modifier += effects.str_modifier
            combined.dex_modifier += effects.dex_modifier
            combined.con_modifier += effects.con_modifier
            combined.int_modifier += effects.int_modifier
            combined.wis_modifier += effects.wis_modifier
            combined.cha_modifier += effects.cha_modifier

            combined.attack_modifier += effects.attack_modifier
            combined.damage_modifier += effects.damage_modifier
            combined.ac_modifier += effects.ac_modifier

            combined.fortitude_modifier += effects.fortitude_modifier
            combined.reflex_modifier += effects.reflex_modifier
            combined.will_modifier += effects.will_modifier
            combined.all_saves_modifier += effects.all_saves_modifier

            combined.all_skills_modifier += effects.all_skills_modifier
            combined.speed_modifier += effects.speed_modifier

            # Flags - any true makes combined true
            combined.loses_dex_to_ac = combined.loses_dex_to_ac or effects.loses_dex_to_ac
            combined.cannot_act = combined.cannot_act or effects.cannot_act
            combined.helpless = combined.helpless or effects.helpless
            combined.flat_footed = combined.flat_footed or effects.flat_footed
            combined.invisible = combined.invisible or effects.invisible
            combined.cannot_run = combined.cannot_run or effects.cannot_run
            combined.cannot_charge = combined.cannot_charge or effects.cannot_charge

        return combined

    def get_active_condition_names(self) -> list[str]:
        """Get names of all active conditions.

        Returns:
            List of condition names
        """
        return [c.name for c in self.active_conditions.values()]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "active": list(self.active_conditions.keys()),
            "durations": self.condition_durations.copy(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConditionManager":
        """Create from dictionary data."""
        manager = cls()
        for condition_key in data.get("active", []):
            duration = data.get("durations", {}).get(condition_key)
            manager.add_condition(condition_key, duration)
        return manager
