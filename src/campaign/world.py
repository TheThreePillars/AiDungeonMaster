"""World state tracking for campaign management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class FactionDisposition(Enum):
    """Disposition of a faction toward the party."""

    HOSTILE = "hostile"
    UNFRIENDLY = "unfriendly"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    ALLIED = "allied"


@dataclass
class Faction:
    """A faction or organization in the world."""

    name: str
    description: str
    disposition: FactionDisposition = FactionDisposition.NEUTRAL
    reputation: int = 0  # -100 to 100
    leader: str = ""
    headquarters: str = ""
    goals: list[str] = field(default_factory=list)
    allies: list[str] = field(default_factory=list)
    enemies: list[str] = field(default_factory=list)
    notes: str = ""

    def modify_reputation(self, amount: int) -> None:
        """Modify reputation with this faction."""
        self.reputation = max(-100, min(100, self.reputation + amount))
        self._update_disposition()

    def _update_disposition(self) -> None:
        """Update disposition based on reputation."""
        if self.reputation <= -50:
            self.disposition = FactionDisposition.HOSTILE
        elif self.reputation <= -20:
            self.disposition = FactionDisposition.UNFRIENDLY
        elif self.reputation <= 20:
            self.disposition = FactionDisposition.NEUTRAL
        elif self.reputation <= 50:
            self.disposition = FactionDisposition.FRIENDLY
        else:
            self.disposition = FactionDisposition.ALLIED


@dataclass
class WorldLocation:
    """A location in the game world."""

    name: str
    location_type: str  # city, town, village, dungeon, wilderness, etc.
    description: str
    region: str = ""
    population: int = 0
    government: str = ""
    notable_npcs: list[str] = field(default_factory=list)
    notable_locations: list[str] = field(default_factory=list)  # Sub-locations
    factions_present: list[str] = field(default_factory=list)
    current_events: list[str] = field(default_factory=list)
    visited: bool = False
    discovered: bool = False
    notes: str = ""

    # Connections to other locations
    connections: dict[str, str] = field(default_factory=dict)  # location: travel_method


@dataclass
class WorldEvent:
    """A significant event in the world."""

    name: str
    description: str
    date: str  # In-game date
    location: str
    participants: list[str] = field(default_factory=list)
    consequences: list[str] = field(default_factory=list)
    party_involved: bool = False
    public_knowledge: bool = True


@dataclass
class CalendarDate:
    """In-game calendar date."""

    year: int = 4720  # Default Golarion year
    month: int = 1
    day: int = 1
    time_of_day: str = "morning"  # morning, afternoon, evening, night

    MONTHS = [
        "Abadius", "Calistril", "Pharast", "Gozran",
        "Desnus", "Sarenith", "Erastus", "Arodus",
        "Rova", "Lamashan", "Neth", "Kuthona"
    ]

    DAYS_IN_MONTH = 30  # Simplified

    def advance_time(self, hours: int = 0, days: int = 0) -> None:
        """Advance the calendar by the specified time."""
        # Handle hours
        time_order = ["morning", "afternoon", "evening", "night"]
        current_idx = time_order.index(self.time_of_day)

        periods_to_advance = hours // 6
        current_idx += periods_to_advance
        days += current_idx // 4
        current_idx = current_idx % 4
        self.time_of_day = time_order[current_idx]

        # Handle days
        self.day += days
        while self.day > self.DAYS_IN_MONTH:
            self.day -= self.DAYS_IN_MONTH
            self.month += 1
            if self.month > 12:
                self.month = 1
                self.year += 1

    def __str__(self) -> str:
        """Get formatted date string."""
        month_name = self.MONTHS[self.month - 1]
        return f"{self.day} {month_name}, {self.year} AR ({self.time_of_day})"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "year": self.year,
            "month": self.month,
            "day": self.day,
            "time_of_day": self.time_of_day,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CalendarDate":
        """Create from dictionary."""
        return cls(
            year=data.get("year", 4720),
            month=data.get("month", 1),
            day=data.get("day", 1),
            time_of_day=data.get("time_of_day", "morning"),
        )


class WorldState:
    """Manages the state of the game world."""

    def __init__(self):
        """Initialize world state."""
        self.locations: dict[str, WorldLocation] = {}
        self.factions: dict[str, Faction] = {}
        self.events: list[WorldEvent] = []
        self.calendar: CalendarDate = CalendarDate()

        # Party location
        self.current_location: str = ""
        self.previous_location: str = ""

        # World-level flags and variables
        self.flags: dict[str, bool] = {}
        self.variables: dict[str, Any] = {}

        # Weather and environment
        self.current_weather: str = "clear"
        self.temperature: str = "mild"

    def add_location(self, location: WorldLocation) -> None:
        """Add a location to the world.

        Args:
            location: Location to add
        """
        self.locations[location.name.lower()] = location

    def get_location(self, name: str) -> WorldLocation | None:
        """Get a location by name.

        Args:
            name: Location name

        Returns:
            WorldLocation or None
        """
        return self.locations.get(name.lower())

    def discover_location(self, name: str) -> bool:
        """Mark a location as discovered.

        Args:
            name: Location name

        Returns:
            True if location exists and was discovered
        """
        location = self.get_location(name)
        if location:
            location.discovered = True
            return True
        return False

    def visit_location(self, name: str) -> bool:
        """Move the party to a location.

        Args:
            name: Location name

        Returns:
            True if successful
        """
        location = self.get_location(name)
        if location:
            self.previous_location = self.current_location
            self.current_location = name
            location.visited = True
            location.discovered = True
            return True
        return False

    def add_faction(self, faction: Faction) -> None:
        """Add a faction to the world.

        Args:
            faction: Faction to add
        """
        self.factions[faction.name.lower()] = faction

    def get_faction(self, name: str) -> Faction | None:
        """Get a faction by name.

        Args:
            name: Faction name

        Returns:
            Faction or None
        """
        return self.factions.get(name.lower())

    def modify_faction_reputation(self, name: str, amount: int) -> bool:
        """Modify reputation with a faction.

        Args:
            name: Faction name
            amount: Reputation change

        Returns:
            True if faction exists
        """
        faction = self.get_faction(name)
        if faction:
            faction.modify_reputation(amount)
            return True
        return False

    def add_event(self, event: WorldEvent) -> None:
        """Add a world event.

        Args:
            event: Event to add
        """
        self.events.append(event)

    def get_recent_events(self, count: int = 5) -> list[WorldEvent]:
        """Get most recent events.

        Args:
            count: Number of events to return

        Returns:
            List of recent events
        """
        return self.events[-count:] if self.events else []

    def set_flag(self, name: str, value: bool = True) -> None:
        """Set a world flag.

        Args:
            name: Flag name
            value: Flag value
        """
        self.flags[name] = value

    def get_flag(self, name: str, default: bool = False) -> bool:
        """Get a world flag.

        Args:
            name: Flag name
            default: Default value if not set

        Returns:
            Flag value
        """
        return self.flags.get(name, default)

    def set_variable(self, name: str, value: Any) -> None:
        """Set a world variable.

        Args:
            name: Variable name
            value: Variable value
        """
        self.variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a world variable.

        Args:
            name: Variable name
            default: Default value

        Returns:
            Variable value
        """
        return self.variables.get(name, default)

    def advance_time(self, hours: int = 0, days: int = 0) -> None:
        """Advance world time.

        Args:
            hours: Hours to advance
            days: Days to advance
        """
        self.calendar.advance_time(hours=hours, days=days)

    def get_discovered_locations(self) -> list[WorldLocation]:
        """Get all discovered locations.

        Returns:
            List of discovered locations
        """
        return [loc for loc in self.locations.values() if loc.discovered]

    def get_visited_locations(self) -> list[WorldLocation]:
        """Get all visited locations.

        Returns:
            List of visited locations
        """
        return [loc for loc in self.locations.values() if loc.visited]

    def get_allied_factions(self) -> list[Faction]:
        """Get factions that are friendly or allied.

        Returns:
            List of friendly/allied factions
        """
        return [
            f for f in self.factions.values()
            if f.disposition in (FactionDisposition.FRIENDLY, FactionDisposition.ALLIED)
        ]

    def get_hostile_factions(self) -> list[Faction]:
        """Get hostile factions.

        Returns:
            List of hostile factions
        """
        return [
            f for f in self.factions.values()
            if f.disposition == FactionDisposition.HOSTILE
        ]

    def to_dict(self) -> dict[str, Any]:
        """Convert world state to dictionary for serialization."""
        return {
            "locations": {
                name: {
                    "name": loc.name,
                    "location_type": loc.location_type,
                    "description": loc.description,
                    "region": loc.region,
                    "visited": loc.visited,
                    "discovered": loc.discovered,
                    "notable_npcs": loc.notable_npcs,
                    "notes": loc.notes,
                }
                for name, loc in self.locations.items()
            },
            "factions": {
                name: {
                    "name": f.name,
                    "description": f.description,
                    "disposition": f.disposition.value,
                    "reputation": f.reputation,
                    "leader": f.leader,
                }
                for name, f in self.factions.items()
            },
            "events": [
                {
                    "name": e.name,
                    "description": e.description,
                    "date": e.date,
                    "location": e.location,
                    "party_involved": e.party_involved,
                }
                for e in self.events
            ],
            "calendar": self.calendar.to_dict(),
            "current_location": self.current_location,
            "flags": self.flags,
            "variables": self.variables,
            "weather": self.current_weather,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldState":
        """Create world state from dictionary.

        Args:
            data: Serialized world state

        Returns:
            WorldState instance
        """
        state = cls()

        # Load locations
        for name, loc_data in data.get("locations", {}).items():
            location = WorldLocation(
                name=loc_data.get("name", name),
                location_type=loc_data.get("location_type", "unknown"),
                description=loc_data.get("description", ""),
                region=loc_data.get("region", ""),
                visited=loc_data.get("visited", False),
                discovered=loc_data.get("discovered", False),
                notable_npcs=loc_data.get("notable_npcs", []),
                notes=loc_data.get("notes", ""),
            )
            state.locations[name] = location

        # Load factions
        for name, f_data in data.get("factions", {}).items():
            faction = Faction(
                name=f_data.get("name", name),
                description=f_data.get("description", ""),
                disposition=FactionDisposition(f_data.get("disposition", "neutral")),
                reputation=f_data.get("reputation", 0),
                leader=f_data.get("leader", ""),
            )
            state.factions[name] = faction

        # Load events
        for e_data in data.get("events", []):
            event = WorldEvent(
                name=e_data.get("name", ""),
                description=e_data.get("description", ""),
                date=e_data.get("date", ""),
                location=e_data.get("location", ""),
                party_involved=e_data.get("party_involved", False),
            )
            state.events.append(event)

        # Load other state
        state.calendar = CalendarDate.from_dict(data.get("calendar", {}))
        state.current_location = data.get("current_location", "")
        state.flags = data.get("flags", {})
        state.variables = data.get("variables", {})
        state.current_weather = data.get("weather", "clear")

        return state
