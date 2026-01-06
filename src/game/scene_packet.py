"""Scene Packet - Immediate scene context for LLM.

Contains only what matters RIGHT NOW for the current scene.
Target: 200-350 tokens when serialized.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CombatantStatus:
    """Status of a combatant in the current fight."""
    name: str
    hp_current: int
    hp_max: int
    conditions: list[str] = field(default_factory=list)
    is_player: bool = True

    def to_str(self) -> str:
        cond_str = f" [{', '.join(self.conditions)}]" if self.conditions else ""
        return f"{self.name}: {self.hp_current}/{self.hp_max} HP{cond_str}"


@dataclass
class ScenePacket:
    """Immediate scene context - rebuilt each turn."""

    # Where they are right now (2-5 bullets)
    immediate_location: str = ""  # "Inside the tavern main hall"
    visible_elements: list[str] = field(default_factory=list)  # What they see

    # Combat snapshot (if in combat)
    in_combat: bool = False
    initiative_order: list[str] = field(default_factory=list)  # Names in order
    current_turn: str = ""  # Whose turn it is
    combatants: list[CombatantStatus] = field(default_factory=list)

    # Relevant abilities/items this moment (not full sheets)
    relevant_abilities: list[str] = field(default_factory=list)
    # e.g., "Thorin: Power Attack active, has torch"

    # Environmental factors
    environmental: list[str] = field(default_factory=list)
    # e.g., ["Dim light (-2 Perception)", "Wooden floor", "Fire nearby"]

    # Pending player input
    player_actions: list[tuple[str, str]] = field(default_factory=list)
    # [(character_name, action_text), ...]

    def set_combat_state(self, initiative: list[str], current: str,
                        combatants: list[CombatantStatus]):
        """Set up combat snapshot."""
        self.in_combat = True
        self.initiative_order = initiative
        self.current_turn = current
        self.combatants = combatants

    def add_visible(self, element: str):
        """Add a visible element, max 5."""
        if element not in self.visible_elements:
            self.visible_elements.append(element)
            if len(self.visible_elements) > 5:
                self.visible_elements.pop(0)

    def add_environmental(self, factor: str):
        """Add an environmental factor."""
        if factor not in self.environmental:
            self.environmental.append(factor)

    def set_player_actions(self, actions: list[tuple[str, str]]):
        """Set the player actions to process."""
        self.player_actions = actions

    def to_prompt(self) -> str:
        """Generate scene context for LLM."""
        lines = ["=== CURRENT SCENE ==="]

        # Location
        if self.immediate_location:
            lines.append(f"WHERE: {self.immediate_location}")

        # What they see
        if self.visible_elements:
            lines.append("VISIBLE:")
            for elem in self.visible_elements:
                lines.append(f"  - {elem}")

        # Combat snapshot
        if self.in_combat:
            lines.append("")
            lines.append("COMBAT STATUS:")
            init_str = " > ".join(self.initiative_order)
            lines.append(f"  Initiative: {init_str}")
            lines.append(f"  Current turn: {self.current_turn}")
            if self.combatants:
                lines.append("  Combatants:")
                for c in self.combatants:
                    marker = "[PC]" if c.is_player else "[NPC]"
                    lines.append(f"    {marker} {c.to_str()}")

        # Relevant abilities (only if there are any)
        if self.relevant_abilities:
            lines.append("")
            lines.append("RELEVANT NOW:")
            for ability in self.relevant_abilities:
                lines.append(f"  - {ability}")

        # Environmental factors
        if self.environmental:
            lines.append("")
            lines.append("ENVIRONMENT:")
            for factor in self.environmental:
                lines.append(f"  - {factor}")

        # Player actions to process
        if self.player_actions:
            lines.append("")
            lines.append("PLAYER ACTIONS THIS ROUND:")
            for char_name, action in self.player_actions:
                lines.append(f"  - {char_name}: \"{action}\"")

        return "\n".join(lines)


def build_scene_from_game_state(
    location: str,
    location_detail: str,
    in_combat: bool,
    initiative_order: list[str],
    current_turn: str,
    visible_elements: list[str],
    environmental: list[str],
    player_actions: list[tuple[str, str]],
    combatant_data: list[dict] = None,
    relevant_abilities: list[str] = None,
) -> ScenePacket:
    """Build a ScenePacket from game state."""
    scene = ScenePacket()
    scene.immediate_location = f"{location} - {location_detail}"
    scene.visible_elements = visible_elements or []
    scene.environmental = environmental or []
    scene.player_actions = player_actions or []
    scene.relevant_abilities = relevant_abilities or []

    if in_combat and combatant_data:
        combatants = [
            CombatantStatus(
                name=c["name"],
                hp_current=c.get("hp_current", 0),
                hp_max=c.get("hp_max", 0),
                conditions=c.get("conditions", []),
                is_player=c.get("is_player", True),
            )
            for c in combatant_data
        ]
        scene.set_combat_state(initiative_order, current_turn, combatants)

    return scene
