"""Tests for UI module."""

import pytest
from unittest.mock import MagicMock, patch

from src.game.dice import DiceResult


class TestDiceRollerWidget:
    """Tests for DiceRollerWidget."""

    def test_dice_roller_import(self):
        """Test that dice roller widget can be imported."""
        from src.ui.widgets.dice_roller import DiceRollerWidget
        assert DiceRollerWidget is not None

    def test_dice_roller_initialization(self):
        """Test DiceRollerWidget initialization."""
        from src.ui.widgets.dice_roller import DiceRollerWidget

        widget = DiceRollerWidget()
        assert widget.roller is not None
        assert widget.last_result is None


class TestCharacterDisplayWidget:
    """Tests for CharacterDisplayWidget."""

    def test_character_display_import(self):
        """Test that character display widget can be imported."""
        from src.ui.widgets.character_display import (
            CharacterDisplayWidget,
            HPBar,
            AbilityScoreWidget,
        )
        assert CharacterDisplayWidget is not None
        assert HPBar is not None
        assert AbilityScoreWidget is not None

    def test_hp_bar_initialization(self):
        """Test HPBar initialization."""
        from src.ui.widgets.character_display import HPBar

        bar = HPBar(current=25, maximum=50)
        assert bar.current == 25
        assert bar.maximum == 50

    def test_ability_score_widget_initialization(self):
        """Test AbilityScoreWidget initialization."""
        from src.ui.widgets.character_display import AbilityScoreWidget

        abilities = {"STR": 16, "DEX": 14, "CON": 12, "INT": 10, "WIS": 8, "CHA": 6}
        widget = AbilityScoreWidget(abilities=abilities)

        assert widget.abilities["STR"] == 16
        assert widget.abilities["CHA"] == 6


class TestChatLogWidget:
    """Tests for ChatLogWidget."""

    def test_chat_log_import(self):
        """Test that chat log widget can be imported."""
        from src.ui.widgets.chat_log import ChatLogWidget, MessageType, ChatMessage
        assert ChatLogWidget is not None
        assert MessageType is not None
        assert ChatMessage is not None

    def test_message_types(self):
        """Test message type enum."""
        from src.ui.widgets.chat_log import MessageType

        assert MessageType.PLAYER.value == "player"
        assert MessageType.DM.value == "dm"
        assert MessageType.SYSTEM.value == "system"
        assert MessageType.DICE.value == "dice"
        assert MessageType.COMBAT.value == "combat"

    def test_chat_message_formatting(self):
        """Test chat message formatting."""
        from src.ui.widgets.chat_log import ChatMessage, MessageType

        # Player message
        msg = ChatMessage("Hello", MessageType.PLAYER)
        formatted = msg.formatted
        assert ">" in formatted
        assert "Hello" in formatted

        # DM message
        msg = ChatMessage("Welcome adventurer", MessageType.DM)
        formatted = msg.formatted
        assert "DM:" in formatted

        # System message
        msg = ChatMessage("Game saved", MessageType.SYSTEM)
        formatted = msg.formatted
        assert "italic" in formatted

    def test_chat_log_widget_initialization(self):
        """Test ChatLogWidget initialization."""
        from src.ui.widgets.chat_log import ChatLogWidget

        widget = ChatLogWidget(show_input=True)
        assert widget.show_input is True
        assert widget.messages == []

        widget2 = ChatLogWidget(show_input=False)
        assert widget2.show_input is False


class TestScreenImports:
    """Tests for screen module imports."""

    def test_main_menu_import(self):
        """Test main menu screen import."""
        from src.ui.screens.main_menu import MainMenuScreen
        assert MainMenuScreen is not None

    def test_character_creation_import(self):
        """Test character creation screen import."""
        from src.ui.screens.character_creation import (
            CharacterCreationScreen,
            AbilityScoreDisplay,
        )
        assert CharacterCreationScreen is not None
        assert AbilityScoreDisplay is not None

    def test_game_session_import(self):
        """Test game session screen import."""
        from src.ui.screens.game_session import GameSessionScreen, PartyStatusWidget
        assert GameSessionScreen is not None
        assert PartyStatusWidget is not None

    def test_combat_view_import(self):
        """Test combat view screen import."""
        from src.ui.screens.combat_view import CombatViewScreen, ENEMY_TEMPLATES
        assert CombatViewScreen is not None
        assert ENEMY_TEMPLATES is not None
        assert "Goblin" in ENEMY_TEMPLATES

    def test_party_manager_import(self):
        """Test party manager screen import."""
        from src.ui.screens.party_manager import PartyManagerScreen
        assert PartyManagerScreen is not None


class TestAppImport:
    """Tests for main app import."""

    def test_app_import(self):
        """Test main app import."""
        from src.ui.app import AIDungeonMasterApp, run_app
        assert AIDungeonMasterApp is not None
        assert run_app is not None

    def test_app_initialization(self):
        """Test app initialization."""
        from src.ui.app import AIDungeonMasterApp

        app = AIDungeonMasterApp()
        assert app.TITLE == "AI Dungeon Master"
        assert app.game_state is not None
        assert app.game_state.party_id is None
        assert app.game_state.campaign_id is None

    def test_app_screens_registered(self):
        """Test that screens are registered."""
        from src.ui.app import AIDungeonMasterApp

        app = AIDungeonMasterApp()
        assert "main_menu" in app.SCREENS
        assert "character_creation" in app.SCREENS
        assert "game_session" in app.SCREENS
        assert "combat_view" in app.SCREENS
        assert "party_manager" in app.SCREENS

    def test_app_bindings(self):
        """Test that key bindings are defined."""
        from src.ui.app import AIDungeonMasterApp

        app = AIDungeonMasterApp()
        binding_keys = [b.key for b in app.BINDINGS]

        assert "q" in binding_keys
        assert "escape" in binding_keys
        assert "f1" in binding_keys


class TestAbilityScoreDisplay:
    """Tests for AbilityScoreDisplay widget in character creation."""

    def test_modifier_calculation(self):
        """Test ability modifier calculation."""
        from src.ui.screens.character_creation import AbilityScoreDisplay

        display = AbilityScoreDisplay()

        # Test modifier string generation
        assert display._get_modifier(10) == "(+0)"
        assert display._get_modifier(14) == "(+2)"
        assert display._get_modifier(8) == "(-1)"
        assert display._get_modifier(18) == "(+4)"
        assert display._get_modifier(6) == "(-2)"


class TestCombatTracker:
    """Tests for CombatTracker used in combat view."""

    def test_tracker_initialization(self):
        """Test combat tracker initialization."""
        from src.game.combat import CombatTracker, CombatState

        tracker = CombatTracker()
        assert tracker.combatants == []
        assert tracker.current_turn == 0
        assert tracker.state == CombatState.NOT_STARTED


class TestGameSessionScreen:
    """Tests for GameSessionScreen."""

    def test_screen_initialization(self):
        """Test game session screen can be initialized."""
        from src.ui.screens.game_session import GameSessionScreen

        screen = GameSessionScreen()
        assert screen is not None


class TestCombatViewScreen:
    """Tests for CombatViewScreen."""

    def test_screen_initialization(self):
        """Test combat view screen can be initialized."""
        from src.ui.screens.combat_view import CombatViewScreen

        screen = CombatViewScreen()
        assert screen.combat_tracker is not None
        assert screen.selected_target is None


class TestPartyManagerScreen:
    """Tests for PartyManagerScreen."""

    def test_screen_initialization(self):
        """Test party manager screen can be initialized."""
        from src.ui.screens.party_manager import PartyManagerScreen

        screen = PartyManagerScreen()
        assert screen.selected_character_id is None
        assert screen.party_gold == 0  # Starts at 0, loaded from database


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
