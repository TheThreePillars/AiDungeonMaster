"""Tests for campaign module."""

import pytest

from src.campaign.quests import (
    ObjectiveStatus,
    Quest,
    QuestObjective,
    QuestReward,
    QuestStatus,
    QuestTracker,
    QuestType,
)
from src.campaign.npcs import (
    NPC,
    NPCDisposition,
    NPCManager,
    NPCPersonality,
    NPCRole,
)
from src.campaign.world import (
    CalendarDate,
    Faction,
    FactionDisposition,
    WorldEvent,
    WorldLocation,
    WorldState,
)
from src.campaign.generator import (
    CampaignGenerator,
    Encounter,
    Location,
    PlotHook,
)


class TestQuestObjective:
    """Tests for QuestObjective class."""

    def test_objective_creation(self):
        """Test basic objective creation."""
        obj = QuestObjective(description="Kill the dragon")
        assert obj.description == "Kill the dragon"
        assert obj.status == ObjectiveStatus.INCOMPLETE
        assert obj.progress == 0
        assert obj.target == 1
        assert not obj.is_complete

    def test_objective_progress(self):
        """Test objective progress tracking."""
        obj = QuestObjective(description="Collect 5 gems", target=5)
        assert not obj.is_complete

        obj.update_progress(2)
        assert obj.progress == 2
        assert not obj.is_complete

        obj.update_progress(3)
        assert obj.progress == 5
        assert obj.is_complete
        assert obj.status == ObjectiveStatus.COMPLETE

    def test_objective_serialization(self):
        """Test objective to_dict and from_dict."""
        obj = QuestObjective(
            description="Test objective",
            status=ObjectiveStatus.COMPLETE,
            is_optional=True,
            progress=5,
            target=5,
        )

        data = obj.to_dict()
        restored = QuestObjective.from_dict(data)

        assert restored.description == obj.description
        assert restored.status == obj.status
        assert restored.is_optional == obj.is_optional
        assert restored.progress == obj.progress


class TestQuest:
    """Tests for Quest class."""

    def test_quest_creation(self):
        """Test basic quest creation."""
        quest = Quest(
            name="Dragon Slayer",
            description="Defeat the dragon threatening the village",
            quest_type=QuestType.MAIN,
        )

        assert quest.name == "Dragon Slayer"
        assert quest.quest_type == QuestType.MAIN
        assert quest.status == QuestStatus.AVAILABLE

    def test_quest_lifecycle(self):
        """Test quest start, complete, fail, abandon."""
        quest = Quest(name="Test Quest", description="A test")

        # Start
        quest.start()
        assert quest.status == QuestStatus.ACTIVE
        assert quest.started_at != ""

        # Complete
        quest.complete()
        assert quest.status == QuestStatus.COMPLETED
        assert quest.completed_at != ""

    def test_quest_objectives(self):
        """Test quest objective management."""
        quest = Quest(name="Multi-objective", description="Test")

        quest.add_objective("Step 1")
        quest.add_objective("Step 2")
        quest.add_objective("Optional step", is_optional=True)

        assert len(quest.objectives) == 3
        assert not quest.is_complete

        # Complete required objectives
        quest.objectives[0].status = ObjectiveStatus.COMPLETE
        quest.objectives[1].status = ObjectiveStatus.COMPLETE

        assert quest.is_complete

    def test_quest_progress_percentage(self):
        """Test progress calculation."""
        quest = Quest(name="Progress Test", description="Test")

        quest.add_objective("Step 1")
        quest.add_objective("Step 2")
        quest.add_objective("Step 3")
        quest.add_objective("Optional", is_optional=True)

        assert quest.progress_percentage == 0.0

        quest.objectives[0].status = ObjectiveStatus.COMPLETE
        assert quest.progress_percentage == pytest.approx(33.33, rel=0.1)

        quest.objectives[1].status = ObjectiveStatus.COMPLETE
        quest.objectives[2].status = ObjectiveStatus.COMPLETE
        assert quest.progress_percentage == 100.0

    def test_quest_serialization(self):
        """Test quest serialization."""
        quest = Quest(
            name="Serialization Test",
            description="Test quest",
            quest_type=QuestType.SIDE,
            quest_giver="Test NPC",
        )
        quest.add_objective("Test objective")
        quest.rewards = QuestReward(gold=100, xp=500)

        data = quest.to_dict()
        restored = Quest.from_dict(data)

        assert restored.name == quest.name
        assert restored.quest_type == quest.quest_type
        assert restored.quest_giver == quest.quest_giver
        assert len(restored.objectives) == 1
        assert restored.rewards.gold == 100


class TestQuestTracker:
    """Tests for QuestTracker class."""

    def test_add_quest(self):
        """Test adding quests."""
        tracker = QuestTracker()

        quest = Quest(name="Test Quest", description="A test")
        quest_id = tracker.add_quest(quest)

        assert quest_id.startswith("quest_")
        assert quest.id == quest_id
        assert tracker.get_quest(quest_id) == quest

    def test_find_quest_by_name(self):
        """Test finding quests by name."""
        tracker = QuestTracker()

        quest1 = Quest(name="Dragon Hunt", description="Hunt the dragon")
        quest2 = Quest(name="Goblin Raid", description="Stop the goblins")

        tracker.add_quest(quest1)
        tracker.add_quest(quest2)

        found = tracker.find_quest_by_name("dragon")
        assert found == quest1

        found = tracker.find_quest_by_name("goblin")
        assert found == quest2

    def test_get_quests_by_status(self):
        """Test filtering quests by status."""
        tracker = QuestTracker()

        quest1 = Quest(name="Q1", description="")
        quest2 = Quest(name="Q2", description="")
        quest3 = Quest(name="Q3", description="")

        tracker.add_quest(quest1)
        tracker.add_quest(quest2)
        tracker.add_quest(quest3)

        quest1.start()
        quest2.start()
        quest2.complete()

        active = tracker.get_active_quests()
        assert len(active) == 1
        assert quest1 in active

        available = tracker.get_available_quests()
        assert len(available) == 1
        assert quest3 in available

        completed = tracker.get_completed_quests()
        assert len(completed) == 1
        assert quest2 in completed


class TestNPC:
    """Tests for NPC class."""

    def test_npc_creation(self):
        """Test basic NPC creation."""
        npc = NPC(
            name="John the Blacksmith",
            race="Human",
            occupation="blacksmith",
            role=NPCRole.MERCHANT,
        )

        assert npc.name == "John the Blacksmith"
        assert npc.race == "Human"
        assert npc.role == NPCRole.MERCHANT
        assert npc.disposition == NPCDisposition.INDIFFERENT

    def test_trust_and_disposition(self):
        """Test trust level affecting disposition."""
        npc = NPC(name="Test NPC", race="Human")

        # Start neutral
        assert npc.disposition == NPCDisposition.INDIFFERENT

        # Increase trust
        npc.modify_trust(30)
        assert npc.trust_level == 30
        assert npc.disposition == NPCDisposition.FRIENDLY

        # Increase more
        npc.modify_trust(30)
        assert npc.trust_level == 60
        assert npc.disposition == NPCDisposition.HELPFUL

        # Decrease dramatically
        npc.modify_trust(-120)
        assert npc.trust_level == -60
        assert npc.disposition == NPCDisposition.HOSTILE

    def test_npc_interactions(self):
        """Test recording interactions."""
        npc = NPC(name="Test NPC", race="Human")

        assert not npc.met_before
        assert len(npc.interactions) == 0

        npc.add_interaction("Met at the tavern")
        assert npc.met_before
        assert len(npc.interactions) == 1

    def test_npc_serialization(self):
        """Test NPC serialization."""
        npc = NPC(
            name="Test NPC",
            race="Elf",
            occupation="wizard",
            knowledge=["Secret spell"],
        )

        data = npc.to_dict()
        restored = NPC.from_dict(data)

        assert restored.name == npc.name
        assert restored.race == npc.race
        assert restored.knowledge == npc.knowledge


class TestNPCManager:
    """Tests for NPCManager class."""

    def test_add_and_get_npc(self):
        """Test adding and retrieving NPCs."""
        manager = NPCManager()

        npc = NPC(name="Test NPC", race="Human")
        manager.add_npc(npc)

        retrieved = manager.get_npc("Test NPC")
        assert retrieved == npc

        # Case insensitive
        retrieved = manager.get_npc("test npc")
        assert retrieved == npc

    def test_get_npcs_at_location(self):
        """Test filtering NPCs by location."""
        manager = NPCManager()

        npc1 = NPC(name="NPC1", race="Human", location="Tavern")
        npc2 = NPC(name="NPC2", race="Human", location="Tavern")
        npc3 = NPC(name="NPC3", race="Human", location="Market")

        manager.add_npc(npc1)
        manager.add_npc(npc2)
        manager.add_npc(npc3)

        tavern_npcs = manager.get_npcs_at_location("Tavern")
        assert len(tavern_npcs) == 2
        assert npc1 in tavern_npcs
        assert npc2 in tavern_npcs

    def test_random_npc_generation(self):
        """Test random NPC generation without AI."""
        manager = NPCManager()

        npc = manager._generate_random_npc(
            role=NPCRole.MERCHANT,
            location="Market",
            occupation="",
            race="",
        )

        assert npc.name != ""
        assert npc.race != ""
        assert npc.occupation != ""
        assert npc.location == "Market"
        assert npc.role == NPCRole.MERCHANT


class TestWorldState:
    """Tests for WorldState class."""

    def test_location_management(self):
        """Test adding and visiting locations."""
        state = WorldState()

        location = WorldLocation(
            name="Test Town",
            location_type="town",
            description="A small town",
        )
        state.add_location(location)

        retrieved = state.get_location("Test Town")
        assert retrieved == location
        assert not retrieved.visited

        state.visit_location("Test Town")
        assert retrieved.visited
        assert retrieved.discovered
        assert state.current_location == "Test Town"

    def test_faction_reputation(self):
        """Test faction reputation management."""
        state = WorldState()

        faction = Faction(
            name="Thieves Guild",
            description="A shadowy organization",
        )
        state.add_faction(faction)

        assert faction.disposition == FactionDisposition.NEUTRAL

        state.modify_faction_reputation("Thieves Guild", 30)
        assert faction.reputation == 30
        assert faction.disposition == FactionDisposition.FRIENDLY

    def test_calendar_advancement(self):
        """Test calendar time advancement."""
        state = WorldState()

        # Initial state
        assert state.calendar.year == 4720
        assert state.calendar.time_of_day == "morning"

        # Advance time
        state.advance_time(hours=12)
        assert state.calendar.time_of_day == "evening"

        state.advance_time(days=5)
        assert state.calendar.day == 6

    def test_world_flags(self):
        """Test world state flags."""
        state = WorldState()

        assert not state.get_flag("dragon_defeated")

        state.set_flag("dragon_defeated", True)
        assert state.get_flag("dragon_defeated")

    def test_serialization(self):
        """Test world state serialization."""
        state = WorldState()

        location = WorldLocation(
            name="Test",
            location_type="town",
            description="Test",
        )
        state.add_location(location)
        state.set_flag("test_flag", True)

        data = state.to_dict()
        restored = WorldState.from_dict(data)

        assert restored.get_location("test") is not None
        assert restored.get_flag("test_flag")


class TestCalendarDate:
    """Tests for CalendarDate class."""

    def test_initial_date(self):
        """Test initial date values."""
        date = CalendarDate()

        assert date.year == 4720
        assert date.month == 1
        assert date.day == 1
        assert date.time_of_day == "morning"

    def test_advance_hours(self):
        """Test advancing time by hours."""
        date = CalendarDate()

        # Morning to afternoon (6 hours)
        date.advance_time(hours=6)
        assert date.time_of_day == "afternoon"

        # Afternoon to evening
        date.advance_time(hours=6)
        assert date.time_of_day == "evening"

        # Evening to night
        date.advance_time(hours=6)
        assert date.time_of_day == "night"

        # Night to next day morning
        date.advance_time(hours=6)
        assert date.time_of_day == "morning"
        assert date.day == 2

    def test_advance_days(self):
        """Test advancing by days."""
        date = CalendarDate(day=28)

        date.advance_time(days=5)
        assert date.day == 3
        assert date.month == 2

    def test_month_rollover(self):
        """Test month and year rollover."""
        date = CalendarDate(month=12, day=28)

        date.advance_time(days=5)
        assert date.month == 1
        assert date.year == 4721

    def test_string_format(self):
        """Test date string formatting."""
        date = CalendarDate(year=4720, month=3, day=15, time_of_day="afternoon")

        result = str(date)
        assert "15" in result
        assert "Pharast" in result
        assert "4720" in result
        assert "afternoon" in result


class TestCampaignGenerator:
    """Tests for CampaignGenerator class."""

    def test_random_plot_hook(self):
        """Test random plot hook generation."""
        generator = CampaignGenerator()

        hook = generator._generate_random_plot_hook(party_level=3)

        assert hook.title != ""
        assert hook.description != ""
        assert hook.hook_type in ["mystery", "exploration", "social", "combat", "rescue"]
        assert hook.rewards != {}

    def test_random_encounter(self):
        """Test random encounter generation."""
        generator = CampaignGenerator()

        encounter = generator._generate_random_encounter(
            party_level=3,
            difficulty="medium",
        )

        assert encounter.name != ""
        assert encounter.description != ""
        assert len(encounter.enemies) > 0
        assert encounter.xp_reward > 0

    def test_random_location(self):
        """Test random location generation."""
        generator = CampaignGenerator()

        location = generator._generate_random_location("dungeon")

        assert location.name != ""
        assert location.description != ""
        assert len(location.notable_features) > 0

    def test_simple_recap(self):
        """Test simple recap generation."""
        generator = CampaignGenerator()

        recap = generator._generate_simple_recap(
            events=["fought goblins", "found treasure"],
            npcs_met=["Garrick the Blacksmith"],
            locations_visited=["Old Mill", "Forest Path"],
        )

        assert "heroes" in recap.lower()
        assert "Old Mill" in recap
        assert "Garrick" in recap


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
