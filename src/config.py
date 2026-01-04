"""Configuration management for AI Dungeon Master."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: str = "ollama"
    model: str = "hermes3:latest"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.8
    max_tokens: int = 1024
    context_window: int = 4096


class GameConfig(BaseModel):
    """Game rules configuration."""

    ruleset: str = "pf1e"
    difficulty: str = "normal"
    auto_roll: bool = False
    narration_style: str = "detailed"
    max_party_size: int = 6
    experience_track: str = "medium"


class CombatConfig(BaseModel):
    """Combat system configuration."""

    initiative_style: str = "individual"
    confirm_criticals: bool = True
    auto_stabilize: bool = False


class UIConfig(BaseModel):
    """UI display configuration."""

    theme: str = "dark"
    dice_animation: bool = True
    combat_log_length: int = 50
    chat_history_display: int = 100
    show_roll_details: bool = True


class PathsConfig(BaseModel):
    """File paths configuration."""

    saves: Path = Path("./saves")
    srd_data: Path = Path("./data/srd")
    prompts: Path = Path("./data/prompts")
    database: Path = Path("./saves/campaign.db")


class SessionConfig(BaseModel):
    """Session management configuration."""

    auto_save_interval: int = 300
    summary_frequency: int = 15
    max_context_messages: int = 20


class AppConfig(BaseModel):
    """Main application configuration."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    game: GameConfig = Field(default_factory=GameConfig)
    combat: CombatConfig = Field(default_factory=CombatConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)


def load_config(config_path: Path | str | None = None) -> AppConfig:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config file. Defaults to ./config.yaml

    Returns:
        AppConfig instance with loaded or default values
    """
    if config_path is None:
        config_path = Path("config.yaml")
    else:
        config_path = Path(config_path)

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return AppConfig(**data)

    return AppConfig()


def save_config(config: AppConfig, config_path: Path | str | None = None) -> None:
    """Save configuration to YAML file.

    Args:
        config: AppConfig instance to save
        config_path: Path to save to. Defaults to ./config.yaml
    """
    if config_path is None:
        config_path = Path("config.yaml")
    else:
        config_path = Path(config_path)

    data = config.model_dump()
    # Convert Path objects to strings for YAML serialization
    data["paths"] = {k: str(v) for k, v in data["paths"].items()}

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


# Global config instance
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get the global configuration instance.

    Returns:
        The loaded AppConfig instance
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: Path | str | None = None) -> AppConfig:
    """Reload configuration from disk.

    Args:
        config_path: Path to config file

    Returns:
        Newly loaded AppConfig instance
    """
    global _config
    _config = load_config(config_path)
    return _config
