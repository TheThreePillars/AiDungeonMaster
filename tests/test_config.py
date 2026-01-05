"""Tests for configuration management."""

import tempfile
from pathlib import Path

import pytest

from src.config import (
    AppConfig,
    CombatConfig,
    GameConfig,
    LLMConfig,
    PathsConfig,
    SessionConfig,
    UIConfig,
    load_config,
    save_config,
)


class TestLLMConfig:
    """Test LLM configuration."""

    def test_default_values(self):
        """Test default LLM config values."""
        config = LLMConfig()
        assert config.provider == "ollama"
        assert config.model == "hermes3:8b"
        assert config.temperature == 0.8
        assert config.max_tokens == 1024

    def test_custom_values(self):
        """Test custom LLM config."""
        config = LLMConfig(
            model="hermes3:7b",
            temperature=0.5,
        )
        assert config.model == "hermes3:7b"
        assert config.temperature == 0.5


class TestGameConfig:
    """Test game configuration."""

    def test_default_values(self):
        """Test default game config values."""
        config = GameConfig()
        assert config.ruleset == "pf1e"
        assert config.difficulty == "normal"
        assert config.max_party_size == 6

    def test_pf1e_specific_settings(self):
        """Test Pathfinder 1e specific settings."""
        config = GameConfig()
        assert config.experience_track == "medium"


class TestCombatConfig:
    """Test combat configuration."""

    def test_default_values(self):
        """Test default combat config."""
        config = CombatConfig()
        assert config.initiative_style == "individual"
        assert config.confirm_criticals is True  # PF1e rule

    def test_custom_values(self):
        """Test custom combat config."""
        config = CombatConfig(
            initiative_style="group",
            confirm_criticals=False,
        )
        assert config.initiative_style == "group"
        assert config.confirm_criticals is False


class TestUIConfig:
    """Test UI configuration."""

    def test_default_values(self):
        """Test default UI config."""
        config = UIConfig()
        assert config.theme == "dark"
        assert config.dice_animation is True
        assert config.combat_log_length == 50


class TestPathsConfig:
    """Test paths configuration."""

    def test_default_paths(self):
        """Test default path values."""
        config = PathsConfig()
        assert config.saves == Path("./saves")
        assert config.srd_data == Path("./data/srd")
        assert config.database == Path("./saves/campaign.db")


class TestSessionConfig:
    """Test session configuration."""

    def test_default_values(self):
        """Test default session config."""
        config = SessionConfig()
        assert config.auto_save_interval == 300
        assert config.summary_frequency == 15
        assert config.max_context_messages == 20


class TestAppConfig:
    """Test main application configuration."""

    def test_default_config(self):
        """Test default app config creation."""
        config = AppConfig()
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.game, GameConfig)
        assert isinstance(config.combat, CombatConfig)
        assert isinstance(config.ui, UIConfig)
        assert isinstance(config.paths, PathsConfig)
        assert isinstance(config.session, SessionConfig)

    def test_nested_config(self):
        """Test nested configuration access."""
        config = AppConfig()
        assert config.llm.model == "hermes3:8b"
        assert config.game.ruleset == "pf1e"
        assert config.combat.confirm_criticals is True


class TestConfigFileOperations:
    """Test config file save/load operations."""

    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"

            # Create custom config
            config = AppConfig(
                llm=LLMConfig(model="custom-model", temperature=0.5),
                game=GameConfig(difficulty="hard"),
            )

            # Save
            save_config(config, config_path)
            assert config_path.exists()

            # Load
            loaded = load_config(config_path)
            assert loaded.llm.model == "custom-model"
            assert loaded.llm.temperature == 0.5
            assert loaded.game.difficulty == "hard"

    def test_load_nonexistent_config(self):
        """Test loading returns defaults when file doesn't exist."""
        config = load_config(Path("/nonexistent/path/config.yaml"))

        # Should return default config
        assert config.llm.model == "hermes3:8b"
        assert config.game.ruleset == "pf1e"

    def test_config_yaml_format(self):
        """Test that saved config is valid YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test.yaml"

            config = AppConfig()
            save_config(config, config_path)

            # Read raw content
            content = config_path.read_text()

            # Should be readable YAML
            assert "llm:" in content
            assert "game:" in content
            assert "ruleset: pf1e" in content
