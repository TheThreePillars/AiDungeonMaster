"""Prompt Builder - Assembles structured prompts for LLM calls.

Combines DM Contract + Session State + Scene Packet into final prompt.
"""

import json
import re
from typing import Optional, Tuple

from .dm_contract import DM_CONTRACT, OUTPUT_INSTRUCTION
from ..game.session_state import SessionState
from ..game.scene_packet import ScenePacket


def build_prompt(
    session_state: SessionState,
    scene: ScenePacket,
    player_input: str = "",
    include_output_instruction: bool = True,
) -> str:
    """Build the complete prompt for an LLM call.

    Args:
        session_state: Current session state summary
        scene: Current scene packet
        player_input: Optional additional player input text
        include_output_instruction: Whether to include structured output format

    Returns:
        Complete prompt string
    """
    parts = [
        DM_CONTRACT,
        "",
        session_state.to_prompt(),
        "",
        scene.to_prompt(),
    ]

    if player_input:
        parts.extend(["", f"=== ADDITIONAL CONTEXT ===", player_input])

    if include_output_instruction:
        parts.extend(["", OUTPUT_INSTRUCTION])

    return "\n".join(parts)


def build_opening_prompt(
    session_state: SessionState,
    party_text: str,
    initiative_text: str,
    first_player: str,
    first_roll: int,
) -> str:
    """Build the opening scene prompt.

    Args:
        session_state: Current session state
        party_text: Formatted party member list
        initiative_text: Formatted initiative rolls
        first_player: Who goes first
        first_roll: Their initiative roll

    Returns:
        Opening scene prompt
    """
    scene = ScenePacket()
    scene.immediate_location = "The Rusty Dragon Inn - Main hall, evening"
    scene.visible_elements = [
        "Warm tavern with crackling fireplace",
        "Local patrons drinking and talking quietly",
        "Bar counter with bottles and mugs",
        "Innkeeper Ameiko (Tian woman) polishing glasses",
        "Stairs leading to guest rooms",
    ]
    scene.environmental = [
        "Warm and inviting atmosphere",
        "Normal lighting from fire and candles",
        "Smell of ale and cooking food",
    ]

    opening_instruction = f"""=== OPENING SCENE ===
Create the opening scene for this adventure.

PLAYER CHARACTERS (these are the PLAYERS, not NPCs):
{party_text}

INITIATIVE ROLLED:
{initiative_text}

INSTRUCTIONS:
1. Set the scene at the Rusty Dragon Inn (4-5 sentences max)
2. Describe the atmosphere - warm tavern, locals drinking, innkeeper Ameiko
3. Do NOT introduce other adventurers or performers as NPCs
4. Announce initiative order
5. End with: "{first_player}, you rolled {first_roll} for initiative. It's your turn. What do you do?"

[RESPONSE]
<Write opening scene here>
[/RESPONSE]

[STATE_UPDATE]
{{"new_event": "Adventure began at the Rusty Dragon Inn", "new_npc": {{"name": "Ameiko Kaijitsu", "attitude": "friendly", "note": "Innkeeper, knows local rumors"}}}}
[/STATE_UPDATE]"""

    return f"{DM_CONTRACT}\n\n{session_state.to_prompt()}\n\n{scene.to_prompt()}\n\n{opening_instruction}"


def parse_dm_response(raw_response: str) -> Tuple[str, Optional[dict]]:
    """Parse the DM response to extract player-facing text and state update.

    Args:
        raw_response: Raw LLM response text

    Returns:
        Tuple of (player_facing_text, state_update_dict or None)
    """
    player_text = raw_response
    state_update = None

    # Try to extract [RESPONSE] block
    response_match = re.search(
        r'\[RESPONSE\](.*?)\[/RESPONSE\]',
        raw_response,
        re.DOTALL | re.IGNORECASE
    )
    if response_match:
        player_text = response_match.group(1).strip()

    # Try to extract [STATE_UPDATE] block (various formats)
    state_patterns = [
        r'\[STATE_UPDATE\](.*?)\[/STATE_UPDATE\]',
        r'\[STATE_UPDATE\](.*?)$',  # No closing tag
        r'STATE_UPDATE[:\s]*(\{.*?\})',  # Without brackets
        r'\[STATE\](.*?)\[/STATE\]',  # Alternate tag name
    ]

    for pattern in state_patterns:
        state_match = re.search(pattern, raw_response, re.DOTALL | re.IGNORECASE)
        if state_match:
            try:
                state_json = state_match.group(1).strip()
                state_update = json.loads(state_json)
                break
            except json.JSONDecodeError:
                continue

    # Always strip out state-related content from player text
    # Remove [STATE_UPDATE]...[/STATE_UPDATE] blocks
    player_text = re.sub(
        r'\[STATE_UPDATE\].*?(\[/STATE_UPDATE\]|$)',
        '',
        player_text,
        flags=re.DOTALL | re.IGNORECASE
    ).strip()

    # Remove [STATE]...[/STATE] blocks
    player_text = re.sub(
        r'\[STATE\].*?(\[/STATE\]|$)',
        '',
        player_text,
        flags=re.DOTALL | re.IGNORECASE
    ).strip()

    # Remove any remaining JSON-like state blocks at the end
    player_text = re.sub(
        r'STATE_UPDATE[:\s]*\{.*$',
        '',
        player_text,
        flags=re.DOTALL | re.IGNORECASE
    ).strip()

    # Remove [RESPONSE] tags if present
    player_text = re.sub(r'\[/?RESPONSE\]', '', player_text, flags=re.IGNORECASE).strip()

    return player_text, state_update


def build_action_prompt(
    session_state: SessionState,
    scene: ScenePacket,
    next_player: str,
) -> str:
    """Build prompt for processing player actions.

    Args:
        session_state: Current session state
        scene: Scene packet with player actions
        next_player: Who gets the next turn

    Returns:
        Action processing prompt
    """
    instruction = f"""=== PROCESS ACTIONS ===
Narrate the outcome of each player action above.

INSTRUCTIONS:
1. Describe what happens for EACH character's action (2-3 sentences total)
2. Advance the story - NPCs react, discoveries made, consequences happen
3. End with: "{next_player}, it's your turn. What do you do?"
4. If combat, state HP changes and conditions clearly

{OUTPUT_INSTRUCTION}"""

    return f"{DM_CONTRACT}\n\n{session_state.to_prompt()}\n\n{scene.to_prompt()}\n\n{instruction}"


def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars per token average for English)."""
    return len(text) // 4
