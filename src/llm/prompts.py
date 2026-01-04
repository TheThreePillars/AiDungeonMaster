"""System prompts and templates for the AI Dungeon Master."""

from pathlib import Path
from string import Template
from typing import Any


# Default prompt templates (used if files not found)
DEFAULT_DM_SYSTEM_PROMPT = """You are an experienced Game Master running a Pathfinder 1st Edition campaign. You create immersive, descriptive narratives while respecting game mechanics. You:

- Describe scenes vividly but concisely (2-4 sentences for normal descriptions)
- Voice NPCs with distinct personalities and speech patterns
- Present meaningful choices to players
- Balance challenge with fun
- Track context from the current session
- Respect Pathfinder 1e rules (BAB, CMB/CMD, 3.5-style saves, etc.)

When a player attempts an action that requires a check, indicate it with:
[ROLL: type DC/target]

Examples:
- [ROLL: Perception DC 15]
- [ROLL: Attack vs AC 18]
- [ROLL: Fortitude Save DC 14]
- [ROLL: CMB vs CMD 22]

For damage, use:
[DAMAGE: XdY+Z type]

Example:
- [DAMAGE: 1d8+4 slashing]

When combat should begin, say:
[COMBAT: enemy1, enemy2, ...]

Always stay in character as the Game Master. Never break the fourth wall unless the player asks a rules question directly."""


DEFAULT_CHARACTER_INTERVIEW_PROMPT = """You are helping a player create their Pathfinder 1e character through friendly conversation.

Ask questions one at a time to understand:
1. What fantasy archetype excites them (warrior, mage, rogue, healer, etc.)
2. Preferred combat style (melee, ranged, magic, support, battlefield control)
3. Social role (leader, loner, comic relief, mysterious stranger, noble)
4. A brief character concept or inspiration (a book, movie, or idea)

Based on their answers, suggest 2-3 race/class combinations that fit their vision. Consider:
- Core classes: Fighter, Rogue, Wizard, Cleric, Barbarian, Bard, Druid, Monk, Paladin, Ranger, Sorcerer
- Popular alternatives: Alchemist, Cavalier, Gunslinger, Inquisitor, Magus, Oracle, Summoner, Witch

After they choose, help them develop:
- Two personality traits
- A background/origin
- A motivation or goal
- A flaw or weakness

Keep questions conversational and engaging. One question at a time."""


DEFAULT_COMBAT_NARRATOR_PROMPT = """Narrate combat actions dramatically but briefly (1-3 sentences).

You receive:
- The action taken (attack, spell, ability, maneuver)
- The roll result and whether it hits
- Damage dealt (if applicable)
- Current HP of target
- Any special conditions

Guidelines:
- Make critical hits feel epic and impactful
- Make misses feel consequential but not frustrating
- Describe spell effects vividly
- Note when enemies are bloodied (below 50% HP) or near death
- Vary your descriptions - don't repeat the same phrases
- Include environmental details occasionally
- Reference the character's fighting style or personality

Do NOT:
- Describe player character deaths without explicit GM decision
- Skip important mechanical information
- Make the narration longer than 3 sentences for normal attacks"""


DEFAULT_WORLD_BUILDER_PROMPT = """You are a world-building assistant for a Pathfinder 1e campaign.

When asked to generate content, create:
- Locations with interesting features and potential plot hooks
- NPCs with distinct personalities, motivations, and secrets
- Quest hooks that connect to the party's goals
- Encounters appropriate for the party's level

For locations, include:
- Physical description (2-3 sentences)
- Atmosphere/mood
- Notable features
- Potential dangers or opportunities
- 1-2 interesting NPCs or creatures

For NPCs, include:
- Name and brief physical description
- Personality in 2-3 words
- Motivation/goal
- A secret or hidden depth
- Voice/speech pattern notes

Keep content appropriate for the Golarion setting or generic fantasy if no setting specified."""


class PromptManager:
    """Manages loading and formatting of prompt templates."""

    def __init__(self, prompts_dir: Path | str | None = None):
        """Initialize the prompt manager.

        Args:
            prompts_dir: Directory containing prompt template files
        """
        if prompts_dir:
            self.prompts_dir = Path(prompts_dir)
        else:
            self.prompts_dir = Path("data/prompts")

        # Cache for loaded prompts
        self._cache: dict[str, str] = {}

        # Default prompts
        self._defaults = {
            "dm_system": DEFAULT_DM_SYSTEM_PROMPT,
            "character_interview": DEFAULT_CHARACTER_INTERVIEW_PROMPT,
            "combat_narrator": DEFAULT_COMBAT_NARRATOR_PROMPT,
            "world_builder": DEFAULT_WORLD_BUILDER_PROMPT,
        }

    def get_prompt(self, name: str, **kwargs: Any) -> str:
        """Get a prompt template, optionally with variable substitution.

        Args:
            name: Prompt name (e.g., "dm_system", "character_interview")
            **kwargs: Variables to substitute in the template

        Returns:
            The prompt string with variables substituted
        """
        # Check cache first
        if name not in self._cache:
            self._cache[name] = self._load_prompt(name)

        template = self._cache[name]

        # Substitute variables if any provided
        if kwargs:
            try:
                return Template(template).safe_substitute(**kwargs)
            except Exception:
                return template

        return template

    def _load_prompt(self, name: str) -> str:
        """Load a prompt from file or return default.

        Args:
            name: Prompt name

        Returns:
            Prompt content
        """
        # Try to load from file
        file_path = self.prompts_dir / f"{name}.txt"
        if file_path.exists():
            try:
                return file_path.read_text(encoding="utf-8")
            except Exception:
                pass

        # Fall back to default
        return self._defaults.get(name, "")

    def save_prompt(self, name: str, content: str) -> None:
        """Save a prompt to file.

        Args:
            name: Prompt name
            content: Prompt content
        """
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        file_path = self.prompts_dir / f"{name}.txt"
        file_path.write_text(content, encoding="utf-8")
        self._cache[name] = content

    def reload(self) -> None:
        """Clear cache and reload all prompts from disk."""
        self._cache.clear()

    def list_prompts(self) -> list[str]:
        """List all available prompt names.

        Returns:
            List of prompt names
        """
        names = set(self._defaults.keys())

        if self.prompts_dir.exists():
            for file in self.prompts_dir.glob("*.txt"):
                names.add(file.stem)

        return sorted(names)


# Utility functions for building context-aware prompts
def build_character_context(character_data: dict[str, Any]) -> str:
    """Build a character context string for injection into prompts.

    Args:
        character_data: Character data dictionary

    Returns:
        Formatted character context string
    """
    lines = [
        f"CHARACTER: {character_data.get('name', 'Unknown')}",
        f"Race/Class: {character_data.get('race', '?')} {character_data.get('character_class', '?')} {character_data.get('level', 1)}",
        f"HP: {character_data.get('current_hp', 0)}/{character_data.get('max_hp', 0)}",
        f"AC: {character_data.get('armor_class', 10)}",
    ]

    # Add ability scores
    abilities = []
    for ability in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
        score = character_data.get(ability, 10)
        mod = (score - 10) // 2
        sign = "+" if mod >= 0 else ""
        abilities.append(f"{ability[:3].upper()} {score}({sign}{mod})")
    lines.append(" | ".join(abilities))

    # Add conditions if any
    conditions = character_data.get("conditions", [])
    if conditions:
        lines.append(f"Conditions: {', '.join(conditions)}")

    return "\n".join(lines)


def build_party_context(party_data: list[dict[str, Any]]) -> str:
    """Build a party context string for injection into prompts.

    Args:
        party_data: List of character data dictionaries

    Returns:
        Formatted party context string
    """
    if not party_data:
        return "No party members."

    lines = ["PARTY MEMBERS:"]
    for char in party_data:
        hp_status = ""
        current_hp = char.get("current_hp", 0)
        max_hp = char.get("max_hp", 1)
        hp_pct = (current_hp / max_hp * 100) if max_hp > 0 else 0

        if hp_pct <= 0:
            hp_status = " [UNCONSCIOUS]"
        elif hp_pct <= 25:
            hp_status = " [CRITICAL]"
        elif hp_pct <= 50:
            hp_status = " [BLOODIED]"

        lines.append(
            f"- {char.get('name', 'Unknown')}: "
            f"{char.get('race', '?')} {char.get('character_class', '?')} {char.get('level', 1)}, "
            f"HP {current_hp}/{max_hp}{hp_status}"
        )

    return "\n".join(lines)


def build_combat_context(
    combatants: list[dict[str, Any]],
    current_turn: str,
    round_number: int,
) -> str:
    """Build a combat context string.

    Args:
        combatants: List of combatant data (name, hp, ac, conditions)
        current_turn: Name of combatant whose turn it is
        round_number: Current combat round

    Returns:
        Formatted combat context string
    """
    lines = [
        f"COMBAT - Round {round_number}",
        f"Current Turn: {current_turn}",
        "",
        "Initiative Order:",
    ]

    for i, combatant in enumerate(combatants, 1):
        name = combatant.get("name", "Unknown")
        hp_current = combatant.get("current_hp", 0)
        hp_max = combatant.get("max_hp", 1)
        conditions = combatant.get("conditions", [])

        marker = ">>>" if name == current_turn else "   "
        status = ""

        if hp_current <= 0:
            status = " [DOWN]"
        elif hp_current <= hp_max * 0.25:
            status = " [CRITICAL]"
        elif hp_current <= hp_max * 0.5:
            status = " [BLOODIED]"

        cond_str = f" ({', '.join(conditions)})" if conditions else ""

        lines.append(f"{marker} {i}. {name} - HP {hp_current}/{hp_max}{status}{cond_str}")

    return "\n".join(lines)
