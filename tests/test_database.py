"""Tests for database models and session management."""

import tempfile
from pathlib import Path

import pytest

from src.database.models import (
    Base,
    Campaign,
    Character,
    CombatEncounter,
    InventoryItem,
    NPC,
    Party,
    Quest,
    Session,
)
from src.database.session import (
    close_db,
    get_session,
    init_db,
    reset_db,
    session_scope,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        yield db_path
        close_db()


class TestDatabaseSession:
    """Test database session management."""

    def test_init_db(self, temp_db):
        """Test database initialization."""
        assert temp_db.exists()

    def test_get_session(self, temp_db):
        """Test getting a database session."""
        session = get_session()
        assert session is not None
        session.close()

    def test_session_scope(self, temp_db):
        """Test session scope context manager."""
        with session_scope() as session:
            assert session is not None
            # Session should be active within the context
            assert session.is_active

    def test_reset_db(self, temp_db):
        """Test database reset."""
        # Add some data
        with session_scope() as session:
            campaign = Campaign(name="Test Campaign")
            session.add(campaign)

        # Reset
        reset_db(temp_db)

        # Verify data is gone
        with session_scope() as session:
            campaigns = session.query(Campaign).all()
            assert len(campaigns) == 0


class TestCharacterModel:
    """Test Character model."""

    def test_create_character(self, temp_db):
        """Test creating a character."""
        with session_scope() as session:
            char = Character(
                name="Theron",
                player_name="Player1",
                race="Human",
                character_class="Fighter",
                level=5,
                strength=16,
                dexterity=14,
                constitution=15,
                intelligence=10,
                wisdom=12,
                charisma=8,
            )
            session.add(char)
            session.flush()

            assert char.id is not None
            assert char.name == "Theron"

    def test_ability_modifier(self, temp_db):
        """Test ability modifier calculation."""
        with session_scope() as session:
            char = Character(
                name="Test",
                race="Human",
                character_class="Fighter",
                strength=18,  # +4 modifier
                dexterity=8,  # -1 modifier
                constitution=10,  # +0 modifier
            )
            session.add(char)

            assert char.get_ability_modifier("strength") == 4
            assert char.get_ability_modifier("dexterity") == -1
            assert char.get_ability_modifier("constitution") == 0

    def test_ability_adjustments(self, temp_db):
        """Test ability score adjustments."""
        with session_scope() as session:
            char = Character(
                name="Test",
                race="Human",
                character_class="Fighter",
                strength=14,  # Base
                ability_adjustments={"strength": 4},  # Enhancement bonus
            )
            session.add(char)

            # 14 + 4 = 18, modifier = +4
            assert char.get_ability_modifier("strength") == 4

    def test_character_default_values(self, temp_db):
        """Test character default values."""
        with session_scope() as session:
            char = Character(
                name="Test",
                race="Human",
                character_class="Fighter",
            )
            session.add(char)
            session.flush()

            assert char.level == 1
            assert char.experience == 0
            assert char.max_hp == 1
            assert char.armor_class == 10
            assert char.skills == {}
            assert char.feats == []

    def test_character_json_fields(self, temp_db):
        """Test JSON field storage and retrieval."""
        with session_scope() as session:
            char = Character(
                name="Wizard",
                race="Elf",
                character_class="Wizard",
                spells_known=["Magic Missile", "Shield", "Fireball"],
                feats=["Spell Focus", "Combat Casting"],
                skills={"spellcraft": {"ranks": 5, "class_skill": True}},
            )
            session.add(char)
            session.flush()
            char_id = char.id

        # Retrieve in new session
        with session_scope() as session:
            char = session.query(Character).get(char_id)
            assert "Fireball" in char.spells_known
            assert "Combat Casting" in char.feats
            assert char.skills["spellcraft"]["ranks"] == 5


class TestPartyModel:
    """Test Party model for multiplayer."""

    def test_create_party(self, temp_db):
        """Test creating a party."""
        with session_scope() as session:
            party = Party(name="The Adventurers", shared_gold=500)
            session.add(party)
            session.flush()

            assert party.id is not None

    def test_party_characters_relationship(self, temp_db):
        """Test party-characters relationship."""
        with session_scope() as session:
            party = Party(name="Test Party")
            session.add(party)
            session.flush()

            char1 = Character(
                name="Fighter",
                race="Human",
                character_class="Fighter",
                party_id=party.id,
            )
            char2 = Character(
                name="Wizard",
                race="Elf",
                character_class="Wizard",
                party_id=party.id,
            )
            session.add_all([char1, char2])
            session.flush()

            # Refresh party to load relationship
            session.refresh(party)
            assert len(party.characters) == 2


class TestCampaignModel:
    """Test Campaign model."""

    def test_create_campaign(self, temp_db):
        """Test creating a campaign."""
        with session_scope() as session:
            campaign = Campaign(
                name="Rise of the Runelords",
                description="A Pathfinder adventure path",
                setting="Golarion",
            )
            session.add(campaign)
            session.flush()

            assert campaign.id is not None
            assert campaign.total_sessions == 0

    def test_campaign_world_state(self, temp_db):
        """Test campaign world state JSON storage."""
        with session_scope() as session:
            campaign = Campaign(
                name="Test",
                world_state={
                    "locations": ["Sandpoint", "Magnimar"],
                    "factions": {"Pathfinder Society": "friendly"},
                    "major_events": ["Goblin attack on Sandpoint"],
                },
            )
            session.add(campaign)
            session.flush()
            campaign_id = campaign.id

        with session_scope() as session:
            campaign = session.query(Campaign).get(campaign_id)
            assert "Sandpoint" in campaign.world_state["locations"]


class TestNPCModel:
    """Test NPC model."""

    def test_create_npc(self, temp_db):
        """Test creating an NPC."""
        with session_scope() as session:
            campaign = Campaign(name="Test")
            session.add(campaign)
            session.flush()

            npc = NPC(
                campaign_id=campaign.id,
                name="Ameiko Kaijitsu",
                description="A beautiful Tian woman with a sharp wit",
                role="innkeeper",
                disposition="friendly",
                location="Sandpoint",
            )
            session.add(npc)
            session.flush()

            assert npc.id is not None
            assert npc.is_alive is True

    def test_npc_combat_stats(self, temp_db):
        """Test NPC with combat stats."""
        with session_scope() as session:
            campaign = Campaign(name="Test")
            session.add(campaign)
            session.flush()

            npc = NPC(
                campaign_id=campaign.id,
                name="Goblin",
                is_combatant=True,
                cr=0.33,
                stats={
                    "hp": 6,
                    "ac": 16,
                    "attack": "+2 dogslicer (1d4)",
                    "saves": {"fort": 3, "ref": 4, "will": -1},
                },
            )
            session.add(npc)
            session.flush()

            assert npc.stats["hp"] == 6


class TestQuestModel:
    """Test Quest model."""

    def test_create_quest(self, temp_db):
        """Test creating a quest."""
        with session_scope() as session:
            campaign = Campaign(name="Test")
            session.add(campaign)
            session.flush()

            quest = Quest(
                campaign_id=campaign.id,
                name="The Missing Merchant",
                description="Find the merchant who disappeared",
                quest_giver="Mayor Kendra",
                objectives=[
                    {"description": "Investigate the merchant's shop", "completed": False},
                    {"description": "Track the merchant", "completed": False},
                ],
                rewards={"gold": 200, "xp": 400},
            )
            session.add(quest)
            session.flush()

            assert quest.status == "active"
            assert len(quest.objectives) == 2


class TestInventoryItemModel:
    """Test InventoryItem model."""

    def test_create_item(self, temp_db):
        """Test creating an inventory item."""
        with session_scope() as session:
            char = Character(
                name="Test",
                race="Human",
                character_class="Fighter",
            )
            session.add(char)
            session.flush()

            item = InventoryItem(
                character_id=char.id,
                name="Longsword +1",
                item_type="weapon",
                is_magic=True,
                equipped=True,
                slot="main_hand",
                properties={
                    "damage": "1d8",
                    "damage_type": "slashing",
                    "critical": "19-20/x2",
                    "enhancement": 1,
                },
            )
            session.add(item)
            session.flush()

            assert item.is_magic is True
            assert item.properties["enhancement"] == 1

    def test_item_with_charges(self, temp_db):
        """Test item with charges (wand)."""
        with session_scope() as session:
            char = Character(
                name="Wizard",
                race="Human",
                character_class="Wizard",
            )
            session.add(char)
            session.flush()

            wand = InventoryItem(
                character_id=char.id,
                name="Wand of Magic Missile",
                item_type="wand",
                is_magic=True,
                max_charges=50,
                current_charges=47,
            )
            session.add(wand)
            session.flush()

            assert wand.current_charges == 47


class TestSessionModel:
    """Test Session model."""

    def test_create_session(self, temp_db):
        """Test creating a game session."""
        with session_scope() as db_session:
            campaign = Campaign(name="Test")
            db_session.add(campaign)
            db_session.flush()

            game_session = Session(
                campaign_id=campaign.id,
                session_number=1,
                title="The Beginning",
                summary="The party met in a tavern...",
            )
            db_session.add(game_session)
            db_session.flush()

            assert game_session.id is not None


class TestCombatEncounter:
    """Test CombatEncounter model."""

    def test_create_encounter(self, temp_db):
        """Test creating a combat encounter."""
        with session_scope() as db_session:
            campaign = Campaign(name="Test")
            db_session.add(campaign)
            db_session.flush()

            game_session = Session(campaign_id=campaign.id, session_number=1)
            db_session.add(game_session)
            db_session.flush()

            encounter = CombatEncounter(
                session_id=game_session.id,
                name="Goblin Ambush",
                participants=[
                    {"name": "Fighter", "type": "player", "hp": 45, "ac": 18, "initiative": 15},
                    {"name": "Goblin 1", "type": "enemy", "hp": 6, "ac": 16, "initiative": 12},
                ],
                initiative_order=["Fighter", "Goblin 1"],
            )
            db_session.add(encounter)
            db_session.flush()

            assert encounter.status == "active"
            assert len(encounter.participants) == 2
