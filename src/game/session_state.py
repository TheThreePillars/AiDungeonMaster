"""Session State - Rolling summary of game state for LLM context.

This is the main coherence anchor, sent with every LLM call.
Target: 300-450 tokens when serialized.
"""

from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class NPCInfo:
    """Compact NPC representation."""
    name: str
    attitude: str  # friendly, neutral, suspicious, hostile
    note: str  # One-line motivation/role

    def to_str(self) -> str:
        return f"{self.name} ({self.attitude}): {self.note}"


@dataclass
class QuestInfo:
    """Compact quest representation."""
    title: str
    status: str  # active, completed, failed
    objective: str  # Current objective

    def to_str(self) -> str:
        marker = "[X]" if self.status == "completed" else "[ ]"
        return f"{marker} {self.title}: {self.objective}"


@dataclass
class SessionState:
    """Rolling session state summary for LLM context."""

    # Party state (updated from state patches)
    party_summary: str = ""  # "Thorin (Fighter 23/31 HP, torch), Elara (Cleric full, 2 heals)"

    # Location
    location: str = "The Rusty Dragon Inn"
    location_detail: str = "Main hall, evening"

    # Current objective
    current_objective: str = "Begin your adventure"

    # Active NPCs (max 5 most relevant)
    active_npcs: list[NPCInfo] = field(default_factory=list)

    # Active quests (max 3)
    active_quests: list[QuestInfo] = field(default_factory=list)

    # Recent events - very compressed (max 5)
    recent_events: list[str] = field(default_factory=list)

    # DM secrets - hidden info the DM should remember
    dm_secrets: list[str] = field(default_factory=list)

    # Combat state
    in_combat: bool = False
    initiative_order: list[str] = field(default_factory=list)

    # Time tracking
    time_of_day: str = "evening"
    days_elapsed: int = 0

    def add_event(self, event: str):
        """Add a recent event, keeping only last 5."""
        self.recent_events.append(event)
        if len(self.recent_events) > 5:
            self.recent_events.pop(0)

    def add_npc(self, name: str, attitude: str, note: str):
        """Add or update an NPC, keeping only 5 most recent."""
        # Update existing
        for npc in self.active_npcs:
            if npc.name.lower() == name.lower():
                npc.attitude = attitude
                npc.note = note
                return
        # Add new
        self.active_npcs.append(NPCInfo(name, attitude, note))
        if len(self.active_npcs) > 5:
            self.active_npcs.pop(0)

    def update_npc_attitude(self, name: str, attitude: str):
        """Update an NPC's attitude."""
        for npc in self.active_npcs:
            if npc.name.lower() == name.lower():
                npc.attitude = attitude
                return

    def add_quest(self, title: str, objective: str):
        """Add a quest."""
        self.active_quests.append(QuestInfo(title, "active", objective))
        if len(self.active_quests) > 3:
            # Remove oldest completed, or oldest active
            for i, q in enumerate(self.active_quests):
                if q.status == "completed":
                    self.active_quests.pop(i)
                    return
            self.active_quests.pop(0)

    def complete_quest(self, title: str):
        """Mark a quest as completed."""
        for quest in self.active_quests:
            if quest.title.lower() == title.lower():
                quest.status = "completed"
                return

    def add_secret(self, secret: str):
        """Add a DM secret, keeping max 3."""
        self.dm_secrets.append(secret)
        if len(self.dm_secrets) > 3:
            self.dm_secrets.pop(0)

    def apply_state_update(self, update: dict):
        """Apply a state update from LLM response."""
        if not update:
            return

        # HP changes would be applied to character DB separately

        if update.get("location_change"):
            self.location = update["location_change"]

        if update.get("combat_started"):
            self.in_combat = True

        if update.get("combat_ended"):
            self.in_combat = False

        if update.get("new_npc"):
            npc = update["new_npc"]
            if isinstance(npc, dict):
                self.add_npc(npc.get("name", "Unknown"),
                           npc.get("attitude", "neutral"),
                           npc.get("note", ""))

        if update.get("npc_attitude_change"):
            for name, attitude in update["npc_attitude_change"].items():
                self.update_npc_attitude(name, attitude)

        if update.get("quest_update"):
            qu = update["quest_update"]
            if isinstance(qu, dict):
                if qu.get("new"):
                    self.add_quest(qu["new"].get("title", "Quest"),
                                  qu["new"].get("objective", ""))
                if qu.get("completed"):
                    self.complete_quest(qu["completed"])

        if update.get("new_event"):
            self.add_event(update["new_event"])

        if update.get("time_advance"):
            self.time_of_day = update["time_advance"]

    def to_prompt(self) -> str:
        """Generate compressed bullet summary for LLM context."""
        lines = ["=== SESSION STATE ==="]

        # Party
        if self.party_summary:
            lines.append(f"PARTY: {self.party_summary}")

        # Location & Time
        lines.append(f"LOCATION: {self.location} - {self.location_detail}")
        lines.append(f"TIME: {self.time_of_day}, Day {self.days_elapsed + 1}")

        # Combat status
        if self.in_combat:
            init_str = " > ".join(self.initiative_order) if self.initiative_order else "Not set"
            lines.append(f"COMBAT: Active. Initiative: {init_str}")

        # Current objective
        lines.append(f"OBJECTIVE: {self.current_objective}")

        # Active NPCs
        if self.active_npcs:
            lines.append("KEY NPCs:")
            for npc in self.active_npcs:
                lines.append(f"  - {npc.to_str()}")

        # Active quests
        if self.active_quests:
            lines.append("QUESTS:")
            for quest in self.active_quests:
                lines.append(f"  - {quest.to_str()}")

        # Recent events
        if self.recent_events:
            lines.append("RECENT:")
            for event in self.recent_events[-3:]:  # Only last 3 in prompt
                lines.append(f"  - {event}")

        # DM secrets (hidden from players but shown to LLM)
        if self.dm_secrets:
            lines.append("DM NOTES (hidden from players):")
            for secret in self.dm_secrets:
                lines.append(f"  - {secret}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize to dict for storage."""
        return {
            "party_summary": self.party_summary,
            "location": self.location,
            "location_detail": self.location_detail,
            "current_objective": self.current_objective,
            "active_npcs": [{"name": n.name, "attitude": n.attitude, "note": n.note}
                          for n in self.active_npcs],
            "active_quests": [{"title": q.title, "status": q.status, "objective": q.objective}
                            for q in self.active_quests],
            "recent_events": self.recent_events,
            "dm_secrets": self.dm_secrets,
            "in_combat": self.in_combat,
            "initiative_order": self.initiative_order,
            "time_of_day": self.time_of_day,
            "days_elapsed": self.days_elapsed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        """Deserialize from dict."""
        state = cls()
        state.party_summary = data.get("party_summary", "")
        state.location = data.get("location", "The Rusty Dragon Inn")
        state.location_detail = data.get("location_detail", "Main hall, evening")
        state.current_objective = data.get("current_objective", "Begin your adventure")
        state.active_npcs = [NPCInfo(n["name"], n["attitude"], n["note"])
                           for n in data.get("active_npcs", [])]
        state.active_quests = [QuestInfo(q["title"], q["status"], q["objective"])
                             for q in data.get("active_quests", [])]
        state.recent_events = data.get("recent_events", [])
        state.dm_secrets = data.get("dm_secrets", [])
        state.in_combat = data.get("in_combat", False)
        state.initiative_order = data.get("initiative_order", [])
        state.time_of_day = data.get("time_of_day", "evening")
        state.days_elapsed = data.get("days_elapsed", 0)
        return state
