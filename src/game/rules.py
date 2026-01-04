"""Pathfinder 1e rules engine for skill checks, saves, and attacks."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .dice import DiceResult, DiceRoller


class CheckType(Enum):
    """Types of d20 checks."""

    ATTACK = "attack"
    SKILL = "skill"
    SAVING_THROW = "saving_throw"
    ABILITY = "ability"
    CASTER_LEVEL = "caster_level"
    COMBAT_MANEUVER = "combat_maneuver"
    INITIATIVE = "initiative"


class DamageType(Enum):
    """Types of damage."""

    BLUDGEONING = "bludgeoning"
    PIERCING = "piercing"
    SLASHING = "slashing"
    FIRE = "fire"
    COLD = "cold"
    ELECTRICITY = "electricity"
    ACID = "acid"
    SONIC = "sonic"
    FORCE = "force"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NONLETHAL = "nonlethal"


@dataclass
class CheckResult:
    """Result of a d20 check."""

    check_type: CheckType
    roll: DiceResult
    modifier: int
    dc: int | None
    total: int
    success: bool | None  # None if no DC provided
    natural_20: bool
    natural_1: bool
    margin: int | None  # How much over/under the DC

    def __str__(self) -> str:
        """Human-readable result string."""
        result_str = f"{self.check_type.value.title()}: {self.roll.rolls[0]}"

        if self.modifier >= 0:
            result_str += f"+{self.modifier}"
        else:
            result_str += str(self.modifier)

        result_str += f" = {self.total}"

        if self.dc is not None:
            result_str += f" vs DC {self.dc}"
            if self.success:
                result_str += " (SUCCESS)"
            else:
                result_str += " (FAILURE)"

        if self.natural_20:
            result_str += " [NAT 20]"
        elif self.natural_1:
            result_str += " [NAT 1]"

        return result_str


@dataclass
class AttackResult:
    """Result of an attack roll."""

    attack_roll: CheckResult
    hit: bool
    critical_threat: bool
    critical_confirmed: bool
    confirmation_roll: CheckResult | None
    damage: DiceResult | None
    damage_type: DamageType
    total_damage: int

    def __str__(self) -> str:
        """Human-readable attack result."""
        if not self.hit:
            return f"Attack: {self.attack_roll.total} - MISS"

        result = f"Attack: {self.attack_roll.total} - HIT"

        if self.critical_confirmed:
            result += " (CRITICAL!)"
        elif self.critical_threat:
            result += " (threat not confirmed)"

        if self.damage:
            result += f" for {self.total_damage} {self.damage_type.value} damage"

        return result


class RulesEngine:
    """Pathfinder 1e rules engine."""

    # Difficulty class guidelines
    DC_TRIVIAL = 5
    DC_EASY = 10
    DC_AVERAGE = 15
    DC_TOUGH = 20
    DC_CHALLENGING = 25
    DC_HEROIC = 30
    DC_EPIC = 35

    # Standard conditions and their effects
    CONDITIONS = {
        "blinded": {
            "ac_penalty": -2,
            "attack_penalty": -2,
            "loses_dex_to_ac": True,
            "description": "Cannot see. -2 to AC, loses Dex to AC.",
        },
        "confused": {
            "description": "Acts randomly each round.",
        },
        "dazed": {
            "description": "Can take no actions.",
        },
        "deafened": {
            "initiative_penalty": -4,
            "description": "-4 initiative, 20% spell failure for verbal spells.",
        },
        "entangled": {
            "attack_penalty": -2,
            "dex_penalty": -4,
            "description": "-2 attack, -4 Dex, cannot run or charge.",
        },
        "exhausted": {
            "str_penalty": -6,
            "dex_penalty": -6,
            "description": "-6 Str, -6 Dex, cannot run or charge.",
        },
        "fatigued": {
            "str_penalty": -2,
            "dex_penalty": -2,
            "description": "-2 Str, -2 Dex, cannot run or charge.",
        },
        "frightened": {
            "attack_penalty": -2,
            "save_penalty": -2,
            "skill_penalty": -2,
            "description": "-2 to attacks, saves, skill checks. Must flee from source of fear.",
        },
        "grappled": {
            "dex_penalty": -4,
            "attack_penalty": -2,
            "description": "-4 Dex, -2 attack, cannot move, cannot cast unless concentration check.",
        },
        "helpless": {
            "dex_score": 0,
            "description": "Dex 0, can be coup de graced.",
        },
        "invisible": {
            "attack_bonus": 2,
            "description": "+2 attack, target cannot use Dex vs attacker.",
        },
        "nauseated": {
            "description": "Can only take a single move action.",
        },
        "panicked": {
            "attack_penalty": -2,
            "save_penalty": -2,
            "description": "-2 to attacks, saves. Must flee, drops held items.",
        },
        "paralyzed": {
            "dex_score": 0,
            "str_score": 0,
            "description": "Cannot move or act. Str and Dex 0.",
        },
        "prone": {
            "attack_penalty": -4,
            "ac_penalty_melee": -4,
            "ac_bonus_ranged": 4,
            "description": "-4 melee attack, -4 AC vs melee, +4 AC vs ranged.",
        },
        "shaken": {
            "attack_penalty": -2,
            "save_penalty": -2,
            "skill_penalty": -2,
            "description": "-2 to attacks, saves, skill checks.",
        },
        "sickened": {
            "attack_penalty": -2,
            "save_penalty": -2,
            "skill_penalty": -2,
            "damage_penalty": -2,
            "description": "-2 to attacks, saves, skill checks, damage.",
        },
        "staggered": {
            "description": "Can take only a single move or standard action.",
        },
        "stunned": {
            "ac_penalty": -2,
            "loses_dex_to_ac": True,
            "description": "Cannot act, -2 AC, loses Dex to AC.",
        },
        "unconscious": {
            "description": "Cannot act, helpless.",
        },
    }

    def __init__(self):
        """Initialize the rules engine."""
        self.roller = DiceRoller()

    def make_check(
        self,
        check_type: CheckType,
        modifier: int,
        dc: int | None = None,
    ) -> CheckResult:
        """Make a d20 check.

        Args:
            check_type: Type of check
            modifier: Total modifier to the roll
            dc: Difficulty class (optional)

        Returns:
            CheckResult with all details
        """
        roll = self.roller.roll("1d20")
        natural = roll.rolls[0]
        total = natural + modifier

        natural_20 = natural == 20
        natural_1 = natural == 1

        success = None
        margin = None

        if dc is not None:
            # Natural 20 always succeeds for attacks, not for skills/saves
            if check_type == CheckType.ATTACK:
                success = natural_20 or (total >= dc and not natural_1)
            else:
                success = total >= dc

            margin = total - dc

        return CheckResult(
            check_type=check_type,
            roll=roll,
            modifier=modifier,
            dc=dc,
            total=total,
            success=success,
            natural_20=natural_20,
            natural_1=natural_1,
            margin=margin,
        )

    def make_attack(
        self,
        attack_bonus: int,
        target_ac: int,
        damage_dice: str,
        damage_bonus: int = 0,
        damage_type: DamageType = DamageType.SLASHING,
        critical_range: int = 20,
        critical_multiplier: int = 2,
    ) -> AttackResult:
        """Make an attack roll with damage.

        Args:
            attack_bonus: Total attack bonus
            target_ac: Target's armor class
            damage_dice: Damage dice notation (e.g., "1d8")
            damage_bonus: Bonus damage to add
            damage_type: Type of damage
            critical_range: Minimum roll to threaten critical (default 20)
            critical_multiplier: Critical damage multiplier

        Returns:
            AttackResult with all details
        """
        # Attack roll
        attack = self.make_check(CheckType.ATTACK, attack_bonus, target_ac)

        hit = attack.success or False
        critical_threat = attack.natural_20 or (attack.roll.rolls[0] >= critical_range and hit)
        critical_confirmed = False
        confirmation_roll = None
        damage = None
        total_damage = 0

        # Automatic miss on natural 1
        if attack.natural_1:
            hit = False
            critical_threat = False

        # Confirm critical if threatened
        if critical_threat and hit:
            confirmation_roll = self.make_check(CheckType.ATTACK, attack_bonus, target_ac)
            critical_confirmed = confirmation_roll.success or False

        # Roll damage if hit
        if hit:
            damage = self.roller.roll(damage_dice)
            base_damage = damage.total + damage_bonus

            if critical_confirmed:
                # Roll additional damage dice for critical
                crit_dice = self.roller.roll(damage_dice)
                for _ in range(critical_multiplier - 2):  # -1 for base, -1 for first crit roll
                    extra = self.roller.roll(damage_dice)
                    crit_dice.rolls.extend(extra.rolls)
                    crit_dice.kept.extend(extra.kept)

                total_damage = base_damage * critical_multiplier
            else:
                total_damage = max(1, base_damage)

        return AttackResult(
            attack_roll=attack,
            hit=hit,
            critical_threat=critical_threat,
            critical_confirmed=critical_confirmed,
            confirmation_roll=confirmation_roll,
            damage=damage,
            damage_type=damage_type,
            total_damage=total_damage,
        )

    def make_saving_throw(
        self,
        save_type: str,
        base_save: int,
        ability_modifier: int,
        dc: int,
        misc_modifier: int = 0,
    ) -> CheckResult:
        """Make a saving throw.

        Args:
            save_type: "fortitude", "reflex", or "will"
            base_save: Base save from class
            ability_modifier: Relevant ability modifier
            dc: Save DC
            misc_modifier: Other modifiers

        Returns:
            CheckResult
        """
        total_modifier = base_save + ability_modifier + misc_modifier
        return self.make_check(CheckType.SAVING_THROW, total_modifier, dc)

    def make_skill_check(
        self,
        ranks: int,
        ability_modifier: int,
        is_class_skill: bool,
        dc: int,
        misc_modifier: int = 0,
        take_10: bool = False,
        take_20: bool = False,
    ) -> CheckResult:
        """Make a skill check.

        Args:
            ranks: Skill ranks
            ability_modifier: Governing ability modifier
            is_class_skill: Whether this is a class skill
            dc: Difficulty class
            misc_modifier: Other modifiers
            take_10: Use 10 instead of rolling
            take_20: Use 20 instead of rolling

        Returns:
            CheckResult
        """
        total_modifier = ranks + ability_modifier + misc_modifier
        if is_class_skill and ranks > 0:
            total_modifier += 3

        if take_20:
            # Simulated result for taking 20
            return CheckResult(
                check_type=CheckType.SKILL,
                roll=DiceResult("1d20", [20], [20], [], 0, 20),
                modifier=total_modifier,
                dc=dc,
                total=20 + total_modifier,
                success=20 + total_modifier >= dc,
                natural_20=True,
                natural_1=False,
                margin=20 + total_modifier - dc,
            )
        elif take_10:
            return CheckResult(
                check_type=CheckType.SKILL,
                roll=DiceResult("1d20", [10], [10], [], 0, 10),
                modifier=total_modifier,
                dc=dc,
                total=10 + total_modifier,
                success=10 + total_modifier >= dc,
                natural_20=False,
                natural_1=False,
                margin=10 + total_modifier - dc,
            )

        return self.make_check(CheckType.SKILL, total_modifier, dc)

    def make_combat_maneuver(
        self,
        cmb: int,
        target_cmd: int,
    ) -> CheckResult:
        """Make a combat maneuver check.

        Args:
            cmb: Combat Maneuver Bonus
            target_cmd: Target's Combat Maneuver Defense

        Returns:
            CheckResult
        """
        return self.make_check(CheckType.COMBAT_MANEUVER, cmb, target_cmd)

    def roll_initiative(self, dex_modifier: int, misc_modifier: int = 0) -> CheckResult:
        """Roll initiative.

        Args:
            dex_modifier: Dexterity modifier
            misc_modifier: Other initiative modifiers

        Returns:
            CheckResult (no DC for initiative)
        """
        return self.make_check(
            CheckType.INITIATIVE,
            dex_modifier + misc_modifier,
            dc=None,
        )

    def calculate_spell_dc(
        self,
        spell_level: int,
        casting_ability_modifier: int,
        misc_modifier: int = 0,
    ) -> int:
        """Calculate the save DC for a spell.

        Args:
            spell_level: Level of the spell
            casting_ability_modifier: Casting ability modifier
            misc_modifier: Other DC modifiers (spell focus, etc.)

        Returns:
            Spell save DC
        """
        return 10 + spell_level + casting_ability_modifier + misc_modifier

    def get_condition_modifiers(self, conditions: list[str]) -> dict[str, int]:
        """Get total modifiers from active conditions.

        Args:
            conditions: List of condition names

        Returns:
            Dict of modifier types to total modifiers
        """
        modifiers = {
            "attack": 0,
            "ac": 0,
            "saves": 0,
            "skills": 0,
            "damage": 0,
            "str": 0,
            "dex": 0,
        }

        for condition in conditions:
            cond_data = self.CONDITIONS.get(condition.lower(), {})

            modifiers["attack"] += cond_data.get("attack_penalty", 0)
            modifiers["attack"] += cond_data.get("attack_bonus", 0)
            modifiers["ac"] += cond_data.get("ac_penalty", 0)
            modifiers["saves"] += cond_data.get("save_penalty", 0)
            modifiers["skills"] += cond_data.get("skill_penalty", 0)
            modifiers["damage"] += cond_data.get("damage_penalty", 0)
            modifiers["str"] += cond_data.get("str_penalty", 0)
            modifiers["dex"] += cond_data.get("dex_penalty", 0)

        return modifiers
