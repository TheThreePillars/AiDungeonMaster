"""Tests for LLM client and memory management."""

from unittest.mock import MagicMock, patch

import pytest

from src.llm.client import GenerationConfig, GenerationResult, Message, OllamaClient
from src.llm.memory import ContextInfo, ConversationMemory, ConversationTurn
from src.llm.prompts import (
    PromptManager,
    build_character_context,
    build_combat_context,
    build_party_context,
)


class TestMessage:
    """Test Message dataclass."""

    def test_create_message(self):
        """Test creating a message."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_to_dict(self):
        """Test converting message to dictionary."""
        msg = Message(role="assistant", content="Hi there!")
        d = msg.to_dict()
        assert d == {"role": "assistant", "content": "Hi there!"}


class TestGenerationConfig:
    """Test GenerationConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = GenerationConfig()
        assert config.temperature == 0.8
        assert config.max_tokens == 1024
        assert config.top_p == 0.9
        assert config.stop == []

    def test_custom_values(self):
        """Test custom configuration."""
        config = GenerationConfig(
            temperature=0.5,
            max_tokens=512,
            stop=["END"],
        )
        assert config.temperature == 0.5
        assert config.max_tokens == 512
        assert config.stop == ["END"]


class TestOllamaClient:
    """Test OllamaClient wrapper."""

    def test_init(self):
        """Test client initialization."""
        client = OllamaClient(
            model="hermes3:latest",
            base_url="http://localhost:11434",
        )
        assert client.model == "hermes3:latest"
        assert client.base_url == "http://localhost:11434"

    @patch("src.llm.client.Client")
    def test_is_available(self, mock_client_class):
        """Test checking if Ollama is available."""
        mock_client = MagicMock()
        mock_client.list.return_value = {
            "models": [{"name": "hermes3:latest"}, {"name": "llama2:7b"}]
        }
        mock_client_class.return_value = mock_client

        client = OllamaClient(model="hermes3:latest")
        assert client.is_available() is True

    @patch("src.llm.client.Client")
    def test_is_not_available(self, mock_client_class):
        """Test when Ollama model is not available."""
        mock_client = MagicMock()
        mock_client.list.return_value = {"models": [{"name": "llama2:7b"}]}
        mock_client_class.return_value = mock_client

        client = OllamaClient(model="hermes3:latest")
        assert client.is_available() is False

    @patch("src.llm.client.Client")
    def test_list_models(self, mock_client_class):
        """Test listing available models."""
        mock_client = MagicMock()
        mock_client.list.return_value = {
            "models": [{"name": "model1"}, {"name": "model2"}]
        }
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        models = client.list_models()
        assert "model1" in models
        assert "model2" in models

    @patch("src.llm.client.Client")
    def test_generate(self, mock_client_class):
        """Test text generation."""
        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "message": {"content": "Generated response"},
            "model": "hermes3:latest",
            "done": True,
        }
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        result = client.generate("Test prompt")

        assert isinstance(result, GenerationResult)
        assert result.content == "Generated response"
        assert result.done is True

    @patch("src.llm.client.Client")
    def test_generate_with_system_prompt(self, mock_client_class):
        """Test generation with system prompt."""
        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "message": {"content": "Response"},
            "model": "hermes3:latest",
            "done": True,
        }
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        client.generate("Prompt", system_prompt="You are a DM")

        # Verify system prompt was included
        call_args = mock_client.chat.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert "DM" in messages[0]["content"]

    @patch("src.llm.client.Client")
    def test_chat(self, mock_client_class):
        """Test chat with message history."""
        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "message": {"content": "Chat response"},
            "model": "hermes3:latest",
            "done": True,
        }
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi!"),
            Message(role="user", content="How are you?"),
        ]
        result = client.chat(messages)

        assert result.content == "Chat response"


class TestContextInfo:
    """Test ContextInfo dataclass."""

    def test_empty_context(self):
        """Test empty context string."""
        context = ContextInfo()
        assert context.to_context_string() == ""

    def test_context_with_location(self):
        """Test context with location info."""
        context = ContextInfo(
            current_location="Sandpoint",
            time_of_day="Evening",
            weather="Rainy",
        )
        result = context.to_context_string()
        assert "Sandpoint" in result
        assert "Evening" in result
        assert "Rainy" in result

    def test_context_with_party(self):
        """Test context with party info."""
        context = ContextInfo(
            party_summary="A group of 4 adventurers",
            character_summaries=["Fighter Lv 5", "Wizard Lv 5"],
        )
        result = context.to_context_string()
        assert "PARTY" in result
        assert "Fighter Lv 5" in result

    def test_context_with_quests(self):
        """Test context with active quests."""
        context = ContextInfo(
            active_quests=["Find the missing merchant", "Defeat the goblin king"],
        )
        result = context.to_context_string()
        assert "ACTIVE QUESTS" in result
        assert "missing merchant" in result

    def test_context_with_combat(self):
        """Test context with combat info."""
        context = ContextInfo(
            in_combat=True,
            combat_summary="Round 3, Fighter's turn",
        )
        result = context.to_context_string()
        assert "COMBAT STATUS" in result
        assert "Round 3" in result


class TestConversationMemory:
    """Test ConversationMemory class."""

    def test_add_user_message(self):
        """Test adding user message."""
        memory = ConversationMemory()
        memory.add_user_message("Hello, DM!")

        assert len(memory.messages) == 1
        assert memory.messages[0].role == "user"
        assert memory.messages[0].content == "Hello, DM!"

    def test_add_assistant_message(self):
        """Test adding assistant message."""
        memory = ConversationMemory()
        memory.add_assistant_message("Welcome, adventurer!")

        assert len(memory.messages) == 1
        assert memory.messages[0].role == "assistant"

    def test_system_prompt(self):
        """Test system prompt getter/setter."""
        memory = ConversationMemory()
        memory.system_prompt = "You are a DM"

        assert memory.system_prompt == "You are a DM"

    def test_get_messages_for_llm(self):
        """Test getting messages formatted for LLM."""
        memory = ConversationMemory()
        memory.system_prompt = "System prompt"
        memory.add_user_message("User message")
        memory.add_assistant_message("Assistant response")

        messages = memory.get_messages_for_llm()

        assert len(messages) == 3
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert messages[2].role == "assistant"

    def test_update_context(self):
        """Test updating context."""
        memory = ConversationMemory()
        memory.update_context(
            current_location="Tavern",
            in_combat=False,
        )

        assert memory.context.current_location == "Tavern"
        assert memory.context.in_combat is False

    def test_clear(self):
        """Test clearing memory."""
        memory = ConversationMemory()
        memory.add_user_message("Test")
        memory.session_summary = "Summary"

        memory.clear()

        assert len(memory.messages) == 0
        assert memory.session_summary == ""

    def test_export_import_history(self):
        """Test exporting and importing history."""
        memory = ConversationMemory()
        memory.system_prompt = "Test prompt"
        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi")

        exported = memory.export_history()

        new_memory = ConversationMemory()
        new_memory.import_history(exported)

        assert len(new_memory.messages) == 2
        assert new_memory.system_prompt == "Test prompt"

    def test_max_messages_limit(self):
        """Test that get_messages_for_llm respects max_messages."""
        memory = ConversationMemory(max_messages=5)

        for i in range(10):
            memory.add_user_message(f"Message {i}")

        messages = memory.get_messages_for_llm()
        # Should have system + 5 recent messages
        user_messages = [m for m in messages if m.role == "user"]
        assert len(user_messages) <= 5


class TestPromptManager:
    """Test PromptManager class."""

    def test_get_default_prompt(self):
        """Test getting default prompts."""
        manager = PromptManager()

        dm_prompt = manager.get_prompt("dm_system")
        assert "Game Master" in dm_prompt or "Dungeon Master" in dm_prompt

    def test_list_prompts(self):
        """Test listing available prompts."""
        manager = PromptManager()
        prompts = manager.list_prompts()

        assert "dm_system" in prompts
        assert "character_interview" in prompts
        assert "combat_narrator" in prompts

    def test_prompt_with_variables(self):
        """Test prompt with variable substitution."""
        manager = PromptManager()
        manager._cache["test"] = "Hello, $player_name!"

        result = manager.get_prompt("test", player_name="Adventurer")
        assert result == "Hello, Adventurer!"


class TestContextBuilders:
    """Test context building functions."""

    def test_build_character_context(self):
        """Test building character context string."""
        char_data = {
            "name": "Theron",
            "race": "Human",
            "character_class": "Fighter",
            "level": 5,
            "current_hp": 40,
            "max_hp": 45,
            "armor_class": 18,
            "strength": 16,
            "dexterity": 14,
            "constitution": 15,
            "intelligence": 10,
            "wisdom": 12,
            "charisma": 8,
        }

        result = build_character_context(char_data)

        assert "Theron" in result
        assert "Human" in result
        assert "Fighter" in result
        assert "40/45" in result
        assert "STR" in result

    def test_build_party_context(self):
        """Test building party context string."""
        party_data = [
            {"name": "Fighter", "race": "Human", "character_class": "Fighter", "level": 5, "current_hp": 40, "max_hp": 45},
            {"name": "Wizard", "race": "Elf", "character_class": "Wizard", "level": 5, "current_hp": 10, "max_hp": 25},
        ]

        result = build_party_context(party_data)

        assert "Fighter" in result
        assert "Wizard" in result
        assert "BLOODIED" in result  # Wizard is below 50% HP

    def test_build_party_context_empty(self):
        """Test building party context with no members."""
        result = build_party_context([])
        assert "No party members" in result

    def test_build_combat_context(self):
        """Test building combat context string."""
        combatants = [
            {"name": "Fighter", "current_hp": 40, "max_hp": 45, "conditions": []},
            {"name": "Goblin", "current_hp": 3, "max_hp": 6, "conditions": ["frightened"]},
        ]

        result = build_combat_context(combatants, "Fighter", 2)

        assert "Round 2" in result
        assert "Fighter" in result
        assert ">>>" in result  # Current turn indicator
        assert "BLOODIED" in result  # Goblin is below 50%
        assert "frightened" in result
