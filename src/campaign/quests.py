"""Quest tracking and management for campaigns."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class QuestStatus(Enum):
    """Status of a quest."""

    AVAILABLE = "available"  # Known but not started
    ACTIVE = "active"  # Currently being worked on
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"  # Failed to complete
    ABANDONED = "abandoned"  # Given up by party


class QuestType(Enum):
    """Type of quest."""

    MAIN = "main"  # Main storyline
    SIDE = "side"  # Optional side quest
    PERSONAL = "personal"  # Character-specific
    FACTION = "faction"  # Faction-related
    BOUNTY = "bounty"  # Kill/capture target
    FETCH = "fetch"  # Retrieve item
    ESCORT = "escort"  # Protect someone
    EXPLORATION = "exploration"  # Discover location
    MYSTERY = "mystery"  # Solve a puzzle/mystery


class ObjectiveStatus(Enum):
    """Status of a quest objective."""

    INCOMPLETE = "incomplete"
    COMPLETE = "complete"
    FAILED = "failed"
    OPTIONAL = "optional"


@dataclass
class QuestObjective:
    """A single objective within a quest."""

    description: str
    status: ObjectiveStatus = ObjectiveStatus.INCOMPLETE
    is_optional: bool = False
    is_hidden: bool = False  # Revealed later
    progress: int = 0  # For objectives with counts
    target: int = 1  # Target count
    notes: str = ""

    @property
    def is_complete(self) -> bool:
        """Check if objective is complete."""
        return self.status == ObjectiveStatus.COMPLETE or self.progress >= self.target

    def update_progress(self, amount: int = 1) -> bool:
        """Update progress on objective.

        Args:
            amount: Amount to add

        Returns:
            True if objective is now complete
        """
        self.progress = min(self.progress + amount, self.target)
        if self.progress >= self.target:
            self.status = ObjectiveStatus.COMPLETE
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "description": self.description,
            "status": self.status.value,
            "is_optional": self.is_optional,
            "is_hidden": self.is_hidden,
            "progress": self.progress,
            "target": self.target,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuestObjective":
        """Create from dictionary."""
        return cls(
            description=data.get("description", ""),
            status=ObjectiveStatus(data.get("status", "incomplete")),
            is_optional=data.get("is_optional", False),
            is_hidden=data.get("is_hidden", False),
            progress=data.get("progress", 0),
            target=data.get("target", 1),
            notes=data.get("notes", ""),
        )


@dataclass
class QuestReward:
    """Rewards for completing a quest."""

    gold: int = 0
    xp: int = 0
    items: list[str] = field(default_factory=list)
    reputation: dict[str, int] = field(default_factory=dict)  # faction: amount
    special: str = ""  # Special reward description


@dataclass
class Quest:
    """A quest or mission."""

    name: str
    description: str
    quest_type: QuestType = QuestType.SIDE
    status: QuestStatus = QuestStatus.AVAILABLE

    # Quest giver
    quest_giver: str = ""
    quest_giver_location: str = ""

    # Objectives
    objectives: list[QuestObjective] = field(default_factory=list)

    # Rewards
    rewards: QuestReward = field(default_factory=QuestReward)

    # Related elements
    related_npcs: list[str] = field(default_factory=list)
    related_locations: list[str] = field(default_factory=list)

    # Discovered information
    clues: list[str] = field(default_factory=list)
    notes: str = ""

    # Timing
    time_limit: str = ""  # e.g., "3 days", "" for no limit
    started_at: str = ""
    completed_at: str = ""

    # For tracking
    id: str = ""

    @property
    def is_complete(self) -> bool:
        """Check if all required objectives are complete."""
        required = [o for o in self.objectives if not o.is_optional]
        return all(o.is_complete for o in required)

    @property
    def progress_percentage(self) -> float:
        """Calculate completion percentage."""
        if not self.objectives:
            return 0.0

        required = [o for o in self.objectives if not o.is_optional]
        if not required:
            return 100.0 if self.status == QuestStatus.COMPLETED else 0.0

        completed = sum(1 for o in required if o.is_complete)
        return (completed / len(required)) * 100

    @property
    def visible_objectives(self) -> list[QuestObjective]:
        """Get objectives that are visible (not hidden)."""
        return [o for o in self.objectives if not o.is_hidden]

    def start(self) -> None:
        """Start the quest."""
        self.status = QuestStatus.ACTIVE
        self.started_at = datetime.now().isoformat()

    def complete(self) -> None:
        """Mark quest as completed."""
        self.status = QuestStatus.COMPLETED
        self.completed_at = datetime.now().isoformat()

    def fail(self) -> None:
        """Mark quest as failed."""
        self.status = QuestStatus.FAILED
        self.completed_at = datetime.now().isoformat()

    def abandon(self) -> None:
        """Abandon the quest."""
        self.status = QuestStatus.ABANDONED
        self.completed_at = datetime.now().isoformat()

    def add_objective(self, description: str, is_optional: bool = False, is_hidden: bool = False) -> QuestObjective:
        """Add a new objective.

        Args:
            description: Objective description
            is_optional: Whether objective is optional
            is_hidden: Whether objective is hidden initially

        Returns:
            The created objective
        """
        objective = QuestObjective(
            description=description,
            is_optional=is_optional,
            is_hidden=is_hidden,
        )
        self.objectives.append(objective)
        return objective

    def reveal_objective(self, index: int) -> bool:
        """Reveal a hidden objective.

        Args:
            index: Objective index

        Returns:
            True if revealed
        """
        if 0 <= index < len(self.objectives):
            self.objectives[index].is_hidden = False
            return True
        return False

    def add_clue(self, clue: str) -> None:
        """Add a clue discovered during the quest."""
        if clue not in self.clues:
            self.clues.append(clue)

    def get_summary(self) -> str:
        """Get a brief summary of the quest."""
        status_icon = {
            QuestStatus.AVAILABLE: "○",
            QuestStatus.ACTIVE: "●",
            QuestStatus.COMPLETED: "✓",
            QuestStatus.FAILED: "✗",
            QuestStatus.ABANDONED: "—",
        }

        icon = status_icon.get(self.status, "?")
        progress = f" ({self.progress_percentage:.0f}%)" if self.status == QuestStatus.ACTIVE else ""

        return f"{icon} [{self.quest_type.value.upper()}] {self.name}{progress}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "quest_type": self.quest_type.value,
            "status": self.status.value,
            "quest_giver": self.quest_giver,
            "quest_giver_location": self.quest_giver_location,
            "objectives": [o.to_dict() for o in self.objectives],
            "rewards": {
                "gold": self.rewards.gold,
                "xp": self.rewards.xp,
                "items": self.rewards.items,
                "reputation": self.rewards.reputation,
                "special": self.rewards.special,
            },
            "related_npcs": self.related_npcs,
            "related_locations": self.related_locations,
            "clues": self.clues,
            "notes": self.notes,
            "time_limit": self.time_limit,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Quest":
        """Create quest from dictionary."""
        rewards_data = data.get("rewards", {})
        rewards = QuestReward(
            gold=rewards_data.get("gold", 0),
            xp=rewards_data.get("xp", 0),
            items=rewards_data.get("items", []),
            reputation=rewards_data.get("reputation", {}),
            special=rewards_data.get("special", ""),
        )

        objectives = [
            QuestObjective.from_dict(o)
            for o in data.get("objectives", [])
        ]

        return cls(
            id=data.get("id", ""),
            name=data.get("name", "Unnamed Quest"),
            description=data.get("description", ""),
            quest_type=QuestType(data.get("quest_type", "side")),
            status=QuestStatus(data.get("status", "available")),
            quest_giver=data.get("quest_giver", ""),
            quest_giver_location=data.get("quest_giver_location", ""),
            objectives=objectives,
            rewards=rewards,
            related_npcs=data.get("related_npcs", []),
            related_locations=data.get("related_locations", []),
            clues=data.get("clues", []),
            notes=data.get("notes", ""),
            time_limit=data.get("time_limit", ""),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
        )


class QuestTracker:
    """Tracks all quests in a campaign."""

    def __init__(self):
        """Initialize quest tracker."""
        self.quests: dict[str, Quest] = {}
        self._next_id: int = 1

    def add_quest(self, quest: Quest) -> str:
        """Add a quest to the tracker.

        Args:
            quest: Quest to add

        Returns:
            Quest ID
        """
        if not quest.id:
            quest.id = f"quest_{self._next_id}"
            self._next_id += 1

        self.quests[quest.id] = quest
        return quest.id

    def get_quest(self, quest_id: str) -> Quest | None:
        """Get a quest by ID.

        Args:
            quest_id: Quest ID

        Returns:
            Quest or None
        """
        return self.quests.get(quest_id)

    def find_quest_by_name(self, name: str) -> Quest | None:
        """Find a quest by name.

        Args:
            name: Quest name (partial match)

        Returns:
            Quest or None
        """
        name_lower = name.lower()
        for quest in self.quests.values():
            if name_lower in quest.name.lower():
                return quest
        return None

    def get_active_quests(self) -> list[Quest]:
        """Get all active quests."""
        return [q for q in self.quests.values() if q.status == QuestStatus.ACTIVE]

    def get_available_quests(self) -> list[Quest]:
        """Get all available (not started) quests."""
        return [q for q in self.quests.values() if q.status == QuestStatus.AVAILABLE]

    def get_completed_quests(self) -> list[Quest]:
        """Get all completed quests."""
        return [q for q in self.quests.values() if q.status == QuestStatus.COMPLETED]

    def get_main_quests(self) -> list[Quest]:
        """Get all main storyline quests."""
        return [q for q in self.quests.values() if q.quest_type == QuestType.MAIN]

    def get_quests_by_giver(self, npc_name: str) -> list[Quest]:
        """Get all quests from a specific NPC.

        Args:
            npc_name: NPC name

        Returns:
            List of quests from that NPC
        """
        name_lower = npc_name.lower()
        return [
            q for q in self.quests.values()
            if q.quest_giver.lower() == name_lower
        ]

    def get_quests_at_location(self, location: str) -> list[Quest]:
        """Get quests related to a location.

        Args:
            location: Location name

        Returns:
            List of related quests
        """
        location_lower = location.lower()
        return [
            q for q in self.quests.values()
            if location_lower in [loc.lower() for loc in q.related_locations]
            or q.quest_giver_location.lower() == location_lower
        ]

    def start_quest(self, quest_id: str) -> bool:
        """Start a quest.

        Args:
            quest_id: Quest ID

        Returns:
            True if started
        """
        quest = self.get_quest(quest_id)
        if quest and quest.status == QuestStatus.AVAILABLE:
            quest.start()
            return True
        return False

    def complete_quest(self, quest_id: str) -> QuestReward | None:
        """Complete a quest and get rewards.

        Args:
            quest_id: Quest ID

        Returns:
            Quest rewards or None
        """
        quest = self.get_quest(quest_id)
        if quest and quest.status == QuestStatus.ACTIVE and quest.is_complete:
            quest.complete()
            return quest.rewards
        return None

    def fail_quest(self, quest_id: str) -> bool:
        """Fail a quest.

        Args:
            quest_id: Quest ID

        Returns:
            True if failed
        """
        quest = self.get_quest(quest_id)
        if quest and quest.status == QuestStatus.ACTIVE:
            quest.fail()
            return True
        return False

    def update_objective(self, quest_id: str, objective_index: int, progress: int = 1) -> bool:
        """Update progress on a quest objective.

        Args:
            quest_id: Quest ID
            objective_index: Index of objective
            progress: Progress to add

        Returns:
            True if objective is now complete
        """
        quest = self.get_quest(quest_id)
        if quest and 0 <= objective_index < len(quest.objectives):
            return quest.objectives[objective_index].update_progress(progress)
        return False

    def complete_objective(self, quest_id: str, objective_index: int) -> bool:
        """Mark an objective as complete.

        Args:
            quest_id: Quest ID
            objective_index: Index of objective

        Returns:
            True if marked complete
        """
        quest = self.get_quest(quest_id)
        if quest and 0 <= objective_index < len(quest.objectives):
            quest.objectives[objective_index].status = ObjectiveStatus.COMPLETE
            return True
        return False

    def get_quest_log(self) -> str:
        """Get a formatted quest log.

        Returns:
            Formatted string of all quests
        """
        lines = ["=== QUEST LOG ===\n"]

        # Active quests
        active = self.get_active_quests()
        if active:
            lines.append("ACTIVE QUESTS:")
            for quest in active:
                lines.append(f"  {quest.get_summary()}")
                for i, obj in enumerate(quest.visible_objectives):
                    status = "✓" if obj.is_complete else "○"
                    optional = " (optional)" if obj.is_optional else ""
                    progress = f" [{obj.progress}/{obj.target}]" if obj.target > 1 else ""
                    lines.append(f"    {status} {obj.description}{progress}{optional}")
            lines.append("")

        # Available quests
        available = self.get_available_quests()
        if available:
            lines.append("AVAILABLE QUESTS:")
            for quest in available:
                lines.append(f"  {quest.get_summary()}")
            lines.append("")

        # Completed quests (last 5)
        completed = self.get_completed_quests()[-5:]
        if completed:
            lines.append("RECENTLY COMPLETED:")
            for quest in completed:
                lines.append(f"  {quest.get_summary()}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "quests": {qid: q.to_dict() for qid, q in self.quests.items()},
            "next_id": self._next_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuestTracker":
        """Create from dictionary."""
        tracker = cls()
        tracker._next_id = data.get("next_id", 1)

        for qid, quest_data in data.get("quests", {}).items():
            quest = Quest.from_dict(quest_data)
            quest.id = qid
            tracker.quests[qid] = quest

        return tracker
