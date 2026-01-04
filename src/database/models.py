"""SQLAlchemy database models for AI Dungeon Master - Pathfinder 1e."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class Party(Base):
    """Party model for multiplayer support - groups characters together."""

    __tablename__ = "parties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    shared_gold = Column(Integer, default=0)  # Party treasury
    shared_inventory = Column(JSON, default=list)  # Shared items
    notes = Column(Text, nullable=True)  # Party notes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    characters = relationship("Character", back_populates="party")
    campaign = relationship("Campaign", back_populates="parties")


class Character(Base):
    """Character model with full Pathfinder 1e support."""

    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    player_name = Column(String(100), nullable=True)  # For multiplayer
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)

    # Basic Info
    race = Column(String(50), nullable=False)
    character_class = Column(String(50), nullable=False)  # Primary class
    classes = Column(JSON, default=dict)  # For multiclassing: {"fighter": 5, "rogue": 3}
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    alignment = Column(String(20), nullable=True)
    deity = Column(String(50), nullable=True)
    size = Column(String(20), default="Medium")
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    height = Column(String(20), nullable=True)
    weight = Column(String(20), nullable=True)

    # Ability Scores (base values, before racial modifiers)
    strength = Column(Integer, default=10)
    dexterity = Column(Integer, default=10)
    constitution = Column(Integer, default=10)
    intelligence = Column(Integer, default=10)
    wisdom = Column(Integer, default=10)
    charisma = Column(Integer, default=10)

    # Ability Score Adjustments (racial, enhancement, etc.)
    ability_adjustments = Column(JSON, default=dict)

    # Combat Stats
    max_hp = Column(Integer, default=1)
    current_hp = Column(Integer, default=1)
    temp_hp = Column(Integer, default=0)
    nonlethal_damage = Column(Integer, default=0)  # PF1e tracks nonlethal separately
    armor_class = Column(Integer, default=10)
    touch_ac = Column(Integer, default=10)  # PF1e touch AC
    flat_footed_ac = Column(Integer, default=10)  # PF1e flat-footed AC
    base_attack_bonus = Column(Integer, default=0)  # BAB
    initiative_modifier = Column(Integer, default=0)
    speed = Column(Integer, default=30)  # Base land speed

    # PF1e Combat Maneuvers
    cmb = Column(Integer, default=0)  # Combat Maneuver Bonus
    cmd = Column(Integer, default=10)  # Combat Maneuver Defense

    # Saving Throws (base values from class)
    fortitude_base = Column(Integer, default=0)
    reflex_base = Column(Integer, default=0)
    will_base = Column(Integer, default=0)

    # Skills (JSON: {"acrobatics": {"ranks": 5, "class_skill": true, "misc": 0}, ...})
    skills = Column(JSON, default=dict)
    skill_points_remaining = Column(Integer, default=0)

    # Feats and Traits
    feats = Column(JSON, default=list)  # List of feat names
    traits = Column(JSON, default=list)  # PF1e character traits (2 at creation)
    special_abilities = Column(JSON, default=list)  # Class features, racial abilities

    # Spellcasting (if applicable)
    spellcaster = Column(Boolean, default=False)
    caster_level = Column(Integer, default=0)
    spell_slots = Column(JSON, default=dict)  # {"1": {"max": 3, "used": 1}, ...}
    spells_known = Column(JSON, default=list)  # List of spell names
    spells_prepared = Column(JSON, default=list)  # For prepared casters
    concentration_bonus = Column(Integer, default=0)
    spell_dc_base = Column(Integer, default=10)

    # Background and Roleplay
    background = Column(String(50), nullable=True)
    backstory = Column(Text, nullable=True)
    personality_traits = Column(Text, nullable=True)
    ideals = Column(Text, nullable=True)
    bonds = Column(Text, nullable=True)
    flaws = Column(Text, nullable=True)
    languages = Column(JSON, default=list)

    # Wealth
    platinum = Column(Integer, default=0)
    gold = Column(Integer, default=0)
    silver = Column(Integer, default=0)
    copper = Column(Integer, default=0)

    # Conditions and Status
    conditions = Column(JSON, default=list)  # Active conditions
    death_saves = Column(JSON, default=dict)  # {"successes": 0, "failures": 0}

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    party = relationship("Party", back_populates="characters")
    campaign = relationship("Campaign", back_populates="characters")
    inventory = relationship("InventoryItem", back_populates="character", cascade="all, delete-orphan")

    def get_ability_modifier(self, ability: str) -> int:
        """Calculate ability modifier for a given ability score.

        Args:
            ability: Ability name (strength, dexterity, etc.)

        Returns:
            The ability modifier (score - 10) // 2
        """
        score = getattr(self, ability.lower(), 10)
        # Add any adjustments
        adjustments = self.ability_adjustments or {}
        score += adjustments.get(ability.lower(), 0)
        return (score - 10) // 2


class Campaign(Base):
    """Campaign model for tracking game sessions and world state."""

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    setting = Column(String(100), nullable=True)  # e.g., "Golarion", "Homebrew"

    # World State (JSON for flexibility)
    world_state = Column(JSON, default=dict)  # Locations, factions, major events
    current_location = Column(String(100), nullable=True)
    calendar_date = Column(String(50), nullable=True)  # In-game date

    # Campaign Progress
    current_session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    total_sessions = Column(Integer, default=0)

    # Experience Track (slow, medium, fast)
    experience_track = Column(String(20), default="medium")

    # House Rules
    house_rules = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parties = relationship("Party", back_populates="campaign")
    characters = relationship("Character", back_populates="campaign")
    sessions = relationship(
        "Session",
        back_populates="campaign",
        foreign_keys="Session.campaign_id",
    )
    npcs = relationship("NPC", back_populates="campaign", cascade="all, delete-orphan")
    quests = relationship("Quest", back_populates="campaign", cascade="all, delete-orphan")


class Session(Base):
    """Session model for tracking individual play sessions."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    session_number = Column(Integer, nullable=False)

    # Session Content
    title = Column(String(200), nullable=True)  # Session title/name
    summary = Column(Text, nullable=True)  # AI-generated or manual recap
    events = Column(JSON, default=list)  # Array of significant events
    combat_encounters = Column(JSON, default=list)  # Combat summaries
    npcs_introduced = Column(JSON, default=list)  # NPCs met this session
    locations_visited = Column(JSON, default=list)  # Places visited
    loot_acquired = Column(JSON, default=list)  # Items/gold found
    experience_awarded = Column(Integer, default=0)

    # Conversation Log
    conversation_log = Column(JSON, default=list)  # Full message history

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    # Relationships
    campaign = relationship(
        "Campaign",
        back_populates="sessions",
        foreign_keys=[campaign_id],
    )


class NPC(Base):
    """NPC model for non-player characters."""

    __tablename__ = "npcs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)

    # Basic Info
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)  # Physical description
    personality = Column(Text, nullable=True)  # Personality traits
    voice_notes = Column(String(200), nullable=True)  # How to roleplay them

    # Role and Status
    role = Column(String(50), nullable=True)  # merchant, guard, villain, etc.
    disposition = Column(String(20), default="neutral")  # friendly, neutral, hostile
    faction = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)
    is_alive = Column(Boolean, default=True)

    # Relationship to Party
    relationship_to_party = Column(Text, nullable=True)
    trust_level = Column(Integer, default=0)  # -100 to 100

    # Combat Stats (for combat-relevant NPCs)
    is_combatant = Column(Boolean, default=False)
    stats = Column(JSON, nullable=True)  # Full stat block if needed
    cr = Column(Float, nullable=True)  # Challenge Rating

    # Secrets and Knowledge
    secrets = Column(JSON, default=list)  # Things the NPC knows
    quest_hooks = Column(JSON, default=list)  # Quests this NPC can give

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="npcs")


class InventoryItem(Base):
    """Inventory item model for character equipment and possessions."""

    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)

    # Item Info
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    item_type = Column(String(50), nullable=False)  # weapon, armor, potion, etc.
    quantity = Column(Integer, default=1)
    weight = Column(Float, default=0.0)  # In pounds
    value = Column(Integer, default=0)  # In gold pieces

    # Equipment Status
    equipped = Column(Boolean, default=False)
    slot = Column(String(50), nullable=True)  # head, body, hands, etc.

    # Item Properties (JSON for flexibility)
    properties = Column(JSON, default=dict)
    # Examples:
    # Weapon: {"damage": "1d8", "damage_type": "slashing", "critical": "19-20/x2", "range": null}
    # Armor: {"ac_bonus": 5, "max_dex": 3, "armor_check_penalty": -3, "spell_failure": 25}
    # Magic: {"enhancement": 1, "abilities": ["flaming"], "caster_level": 5}

    # Charges (for wands, staves, etc.)
    max_charges = Column(Integer, nullable=True)
    current_charges = Column(Integer, nullable=True)

    # Magic Item Info
    is_magic = Column(Boolean, default=False)
    is_identified = Column(Boolean, default=True)
    aura = Column(String(50), nullable=True)  # Magic aura school

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="inventory")


class Quest(Base):
    """Quest model for tracking adventure objectives."""

    __tablename__ = "quests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)

    # Quest Info
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    quest_giver = Column(String(100), nullable=True)  # NPC who gave the quest
    quest_type = Column(String(50), nullable=True)  # main, side, personal

    # Status
    status = Column(String(20), default="active")  # active, completed, failed, abandoned

    # Objectives
    objectives = Column(JSON, default=list)
    # Example: [{"description": "Find the artifact", "completed": false}, ...]

    # Rewards
    rewards = Column(JSON, default=dict)
    # Example: {"gold": 500, "xp": 1000, "items": ["Sword of Light"]}

    # Progress Notes
    notes = Column(Text, nullable=True)
    clues = Column(JSON, default=list)  # Discovered information

    # Related Elements
    related_npcs = Column(JSON, default=list)  # NPC IDs involved
    related_locations = Column(JSON, default=list)  # Locations involved

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    campaign = relationship("Campaign", back_populates="quests")


class CombatEncounter(Base):
    """Combat encounter model for tracking battles."""

    __tablename__ = "combat_encounters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)

    # Encounter Info
    name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    location = Column(String(100), nullable=True)

    # Participants
    participants = Column(JSON, default=list)
    # Example: [{"name": "Goblin 1", "type": "enemy", "hp": 7, "ac": 15, "initiative": 14}, ...]

    # Initiative Order
    initiative_order = Column(JSON, default=list)  # Ordered list of participant names
    current_turn = Column(Integer, default=0)
    round_number = Column(Integer, default=1)

    # Combat Log
    combat_log = Column(JSON, default=list)  # Array of actions taken

    # Status
    status = Column(String(20), default="active")  # active, victory, defeat, fled
    outcome = Column(Text, nullable=True)

    # Rewards
    xp_awarded = Column(Integer, default=0)
    loot = Column(JSON, default=list)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
