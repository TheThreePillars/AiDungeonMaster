"""Dice rolling engine with full notation support for Pathfinder 1e."""

import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class RollType(Enum):
    """Type of roll modification."""

    NORMAL = "normal"
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"
    DROP_LOWEST = "drop_lowest"
    DROP_HIGHEST = "drop_highest"
    KEEP_HIGHEST = "keep_highest"
    KEEP_LOWEST = "keep_lowest"


@dataclass
class DiceResult:
    """Result of a dice roll with full details."""

    notation: str
    rolls: list[int]
    kept: list[int]
    dropped: list[int]
    modifier: int
    total: int
    roll_type: RollType = RollType.NORMAL
    is_critical: bool = False
    is_fumble: bool = False
    natural_roll: int | None = None  # For d20 rolls, the unmodified result

    def __str__(self) -> str:
        """Human-readable representation of the roll."""
        parts = [f"{self.notation}:"]

        if self.dropped:
            all_rolls = f"[{', '.join(str(r) for r in self.rolls)}]"
            kept_rolls = f"kept [{', '.join(str(r) for r in self.kept)}]"
            parts.append(f"{all_rolls} {kept_rolls}")
        else:
            parts.append(f"[{', '.join(str(r) for r in self.kept)}]")

        if self.modifier != 0:
            sign = "+" if self.modifier > 0 else ""
            parts.append(f"{sign}{self.modifier}")

        parts.append(f"= {self.total}")

        if self.is_critical:
            parts.append("(CRITICAL!)")
        elif self.is_fumble:
            parts.append("(Fumble)")

        return " ".join(parts)


@dataclass
class DicePool:
    """Represents a pool of dice to roll."""

    count: int
    sides: int
    modifier: int = 0
    roll_type: RollType = RollType.NORMAL
    drop_count: int = 0
    keep_count: int | None = None
    critical_range: tuple[int, int] = (20, 20)  # Min and max for critical threat


class DiceRoller:
    """Dice rolling engine with notation parsing."""

    # Regex pattern for dice notation
    # Matches: 2d6, 1d20+5, 4d6-2, 2d20 advantage, 4d6 drop lowest, etc.
    DICE_PATTERN = re.compile(
        r"^(\d+)?d(\d+)"  # NdX (N is optional, defaults to 1)
        r"([+-]\d+)?"  # Optional modifier
        r"(?:\s+(adv|advantage|dis|disadvantage))?"  # Advantage/disadvantage
        r"(?:\s+drop\s+(lowest|highest)(?:\s+(\d+))?)?"  # Drop lowest/highest
        r"(?:\s+keep\s+(lowest|highest)(?:\s+(\d+))?)?"  # Keep lowest/highest
        r"$",
        re.IGNORECASE,
    )

    def __init__(self, rng: random.Random | None = None):
        """Initialize the dice roller.

        Args:
            rng: Random number generator instance. Uses default if not provided.
        """
        self.rng = rng or random.Random()

    def seed(self, seed: int) -> None:
        """Seed the random number generator for reproducible rolls.

        Args:
            seed: Seed value
        """
        self.rng.seed(seed)

    def parse_notation(self, notation: str) -> DicePool:
        """Parse dice notation string into a DicePool.

        Args:
            notation: Dice notation string (e.g., "2d6+4", "1d20 advantage")

        Returns:
            DicePool with parsed parameters

        Raises:
            ValueError: If notation is invalid
        """
        notation = notation.strip().lower()
        match = self.DICE_PATTERN.match(notation)

        if not match:
            raise ValueError(f"Invalid dice notation: {notation}")

        count = int(match.group(1)) if match.group(1) else 1
        sides = int(match.group(2))
        modifier = int(match.group(3)) if match.group(3) else 0

        # Determine roll type and modifiers
        roll_type = RollType.NORMAL
        drop_count = 0
        keep_count = None

        # Advantage/disadvantage
        adv_dis = match.group(4)
        if adv_dis:
            if adv_dis in ("adv", "advantage"):
                roll_type = RollType.ADVANTAGE
            else:
                roll_type = RollType.DISADVANTAGE

        # Drop lowest/highest
        drop_type = match.group(5)
        if drop_type:
            drop_count = int(match.group(6)) if match.group(6) else 1
            if drop_type == "lowest":
                roll_type = RollType.DROP_LOWEST
            else:
                roll_type = RollType.DROP_HIGHEST

        # Keep lowest/highest
        keep_type = match.group(7)
        if keep_type:
            keep_count = int(match.group(8)) if match.group(8) else 1
            if keep_type == "highest":
                roll_type = RollType.KEEP_HIGHEST
            else:
                roll_type = RollType.KEEP_LOWEST

        return DicePool(
            count=count,
            sides=sides,
            modifier=modifier,
            roll_type=roll_type,
            drop_count=drop_count,
            keep_count=keep_count,
        )

    def roll_pool(self, pool: DicePool) -> DiceResult:
        """Roll a dice pool and return the result.

        Args:
            pool: DicePool to roll

        Returns:
            DiceResult with full roll details
        """
        # Handle advantage/disadvantage (roll twice, keep best/worst)
        if pool.roll_type == RollType.ADVANTAGE:
            rolls = [self.rng.randint(1, pool.sides) for _ in range(2)]
            kept = [max(rolls)]
            dropped = [min(rolls)]
        elif pool.roll_type == RollType.DISADVANTAGE:
            rolls = [self.rng.randint(1, pool.sides) for _ in range(2)]
            kept = [min(rolls)]
            dropped = [max(rolls)]
        else:
            # Standard roll
            rolls = [self.rng.randint(1, pool.sides) for _ in range(pool.count)]
            sorted_rolls = sorted(rolls)

            if pool.roll_type == RollType.DROP_LOWEST:
                dropped = sorted_rolls[: pool.drop_count]
                kept = sorted_rolls[pool.drop_count :]
            elif pool.roll_type == RollType.DROP_HIGHEST:
                dropped = sorted_rolls[-pool.drop_count :]
                kept = sorted_rolls[: -pool.drop_count] if pool.drop_count else sorted_rolls
            elif pool.roll_type == RollType.KEEP_HIGHEST and pool.keep_count:
                kept = sorted_rolls[-pool.keep_count :]
                dropped = sorted_rolls[: -pool.keep_count] if pool.keep_count < len(sorted_rolls) else []
            elif pool.roll_type == RollType.KEEP_LOWEST and pool.keep_count:
                kept = sorted_rolls[: pool.keep_count]
                dropped = sorted_rolls[pool.keep_count :]
            else:
                kept = rolls
                dropped = []

        total = sum(kept) + pool.modifier

        # Determine natural roll for d20s (for critical/fumble detection)
        natural_roll = None
        is_critical = False
        is_fumble = False

        if pool.sides == 20 and len(kept) == 1:
            natural_roll = kept[0]
            is_critical = natural_roll >= pool.critical_range[0]
            is_fumble = natural_roll == 1

        # Reconstruct notation string
        notation_parts = [f"{pool.count}d{pool.sides}"]
        if pool.modifier > 0:
            notation_parts.append(f"+{pool.modifier}")
        elif pool.modifier < 0:
            notation_parts.append(str(pool.modifier))

        if pool.roll_type == RollType.ADVANTAGE:
            notation_parts.append(" advantage")
        elif pool.roll_type == RollType.DISADVANTAGE:
            notation_parts.append(" disadvantage")
        elif pool.roll_type == RollType.DROP_LOWEST:
            notation_parts.append(f" drop lowest {pool.drop_count}")
        elif pool.roll_type == RollType.DROP_HIGHEST:
            notation_parts.append(f" drop highest {pool.drop_count}")
        elif pool.roll_type == RollType.KEEP_HIGHEST and pool.keep_count:
            notation_parts.append(f" keep highest {pool.keep_count}")
        elif pool.roll_type == RollType.KEEP_LOWEST and pool.keep_count:
            notation_parts.append(f" keep lowest {pool.keep_count}")

        return DiceResult(
            notation="".join(notation_parts),
            rolls=rolls,
            kept=kept,
            dropped=dropped,
            modifier=pool.modifier,
            total=total,
            roll_type=pool.roll_type,
            is_critical=is_critical,
            is_fumble=is_fumble,
            natural_roll=natural_roll,
        )

    def roll(self, notation: str) -> DiceResult:
        """Parse and roll dice from notation string.

        Args:
            notation: Dice notation string

        Returns:
            DiceResult with full roll details
        """
        pool = self.parse_notation(notation)
        return self.roll_pool(pool)

    def roll_ability_scores(self, method: str = "4d6_drop_lowest") -> list[DiceResult]:
        """Roll a set of ability scores.

        Args:
            method: Rolling method - "4d6_drop_lowest", "3d6", "2d6+6"

        Returns:
            List of 6 DiceResults for ability scores
        """
        methods = {
            "4d6_drop_lowest": "4d6 drop lowest",
            "3d6": "3d6",
            "2d6+6": "2d6+6",
            "standard_array": None,  # Not rolled
        }

        if method not in methods:
            raise ValueError(f"Unknown ability score method: {method}")

        notation = methods[method]
        if notation is None:
            # Return standard array as fake "rolls"
            standard_array = [15, 14, 13, 12, 10, 8]
            return [
                DiceResult(
                    notation="standard array",
                    rolls=[score],
                    kept=[score],
                    dropped=[],
                    modifier=0,
                    total=score,
                )
                for score in standard_array
            ]

        return [self.roll(notation) for _ in range(6)]

    def roll_with_critical(
        self,
        attack_modifier: int,
        critical_range: tuple[int, int] = (20, 20),
    ) -> tuple[DiceResult, bool]:
        """Roll an attack with critical threat detection.

        Args:
            attack_modifier: Modifier to add to the roll
            critical_range: Range of natural rolls that threaten critical (min, max)

        Returns:
            Tuple of (DiceResult, is_critical_threat)
        """
        pool = DicePool(
            count=1,
            sides=20,
            modifier=attack_modifier,
            critical_range=critical_range,
        )
        result = self.roll_pool(pool)
        is_threat = result.natural_roll is not None and result.natural_roll >= critical_range[0]
        return result, is_threat

    def confirm_critical(
        self,
        attack_modifier: int,
        target_ac: int,
    ) -> tuple[DiceResult, bool]:
        """Roll to confirm a critical hit (Pathfinder 1e rule).

        Args:
            attack_modifier: Modifier to add to the confirmation roll
            target_ac: Target's armor class

        Returns:
            Tuple of (DiceResult, is_confirmed)
        """
        pool = DicePool(count=1, sides=20, modifier=attack_modifier)
        result = self.roll_pool(pool)
        is_confirmed = result.total >= target_ac
        return result, is_confirmed


# Convenience function for quick rolls
def roll(notation: str) -> DiceResult:
    """Quick roll function using default roller.

    Args:
        notation: Dice notation string

    Returns:
        DiceResult with full roll details
    """
    return DiceRoller().roll(notation)


# Convenience function for multiple expressions
def roll_multiple(notations: list[str]) -> list[DiceResult]:
    """Roll multiple dice expressions.

    Args:
        notations: List of dice notation strings

    Returns:
        List of DiceResults
    """
    roller = DiceRoller()
    return [roller.roll(n) for n in notations]
