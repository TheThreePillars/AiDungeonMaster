"""Structured prompt system for AI Dungeon Master."""

from .dm_contract import DM_CONTRACT
from .builder import build_prompt, parse_dm_response

__all__ = ["DM_CONTRACT", "build_prompt", "parse_dm_response"]
