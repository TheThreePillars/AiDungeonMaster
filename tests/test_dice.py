"""Tests for the dice rolling engine."""

import random

import pytest

from src.game.dice import DicePool, DiceResult, DiceRoller, RollType, roll, roll_multiple


class TestDiceRoller:
    """Test suite for DiceRoller class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.roller = DiceRoller()
        # Seed for reproducible tests
        self.roller.seed(42)

    def test_simple_roll(self):
        """Test basic dice notation parsing and rolling."""
        result = self.roller.roll("1d20")
        assert result.notation == "1d20"
        assert len(result.rolls) == 1
        assert len(result.kept) == 1
        assert len(result.dropped) == 0
        assert 1 <= result.total <= 20

    def test_multiple_dice(self):
        """Test rolling multiple dice."""
        result = self.roller.roll("3d6")
        assert result.notation == "3d6"
        assert len(result.rolls) == 3
        assert len(result.kept) == 3
        assert 3 <= result.total <= 18

    def test_modifier_positive(self):
        """Test positive modifier."""
        result = self.roller.roll("1d20+5")
        assert result.modifier == 5
        assert result.total == result.kept[0] + 5

    def test_modifier_negative(self):
        """Test negative modifier."""
        result = self.roller.roll("1d20-3")
        assert result.modifier == -3
        assert result.total == result.kept[0] - 3

    def test_advantage(self):
        """Test rolling with advantage."""
        result = self.roller.roll("1d20 advantage")
        assert result.roll_type == RollType.ADVANTAGE
        assert len(result.rolls) == 2
        assert len(result.kept) == 1
        assert len(result.dropped) == 1
        assert result.kept[0] == max(result.rolls)

    def test_disadvantage(self):
        """Test rolling with disadvantage."""
        result = self.roller.roll("1d20 disadvantage")
        assert result.roll_type == RollType.DISADVANTAGE
        assert len(result.rolls) == 2
        assert len(result.kept) == 1
        assert result.kept[0] == min(result.rolls)

    def test_advantage_short_form(self):
        """Test short form advantage notation."""
        result = self.roller.roll("1d20 adv")
        assert result.roll_type == RollType.ADVANTAGE

    def test_disadvantage_short_form(self):
        """Test short form disadvantage notation."""
        result = self.roller.roll("1d20 dis")
        assert result.roll_type == RollType.DISADVANTAGE

    def test_drop_lowest(self):
        """Test dropping lowest dice (4d6 drop lowest)."""
        result = self.roller.roll("4d6 drop lowest")
        assert result.roll_type == RollType.DROP_LOWEST
        assert len(result.rolls) == 4
        assert len(result.kept) == 3
        assert len(result.dropped) == 1
        assert result.dropped[0] == min(result.rolls)
        assert result.total == sum(result.kept)

    def test_drop_lowest_multiple(self):
        """Test dropping multiple lowest dice."""
        result = self.roller.roll("5d6 drop lowest 2")
        assert len(result.dropped) == 2
        assert len(result.kept) == 3

    def test_drop_highest(self):
        """Test dropping highest dice."""
        result = self.roller.roll("4d6 drop highest")
        assert result.roll_type == RollType.DROP_HIGHEST
        assert len(result.dropped) == 1
        assert result.dropped[0] == max(result.rolls)

    def test_keep_highest(self):
        """Test keeping highest dice."""
        result = self.roller.roll("4d6 keep highest 3")
        assert result.roll_type == RollType.KEEP_HIGHEST
        assert len(result.kept) == 3
        assert len(result.dropped) == 1

    def test_keep_lowest(self):
        """Test keeping lowest dice."""
        result = self.roller.roll("4d6 keep lowest 2")
        assert result.roll_type == RollType.KEEP_LOWEST
        assert len(result.kept) == 2
        assert len(result.dropped) == 2

    def test_critical_detection(self):
        """Test natural 20 critical detection."""
        # Force a natural 20
        roller = DiceRoller(rng=random.Random())
        roller.rng.randint = lambda a, b: 20  # Mock to always return 20

        result = roller.roll("1d20")
        assert result.natural_roll == 20
        assert result.is_critical is True
        assert result.is_fumble is False

    def test_fumble_detection(self):
        """Test natural 1 fumble detection."""
        roller = DiceRoller(rng=random.Random())
        roller.rng.randint = lambda a, b: 1  # Mock to always return 1

        result = roller.roll("1d20")
        assert result.natural_roll == 1
        assert result.is_fumble is True
        assert result.is_critical is False

    def test_invalid_notation(self):
        """Test that invalid notation raises ValueError."""
        with pytest.raises(ValueError):
            self.roller.roll("invalid")

        with pytest.raises(ValueError):
            self.roller.roll("d")

        with pytest.raises(ValueError):
            self.roller.roll("abc123")

    def test_case_insensitive(self):
        """Test that notation parsing is case insensitive."""
        result1 = self.roller.roll("1D20")
        result2 = self.roller.roll("1d20 ADVANTAGE")
        result3 = self.roller.roll("4D6 DROP LOWEST")

        assert result1.notation.lower().startswith("1d20")
        assert result2.roll_type == RollType.ADVANTAGE
        assert result3.roll_type == RollType.DROP_LOWEST

    def test_ability_scores_4d6_drop_lowest(self):
        """Test ability score generation with 4d6 drop lowest."""
        scores = self.roller.roll_ability_scores("4d6_drop_lowest")
        assert len(scores) == 6
        for score in scores:
            assert 3 <= score.total <= 18

    def test_ability_scores_3d6(self):
        """Test ability score generation with 3d6."""
        scores = self.roller.roll_ability_scores("3d6")
        assert len(scores) == 6
        for score in scores:
            assert 3 <= score.total <= 18

    def test_ability_scores_standard_array(self):
        """Test standard array ability scores."""
        scores = self.roller.roll_ability_scores("standard_array")
        totals = [s.total for s in scores]
        assert sorted(totals) == [8, 10, 12, 13, 14, 15]

    def test_roll_with_critical(self):
        """Test attack roll with critical threat detection."""
        result, is_threat = self.roller.roll_with_critical(
            attack_modifier=5,
            critical_range=(19, 20),
        )
        assert result.modifier == 5
        if result.natural_roll and result.natural_roll >= 19:
            assert is_threat is True

    def test_confirm_critical(self):
        """Test critical confirmation roll."""
        result, confirmed = self.roller.confirm_critical(
            attack_modifier=10,
            target_ac=15,
        )
        assert confirmed == (result.total >= 15)

    def test_dice_result_str(self):
        """Test DiceResult string representation."""
        result = DiceResult(
            notation="2d6+3",
            rolls=[4, 5],
            kept=[4, 5],
            dropped=[],
            modifier=3,
            total=12,
        )
        str_repr = str(result)
        assert "2d6+3" in str_repr
        assert "12" in str_repr

    def test_dice_result_with_critical_str(self):
        """Test DiceResult string with critical."""
        result = DiceResult(
            notation="1d20+5",
            rolls=[20],
            kept=[20],
            dropped=[],
            modifier=5,
            total=25,
            is_critical=True,
            natural_roll=20,
        )
        str_repr = str(result)
        assert "CRITICAL" in str_repr

    def test_seeded_reproducibility(self):
        """Test that seeded roller produces reproducible results."""
        roller1 = DiceRoller()
        roller1.seed(12345)
        results1 = [roller1.roll("1d20").total for _ in range(5)]

        roller2 = DiceRoller()
        roller2.seed(12345)
        results2 = [roller2.roll("1d20").total for _ in range(5)]

        assert results1 == results2


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_roll_function(self):
        """Test the quick roll function."""
        result = roll("1d20")
        assert isinstance(result, DiceResult)
        assert 1 <= result.total <= 20

    def test_roll_multiple_function(self):
        """Test rolling multiple expressions."""
        results = roll_multiple(["1d20", "2d6", "1d8+2"])
        assert len(results) == 3
        assert all(isinstance(r, DiceResult) for r in results)


class TestDicePool:
    """Test DicePool dataclass."""

    def test_default_values(self):
        """Test DicePool default values."""
        pool = DicePool(count=2, sides=6)
        assert pool.count == 2
        assert pool.sides == 6
        assert pool.modifier == 0
        assert pool.roll_type == RollType.NORMAL
        assert pool.drop_count == 0
        assert pool.keep_count is None
        assert pool.critical_range == (20, 20)
