"""FastAPI WebSocket server for AI Dungeon Master."""

import asyncio
import base64
import json
import logging
import random
import string
from collections import deque
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..llm.client import OllamaClient, GenerationConfig
from .speech import transcribe_audio, is_available as speech_available
from .tts import (
    synthesize as tts_synthesize,
    is_available as tts_available,
    list_voices as tts_list_voices,
    split_into_sentences,
    extract_voice_segments,
    strip_voice_tags,
)
from ..game.dice import roll
from ..database.session import init_db, session_scope
from ..database.models import Campaign, Party, Character, InventoryItem, Session as DBSession
from ..characters.races import RACES
from ..characters.classes import CLASSES
from ..characters.creator import SRDData
from ..game.spells import SPELLS

# Initialize SRD data loader
srd_data = SRDData()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Generate session codes
def generate_session_code() -> str:
    """Generate a random 4-letter session code."""
    return ''.join(random.choices(string.ascii_uppercase, k=4))


# Game state
class GameSession:
    """Manages a single game session."""

    def __init__(self, code: str):
        self.code = code
        self.players: dict[str, WebSocket] = {}
        self.dm_socket: Optional[WebSocket] = None
        self.current_location = "The Rusty Dragon Inn"
        self.location_description = "A warm and inviting tavern in Sandpoint."
        self.time_of_day = "evening"
        # Use deque to automatically cap history and prevent memory leak
        self.conversation_history: deque[dict] = deque(maxlen=50)
        self.initiative_order: list[str] = []
        self.current_turn: int = 0
        self.in_combat = False
        self.created_at = datetime.now()
        # Database linkage for save/load
        self.campaign_id: Optional[int] = None
        self.db_session_id: Optional[int] = None

    def to_world_state(self) -> dict:
        """Serialize world state for saving to database."""
        return {
            "location_description": self.location_description,
            "time_of_day": self.time_of_day,
            "in_combat": self.in_combat,
            "initiative_order": self.initiative_order,
            "current_turn": self.current_turn,
        }

    def load_world_state(self, world_state: dict):
        """Restore world state from database."""
        self.location_description = world_state.get("location_description", "")
        self.time_of_day = world_state.get("time_of_day", "day")
        self.in_combat = world_state.get("in_combat", False)
        self.initiative_order = world_state.get("initiative_order", [])
        self.current_turn = world_state.get("current_turn", 0)

    async def broadcast(self, message: dict):
        """Send message to all connected clients, removing dead sockets."""
        dead_players = []
        for player_name, ws in self.players.items():
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"[{self.code}] Failed to send to '{player_name}', removing: {e}")
                dead_players.append(player_name)

        # Remove dead sockets after iteration
        for player_name in dead_players:
            self.players.pop(player_name, None)

        if self.dm_socket:
            try:
                await self.dm_socket.send_json(message)
            except Exception as e:
                logger.warning(f"[{self.code}] Failed to send to DM, removing: {e}")
                self.dm_socket = None

    def is_empty(self) -> bool:
        """Check if session has no players."""
        return len(self.players) == 0 and self.dm_socket is None


class SessionManager:
    """Manages multiple game sessions."""

    def __init__(self):
        self.sessions: dict[str, GameSession] = {}

    def create_session(self) -> GameSession:
        """Create a new session with a unique code."""
        code = generate_session_code()
        while code in self.sessions:
            code = generate_session_code()
        session = GameSession(code)
        self.sessions[code] = session
        logger.info(f"Created session: {code}")
        return session

    def get_session(self, code: str) -> Optional[GameSession]:
        """Get a session by code."""
        return self.sessions.get(code.upper())

    def get_or_create_session(self, code: Optional[str] = None) -> GameSession:
        """Get existing session or create new one."""
        if code:
            session = self.get_session(code)
            if session:
                return session
        return self.create_session()

    def remove_empty_sessions(self):
        """Clean up empty sessions."""
        empty = [code for code, session in self.sessions.items() if session.is_empty()]
        for code in empty:
            del self.sessions[code]
            logger.info(f"Removed empty session: {code}")

    def list_sessions(self) -> list[dict]:
        """List all active sessions."""
        return [
            {
                "code": session.code,
                "players": len(session.players),
                "location": session.current_location,
                "created_at": session.created_at.isoformat(),
            }
            for session in self.sessions.values()
        ]


# Global state
session_manager = SessionManager()
llm_client: Optional[OllamaClient] = None

# Cached LLM availability check (avoid repeated model list calls)
_llm_available_cache: dict = {"available": False, "checked_at": 0.0}
_LLM_CACHE_TTL = 30.0  # seconds


def is_llm_available() -> bool:
    """Check if LLM is available, with caching to reduce latency."""
    import time
    now = time.time()
    if now - _llm_available_cache["checked_at"] < _LLM_CACHE_TTL:
        return _llm_available_cache["available"]

    available = llm_client.is_available() if llm_client else False
    _llm_available_cache["available"] = available
    _llm_available_cache["checked_at"] = now
    return available


async def auto_save_session(game_session: GameSession):
    """Save a single game session to database."""
    if not game_session.campaign_id:
        return  # No campaign linked yet, skip

    try:
        with session_scope() as db:
            campaign = db.query(Campaign).filter_by(id=game_session.campaign_id).first()
            if campaign:
                campaign.current_location = game_session.current_location
                campaign.world_state = game_session.to_world_state()
                logger.debug(f"Auto-saved session {game_session.code}")
    except Exception as e:
        logger.warning(f"Auto-save failed for session {game_session.code}: {e}")


async def auto_save_loop():
    """Background task that auto-saves all active sessions every 5 minutes."""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        for session in list(session_manager.sessions.values()):
            await auto_save_session(session)
        if session_manager.sessions:
            logger.info(f"Auto-saved {len(session_manager.sessions)} active session(s)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    global llm_client

    # Initialize database
    init_db("saves/campaign.db")
    logger.info("Database initialized")

    # Initialize LLM client with faster 3B model
    llm_client = OllamaClient(model="hermes3:3b")
    if llm_client.is_available():
        logger.info("AI connected: hermes3:3b")
    else:
        logger.warning("AI not available - running in offline mode")

    # Start auto-save background task
    auto_save_task = asyncio.create_task(auto_save_loop())
    logger.info("Auto-save enabled (every 5 minutes)")

    yield

    # Cleanup
    auto_save_task.cancel()
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="AI Dungeon Master",
    description="Pathfinder 1e with AI-powered narration",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS for mobile access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
import os
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


# Pydantic models
class PlayerAction(BaseModel):
    action: str
    player_name: str


class DiceRollRequest(BaseModel):
    notation: str
    player_name: str
    reason: Optional[str] = None


class ChatMessage(BaseModel):
    role: str  # "player", "dm", "system"
    content: str
    player_name: Optional[str] = None
    timestamp: str = ""


class CharacterCreate(BaseModel):
    name: str
    race: str
    character_class: str
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10


# System prompt for DM AI
DM_SYSTEM_PROMPT = """You are an expert Dungeon Master running a Pathfinder 1st Edition tabletop RPG game. You speak like a wise, elderly storyteller.

CORE RESPONSIBILITIES:
1. Narrate the story vividly but concisely (2-4 paragraphs max for mobile)
2. Control NPCs and monsters with distinct personalities
3. Remember and reference previous events in the conversation
4. Create dramatic tension and memorable moments
5. Respond to player actions with meaningful consequences

DICE ROLL HANDLING:
- When you need a dice roll, ask: "Roll [type] (DC X)" or "Roll [dice] for damage"
- When a player tells you their roll result, USE THAT NUMBER to determine success/failure
- Example: If you asked for DC 15 and they rolled 18, they SUCCEED
- Example: If you asked for DC 15 and they rolled 12, they FAIL
- Always narrate the outcome based on their actual roll

NPC VOICE TAGS (for text-to-speech):
When an NPC speaks dialogue, prefix their speech with a voice tag to give them a distinct voice:
- [VOICE:elderly_male] for wise old men, wizards, sages
- [VOICE:young_male] for young male adventurers, squires
- [VOICE:gruff] for dwarves, guards, blacksmiths, grizzled warriors
- [VOICE:noble_male] for lords, elf nobles, refined gentlemen
- [VOICE:commoner_male] for farmers, merchants, tavern keepers
- [VOICE:elderly_female] for old witches, wise women, crones
- [VOICE:young_female] for barmaids, princesses, young women
- [VOICE:noble_female] for ladies, elf nobles, queens
- [VOICE:commoner_female] for villagers, female merchants
- [VOICE:mysterious] for hooded strangers, enigmatic figures
- [VOICE:menacing] for villains, bandits, threatening NPCs
- [VOICE:cheerful] for happy, friendly NPCs
- [VOICE:authoritative] for kings, commanders, priests

Example: The old wizard strokes his beard. [VOICE:elderly_male] "Ah, young adventurer, I have waited long for one such as you."

IMPORTANT RULES:
- Use present tense for narration
- Be descriptive but not verbose
- Continue the story naturally from where it left off
- Reference previous events and NPC interactions
- Never restart or forget what happened earlier

The conversation history and current action will be provided."""


@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the main game page."""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(template_path):
        return FileResponse(template_path)
    return HTMLResponse("<h1>AI Dungeon Master</h1><p>Loading...</p>")


@app.get("/api/status")
async def get_status():
    """Get server and AI status."""
    ai_available = is_llm_available()
    total_players = sum(len(s.players) for s in session_manager.sessions.values())
    return {
        "status": "online",
        "ai_available": ai_available,
        "ai_model": "hermes3:3b" if ai_available else None,
        "speech_available": speech_available(),
        "tts_available": tts_available(),
        "active_sessions": len(session_manager.sessions),
        "total_players": total_players,
    }


@app.get("/api/voices")
async def get_voices():
    """Get available TTS voices."""
    return {"voices": tts_list_voices(), "available": tts_available()}


@app.post("/api/sessions")
async def create_session():
    """Create a new game session."""
    session = session_manager.create_session()
    return {
        "code": session.code,
        "location": session.current_location,
    }


@app.get("/api/sessions/{code}")
async def get_session(code: str):
    """Get session info by code."""
    session = session_manager.get_session(code)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "code": session.code,
        "players": list(session.players.keys()),
        "location": session.current_location,
        "in_combat": session.in_combat,
    }


@app.get("/api/sessions")
async def list_sessions():
    """List all active sessions."""
    return {"sessions": session_manager.list_sessions()}


@app.get("/api/saves")
async def list_saves():
    """List all saved games."""
    with session_scope() as db:
        campaigns = db.query(Campaign).order_by(Campaign.updated_at.desc()).all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "location": c.current_location or "Unknown",
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "total_sessions": c.total_sessions,
            }
            for c in campaigns
        ]


@app.post("/api/sessions/{code}/save")
async def save_game(code: str, save_name: str = "Adventure Save"):
    """Save current game session to database."""
    game_session = session_manager.get_session(code)
    if not game_session:
        raise HTTPException(status_code=404, detail="Session not found")

    with session_scope() as db:
        # Create or update Campaign
        if game_session.campaign_id:
            campaign = db.query(Campaign).filter_by(id=game_session.campaign_id).first()
            if not campaign:
                campaign = Campaign(name=save_name)
                db.add(campaign)
                db.flush()
                game_session.campaign_id = campaign.id
        else:
            campaign = Campaign(name=save_name)
            db.add(campaign)
            db.flush()
            game_session.campaign_id = campaign.id

        # Update campaign state
        campaign.current_location = game_session.current_location
        campaign.world_state = game_session.to_world_state()

        # Save conversation log to a new Session record
        session_record = DBSession(
            campaign_id=campaign.id,
            session_number=(campaign.total_sessions or 0) + 1,
            conversation_log=list(game_session.conversation_history),
        )
        db.add(session_record)
        campaign.total_sessions = (campaign.total_sessions or 0) + 1
        game_session.db_session_id = session_record.id

        logger.info(f"Saved game '{save_name}' for session {code}, campaign_id={campaign.id}")

    return {"saved": True, "campaign_id": game_session.campaign_id, "name": save_name}


@app.post("/api/sessions/{code}/load/{campaign_id}")
async def load_game(code: str, campaign_id: int):
    """Load a saved game into current session."""
    game_session = session_manager.get_session(code)
    if not game_session:
        raise HTTPException(status_code=404, detail="Session not found")

    with session_scope() as db:
        campaign = db.query(Campaign).filter_by(id=campaign_id).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Save not found")

        # Restore session state
        game_session.campaign_id = campaign.id
        game_session.current_location = campaign.current_location or "The Rusty Dragon Inn"
        game_session.load_world_state(campaign.world_state or {})

        # Load latest conversation history
        latest_session = (
            db.query(DBSession)
            .filter_by(campaign_id=campaign_id)
            .order_by(DBSession.id.desc())
            .first()
        )
        if latest_session and latest_session.conversation_log:
            game_session.conversation_history.clear()
            for entry in latest_session.conversation_log[-50:]:
                game_session.conversation_history.append(entry)
            game_session.db_session_id = latest_session.id

        logger.info(f"Loaded game '{campaign.name}' into session {code}")

    # Broadcast loaded state to all players
    await game_session.broadcast({
        "type": "game_loaded",
        "name": campaign.name,
        "location": game_session.current_location,
        "description": game_session.location_description,
        "history_count": len(game_session.conversation_history),
    })

    return {
        "loaded": True,
        "name": campaign.name,
        "location": game_session.current_location,
    }


@app.post("/api/transcribe")
async def transcribe_voice(audio: UploadFile = File(...)):
    """Transcribe uploaded audio to text."""
    if not speech_available():
        raise HTTPException(
            status_code=503,
            detail="Speech-to-text not available. Install faster-whisper."
        )

    # Read audio data
    audio_data = await audio.read()
    if len(audio_data) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Get format from filename or content type
    format = "webm"
    if audio.filename:
        ext = audio.filename.rsplit(".", 1)[-1].lower()
        if ext in ("webm", "wav", "mp3", "ogg", "m4a"):
            format = ext

    # Transcribe
    text = await transcribe_audio(audio_data, format)

    if text is None:
        raise HTTPException(status_code=500, detail="Transcription failed")

    return {"text": text, "format": format}


@app.get("/api/races")
async def get_races():
    """Get all available races."""
    races = []
    for name, race in RACES.items():
        races.append({
            "name": race.name,
            "size": race.size,
            "speed": race.speed,
            "ability_modifiers": race.ability_modifiers,
            "description": race.description,
        })
    return {"races": races}


@app.get("/api/classes")
async def get_classes():
    """Get all available classes."""
    classes = []
    for name, cls in CLASSES.items():
        classes.append({
            "name": cls.name,
            "hit_die": cls.hit_die,
            "description": cls.description,
            "is_spellcaster": cls.is_spellcaster(),
        })
    return {"classes": classes}


@app.get("/api/characters")
async def get_characters():
    """Get all saved characters."""
    try:
        with session_scope() as session:
            characters = session.query(Character).all()
            return {
                "characters": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "race": c.race,
                        "character_class": c.character_class,
                        "level": c.level,
                        "current_hp": c.current_hp,
                        "max_hp": c.max_hp,
                    }
                    for c in characters
                ]
            }
    except Exception as e:
        logger.error(f"Error fetching characters: {e}")
        return {"characters": []}


@app.get("/api/characters/{character_id}")
async def get_character(character_id: int):
    """Get a single character's full details."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")
        return {
            "id": char.id,
            "name": char.name,
            "race": char.race,
            "character_class": char.character_class,
            "level": char.level,
            "current_hp": char.current_hp,
            "max_hp": char.max_hp,
            "strength": char.strength,
            "dexterity": char.dexterity,
            "constitution": char.constitution,
            "intelligence": char.intelligence,
            "wisdom": char.wisdom,
            "charisma": char.charisma,
            "base_attack_bonus": char.base_attack_bonus,
            "armor_class": char.armor_class,
            "experience": char.experience,
            "fortitude_base": char.fortitude_base,
            "reflex_base": char.reflex_base,
            "will_base": char.will_base,
        }


@app.post("/api/characters")
async def create_character(char: CharacterCreate):
    """Create a new character."""
    # Validate race and class
    if char.race not in RACES:
        raise HTTPException(status_code=400, detail=f"Invalid race: {char.race}")
    if char.character_class not in CLASSES:
        raise HTTPException(status_code=400, detail=f"Invalid class: {char.character_class}")

    race = RACES[char.race]
    cls = CLASSES[char.character_class]

    # Apply racial ability modifiers
    str_mod = race.ability_modifiers.get("strength", 0)
    dex_mod = race.ability_modifiers.get("dexterity", 0)
    con_mod = race.ability_modifiers.get("constitution", 0)
    int_mod = race.ability_modifiers.get("intelligence", 0)
    wis_mod = race.ability_modifiers.get("wisdom", 0)
    cha_mod = race.ability_modifiers.get("charisma", 0)

    final_str = char.strength + str_mod
    final_dex = char.dexterity + dex_mod
    final_con = char.constitution + con_mod
    final_int = char.intelligence + int_mod
    final_wis = char.wisdom + wis_mod
    final_cha = char.charisma + cha_mod

    # Calculate derived stats
    con_bonus = (final_con - 10) // 2
    max_hp = cls.hit_die + con_bonus
    ac = 10 + ((final_dex - 10) // 2)

    try:
        with session_scope() as session:
            # Get starting equipment for this class
            starting = STARTING_EQUIPMENT.get(char.character_class, {"gold": 100, "items": []})

            new_char = Character(
                name=char.name,
                race=char.race,
                character_class=char.character_class,
                level=1,
                strength=final_str,
                dexterity=final_dex,
                constitution=final_con,
                intelligence=final_int,
                wisdom=final_wis,
                charisma=final_cha,
                max_hp=max_hp,
                current_hp=max_hp,
                armor_class=ac,
                gold=starting["gold"],  # Starting gold
            )
            session.add(new_char)
            session.flush()

            # Add starting equipment
            for item_data in starting["items"]:
                # Determine item type from slot or name
                item_type = "gear"
                name_lower = item_data["name"].lower()
                if item_data.get("slot") == "main_hand" or any(w in name_lower for w in ["sword", "axe", "mace", "bow", "dagger", "staff", "scimitar", "rapier", "sling"]):
                    item_type = "weapon"
                elif item_data.get("slot") == "body" or any(a in name_lower for a in ["armor", "mail", "shirt"]):
                    item_type = "armor"
                elif "shield" in name_lower:
                    item_type = "shield"
                elif "potion" in name_lower:
                    item_type = "potion"
                elif "arrow" in name_lower or "bolt" in name_lower or "bullet" in name_lower:
                    item_type = "ammunition"
                elif "tool" in name_lower or "kit" in name_lower:
                    item_type = "tool"

                item = InventoryItem(
                    character_id=new_char.id,
                    name=item_data["name"],
                    item_type=item_type,
                    quantity=item_data.get("quantity", 1),
                    weight=item_data.get("weight", 0),
                    value=item_data.get("value", 0),
                    equipped=item_data.get("equipped", False),
                    slot=item_data.get("slot", ""),
                )
                session.add(item)

            # Recalculate AC based on equipped armor
            armor_bonus = 0
            shield_bonus = 0
            for item_data in starting["items"]:
                if item_data.get("equipped"):
                    if item_data.get("slot") == "body":
                        # Armor - estimate AC bonus from value
                        if "Chain" in item_data["name"]:
                            armor_bonus = 4
                        elif "Scale" in item_data["name"]:
                            armor_bonus = 5
                        elif "Leather" in item_data["name"]:
                            armor_bonus = 2
                        elif "Hide" in item_data["name"]:
                            armor_bonus = 4
                    elif item_data.get("slot") == "off_hand" and "Shield" in item_data["name"]:
                        shield_bonus = 2

            # Update AC: 10 + Dex + Armor + Shield
            dex_bonus = (final_dex - 10) // 2
            new_char.armor_class = 10 + dex_bonus + armor_bonus + shield_bonus

            # Add starting spells for caster classes
            starting_spells = STARTING_SPELLS.get(char.character_class)
            if starting_spells:
                new_char.spellcaster = True
                new_char.caster_level = starting_spells["caster_level"]
                new_char.spell_slots = starting_spells["spell_slots"]
                new_char.spells_known = starting_spells["spells_known"]

            return {
                "id": new_char.id,
                "name": new_char.name,
                "race": new_char.race,
                "character_class": new_char.character_class,
                "level": new_char.level,
                "max_hp": new_char.max_hp,
                "ac": new_char.armor_class,
                "gold": new_char.gold,
                "spellcaster": new_char.spellcaster if starting_spells else False,
            }
    except Exception as e:
        logger.error(f"Error creating character: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/characters/{character_id}")
async def delete_character(character_id: int):
    """Delete a character."""
    try:
        with session_scope() as session:
            char = session.query(Character).filter_by(id=character_id).first()
            if not char:
                raise HTTPException(status_code=404, detail="Character not found")
            session.delete(char)
            return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting character: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== INVENTORY ENDPOINTS =====

@app.get("/api/characters/{character_id}/inventory")
async def get_character_inventory(character_id: int):
    """Get character's inventory items."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        items = session.query(InventoryItem).filter_by(character_id=character_id).all()

        # Calculate total weight
        total_weight = sum(item.weight * item.quantity for item in items)

        # Calculate carrying capacity based on Strength
        str_score = char.strength or 10
        # Light load: Str * 3.33, Medium: Str * 6.66, Heavy: Str * 10
        capacity = str_score * 10  # Heavy load max

        return {
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "description": item.description,
                    "item_type": item.item_type,
                    "quantity": item.quantity,
                    "weight": item.weight,
                    "value": item.value,
                    "equipped": item.equipped,
                    "slot": item.slot,
                    "properties": item.properties,
                }
                for item in items
            ],
            "total_weight": total_weight,
            "capacity": capacity,
        }


class ItemCreate(BaseModel):
    name: str
    description: str = ""
    item_type: str = "gear"
    quantity: int = 1
    weight: float = 0.0
    value: float = 0.0
    equipped: bool = False
    slot: str = ""
    properties: dict = Field(default_factory=dict)


@app.post("/api/characters/{character_id}/inventory")
async def add_inventory_item(character_id: int, item: ItemCreate):
    """Add item to character's inventory."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        new_item = InventoryItem(
            character_id=character_id,
            name=item.name,
            description=item.description,
            item_type=item.item_type,
            quantity=item.quantity,
            weight=item.weight,
            value=item.value,
            equipped=item.equipped,
            slot=item.slot,
            properties=item.properties,
        )
        session.add(new_item)
        session.flush()
        return {"id": new_item.id, "name": new_item.name}


@app.put("/api/characters/{character_id}/inventory/{item_id}")
async def update_inventory_item(character_id: int, item_id: int, updates: dict):
    """Update an inventory item (equip, quantity, etc.)."""
    with session_scope() as session:
        item = session.query(InventoryItem).filter_by(
            id=item_id, character_id=character_id
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)

        return {"updated": True}


@app.delete("/api/characters/{character_id}/inventory/{item_id}")
async def delete_inventory_item(character_id: int, item_id: int):
    """Remove item from inventory."""
    with session_scope() as session:
        item = session.query(InventoryItem).filter_by(
            id=item_id, character_id=character_id
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        session.delete(item)
        return {"deleted": True}


# ===== CURRENCY ENDPOINTS =====

@app.get("/api/characters/{character_id}/currency")
async def get_character_currency(character_id: int):
    """Get character's currency."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        return {
            "platinum": char.platinum or 0,
            "gold": char.gold or 0,
            "silver": char.silver or 0,
            "copper": char.copper or 0,
            "total_gold": (char.platinum or 0) * 10 + (char.gold or 0) +
                         (char.silver or 0) / 10 + (char.copper or 0) / 100,
        }


class CurrencyUpdate(BaseModel):
    platinum: int = 0
    gold: int = 0
    silver: int = 0
    copper: int = 0
    operation: str = "set"  # "set", "add", or "subtract"


@app.put("/api/characters/{character_id}/currency")
async def update_character_currency(character_id: int, update: CurrencyUpdate):
    """Update character's currency."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        if update.operation == "set":
            char.platinum = update.platinum
            char.gold = update.gold
            char.silver = update.silver
            char.copper = update.copper
        elif update.operation == "add":
            char.platinum = (char.platinum or 0) + update.platinum
            char.gold = (char.gold or 0) + update.gold
            char.silver = (char.silver or 0) + update.silver
            char.copper = (char.copper or 0) + update.copper
        elif update.operation == "subtract":
            char.platinum = max(0, (char.platinum or 0) - update.platinum)
            char.gold = max(0, (char.gold or 0) - update.gold)
            char.silver = max(0, (char.silver or 0) - update.silver)
            char.copper = max(0, (char.copper or 0) - update.copper)

        return {
            "platinum": char.platinum,
            "gold": char.gold,
            "silver": char.silver,
            "copper": char.copper,
        }


# ===== SPELLS ENDPOINTS =====

@app.get("/api/characters/{character_id}/spells")
async def get_character_spells(character_id: int):
    """Get character's known spells and spell slots."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        return {
            "spells_known": char.spells_known or [],
            "spell_slots": char.spell_slots or {},
            "caster_level": char.caster_level or 0,
            "spellcaster": char.spellcaster or False,
        }


class SpellCast(BaseModel):
    spell_name: str
    spell_level: int


@app.post("/api/characters/{character_id}/spells/cast")
async def cast_spell(character_id: int, cast: SpellCast):
    """Use a spell slot when casting a spell."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        slots = char.spell_slots or {}
        level_key = str(cast.spell_level)

        if level_key not in slots:
            raise HTTPException(status_code=400, detail="No slots at this level")

        slot_info = slots[level_key]
        used = slot_info.get("used", 0)
        max_slots = slot_info.get("max", 0)

        if used >= max_slots:
            raise HTTPException(status_code=400, detail="No spell slots remaining")

        slots[level_key]["used"] = used + 1
        char.spell_slots = slots

        return {
            "cast": cast.spell_name,
            "level": cast.spell_level,
            "slots_remaining": max_slots - used - 1,
        }


@app.post("/api/characters/{character_id}/spells/rest")
async def long_rest(character_id: int):
    """Reset spell slots after a long rest."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        slots = char.spell_slots or {}
        for level in slots:
            slots[level]["used"] = 0
        char.spell_slots = slots

        # Also heal to max HP
        char.current_hp = char.max_hp

        return {"rested": True, "hp": char.current_hp, "spell_slots": slots}


class SpellLearn(BaseModel):
    spell_name: str


@app.post("/api/characters/{character_id}/spells/learn")
async def learn_spell(character_id: int, learn: SpellLearn):
    """Add a spell to character's known spells with class validation."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        # Validate spell exists
        spell_key = learn.spell_name.lower()
        if spell_key not in SPELLS:
            raise HTTPException(status_code=400, detail=f"Unknown spell: {learn.spell_name}")

        spell = SPELLS[spell_key]
        class_lower = char.character_class.lower()

        # Validate class can cast this spell
        if class_lower not in spell.level:
            raise HTTPException(
                status_code=400,
                detail=f"{char.character_class}s cannot learn {spell.name}"
            )

        # Validate character level allows this spell level
        spell_level = spell.level[class_lower]
        spell_slots = char.spell_slots or {}
        max_spell_level = max((int(k) for k in spell_slots.keys()), default=-1)

        if spell_level > max_spell_level and spell_level > 0:
            raise HTTPException(
                status_code=400,
                detail=f"You cannot learn level {spell_level} spells yet"
            )

        known = char.spells_known or []
        if spell_key not in known:
            known.append(spell_key)
            char.spells_known = known

        return {"spells_known": known}


# ===== SPELL & ITEM LISTS =====

@app.get("/api/spells")
async def get_spell_list(character_class: str = None, max_level: int = 9):
    """Get available spells, optionally filtered by class."""
    result = []
    for name, spell in SPELLS.items():
        # Filter by class if specified
        if character_class:
            class_lower = character_class.lower()
            if class_lower not in spell.level:
                continue
            spell_level = spell.level[class_lower]
        else:
            spell_level = min(spell.level.values()) if spell.level else 0

        if spell_level > max_level:
            continue

        result.append({
            "name": name,
            "level": spell_level,
            "school": spell.school.value if hasattr(spell.school, 'value') else str(spell.school),
            "description": spell.description,
            "casting_time": spell.casting_time,
            "range": spell.range.value if hasattr(spell.range, 'value') else str(spell.range),
            "duration": spell.duration.value if hasattr(spell.duration, 'value') else str(spell.duration),
        })

    return {"spells": sorted(result, key=lambda x: (x["level"], x["name"]))}


# Common items for the item picker
COMMON_ITEMS = [
    {"name": "Longsword", "type": "weapon", "weight": 4.0, "value": 15.0, "properties": {"damage": "1d8", "damage_type": "slashing"}},
    {"name": "Shortsword", "type": "weapon", "weight": 2.0, "value": 10.0, "properties": {"damage": "1d6", "damage_type": "piercing"}},
    {"name": "Dagger", "type": "weapon", "weight": 1.0, "value": 2.0, "properties": {"damage": "1d4", "damage_type": "piercing"}},
    {"name": "Longbow", "type": "weapon", "weight": 3.0, "value": 75.0, "properties": {"damage": "1d8", "damage_type": "piercing", "range": 100}},
    {"name": "Crossbow, Light", "type": "weapon", "weight": 4.0, "value": 35.0, "properties": {"damage": "1d8", "damage_type": "piercing"}},
    {"name": "Chain Shirt", "type": "armor", "weight": 25.0, "value": 100.0, "properties": {"ac_bonus": 4, "max_dex": 4}},
    {"name": "Leather Armor", "type": "armor", "weight": 15.0, "value": 10.0, "properties": {"ac_bonus": 2, "max_dex": 6}},
    {"name": "Scale Mail", "type": "armor", "weight": 30.0, "value": 50.0, "properties": {"ac_bonus": 5, "max_dex": 3}},
    {"name": "Shield, Heavy Steel", "type": "shield", "weight": 15.0, "value": 20.0, "properties": {"ac_bonus": 2}},
    {"name": "Potion of Healing", "type": "potion", "weight": 0.1, "value": 50.0, "properties": {"heal_dice": "1d8+1"}},
    {"name": "Potion of Greater Healing", "type": "potion", "weight": 0.1, "value": 150.0, "properties": {"heal_dice": "2d8+2"}},
    {"name": "Rope, Hemp (50 ft)", "type": "gear", "weight": 10.0, "value": 1.0},
    {"name": "Torch", "type": "gear", "weight": 1.0, "value": 0.01},
    {"name": "Rations (1 day)", "type": "gear", "weight": 1.0, "value": 0.5},
    {"name": "Backpack", "type": "gear", "weight": 2.0, "value": 2.0},
    {"name": "Bedroll", "type": "gear", "weight": 5.0, "value": 0.1},
    {"name": "Waterskin", "type": "gear", "weight": 4.0, "value": 1.0},
    {"name": "Thieves' Tools", "type": "tool", "weight": 1.0, "value": 30.0},
    {"name": "Healer's Kit", "type": "tool", "weight": 1.0, "value": 50.0},
    {"name": "Arrows (20)", "type": "ammunition", "weight": 3.0, "value": 1.0},
    {"name": "Bolts (20)", "type": "ammunition", "weight": 2.0, "value": 1.0},
]

# Starting equipment and gold by class (Pathfinder 1e)
STARTING_EQUIPMENT = {
    "Fighter": {
        "gold": 175,
        "items": [
            {"name": "Longsword", "weight": 4.0, "value": 15, "slot": "main_hand", "equipped": True},
            {"name": "Chain Shirt", "weight": 25.0, "value": 100, "slot": "body", "equipped": True},
            {"name": "Heavy Steel Shield", "weight": 15.0, "value": 20, "slot": "off_hand", "equipped": True},
            {"name": "Backpack", "weight": 2.0, "value": 2},
            {"name": "Bedroll", "weight": 5.0, "value": 0.1},
            {"name": "Rations", "weight": 5.0, "value": 2.5, "quantity": 5},
            {"name": "Waterskin", "weight": 4.0, "value": 1},
        ]
    },
    "Rogue": {
        "gold": 140,
        "items": [
            {"name": "Shortsword", "weight": 2.0, "value": 10, "slot": "main_hand", "equipped": True},
            {"name": "Dagger", "weight": 1.0, "value": 2, "quantity": 2},
            {"name": "Leather Armor", "weight": 15.0, "value": 10, "slot": "body", "equipped": True},
            {"name": "Thieves' Tools", "weight": 1.0, "value": 30},
            {"name": "Backpack", "weight": 2.0, "value": 2},
            {"name": "Rope, Hemp (50 ft)", "weight": 10.0, "value": 1},
            {"name": "Torch", "weight": 1.0, "value": 0.01, "quantity": 3},
        ]
    },
    "Wizard": {
        "gold": 70,
        "items": [
            {"name": "Quarterstaff", "weight": 4.0, "value": 0, "slot": "main_hand", "equipped": True},
            {"name": "Dagger", "weight": 1.0, "value": 2},
            {"name": "Spellbook", "weight": 3.0, "value": 15},
            {"name": "Spell Component Pouch", "weight": 2.0, "value": 5},
            {"name": "Backpack", "weight": 2.0, "value": 2},
            {"name": "Ink and Quill", "weight": 0.1, "value": 8},
            {"name": "Rations", "weight": 5.0, "value": 2.5, "quantity": 5},
        ]
    },
    "Cleric": {
        "gold": 140,
        "items": [
            {"name": "Heavy Mace", "weight": 8.0, "value": 12, "slot": "main_hand", "equipped": True},
            {"name": "Scale Mail", "weight": 30.0, "value": 50, "slot": "body", "equipped": True},
            {"name": "Heavy Steel Shield", "weight": 15.0, "value": 20, "slot": "off_hand", "equipped": True},
            {"name": "Holy Symbol, Silver", "weight": 1.0, "value": 25},
            {"name": "Backpack", "weight": 2.0, "value": 2},
            {"name": "Healer's Kit", "weight": 1.0, "value": 50},
        ]
    },
    "Barbarian": {
        "gold": 105,
        "items": [
            {"name": "Greataxe", "weight": 12.0, "value": 20, "slot": "main_hand", "equipped": True},
            {"name": "Hide Armor", "weight": 25.0, "value": 15, "slot": "body", "equipped": True},
            {"name": "Javelin", "weight": 2.0, "value": 1, "quantity": 4},
            {"name": "Backpack", "weight": 2.0, "value": 2},
            {"name": "Bedroll", "weight": 5.0, "value": 0.1},
            {"name": "Rations", "weight": 5.0, "value": 2.5, "quantity": 5},
        ]
    },
    "Bard": {
        "gold": 140,
        "items": [
            {"name": "Rapier", "weight": 2.0, "value": 20, "slot": "main_hand", "equipped": True},
            {"name": "Leather Armor", "weight": 15.0, "value": 10, "slot": "body", "equipped": True},
            {"name": "Shortbow", "weight": 2.0, "value": 30},
            {"name": "Arrows", "weight": 3.0, "value": 1, "quantity": 20},
            {"name": "Musical Instrument (Lute)", "weight": 3.0, "value": 5},
            {"name": "Backpack", "weight": 2.0, "value": 2},
        ]
    },
    "Paladin": {
        "gold": 175,
        "items": [
            {"name": "Longsword", "weight": 4.0, "value": 15, "slot": "main_hand", "equipped": True},
            {"name": "Scale Mail", "weight": 30.0, "value": 50, "slot": "body", "equipped": True},
            {"name": "Heavy Steel Shield", "weight": 15.0, "value": 20, "slot": "off_hand", "equipped": True},
            {"name": "Holy Symbol, Silver", "weight": 1.0, "value": 25},
            {"name": "Backpack", "weight": 2.0, "value": 2},
            {"name": "Waterskin", "weight": 4.0, "value": 1},
        ]
    },
    "Ranger": {
        "gold": 175,
        "items": [
            {"name": "Longbow", "weight": 3.0, "value": 75, "slot": "main_hand", "equipped": True},
            {"name": "Arrows", "weight": 6.0, "value": 2, "quantity": 40},
            {"name": "Shortsword", "weight": 2.0, "value": 10},
            {"name": "Leather Armor", "weight": 15.0, "value": 10, "slot": "body", "equipped": True},
            {"name": "Backpack", "weight": 2.0, "value": 2},
            {"name": "Bedroll", "weight": 5.0, "value": 0.1},
        ]
    },
    "Sorcerer": {
        "gold": 70,
        "items": [
            {"name": "Quarterstaff", "weight": 4.0, "value": 0, "slot": "main_hand", "equipped": True},
            {"name": "Dagger", "weight": 1.0, "value": 2, "quantity": 2},
            {"name": "Backpack", "weight": 2.0, "value": 2},
            {"name": "Rations", "weight": 5.0, "value": 2.5, "quantity": 5},
            {"name": "Waterskin", "weight": 4.0, "value": 1},
        ]
    },
    "Monk": {
        "gold": 35,
        "items": [
            {"name": "Quarterstaff", "weight": 4.0, "value": 0, "slot": "main_hand", "equipped": True},
            {"name": "Sling", "weight": 0.0, "value": 0},
            {"name": "Sling Bullets", "weight": 5.0, "value": 0.1, "quantity": 10},
            {"name": "Backpack", "weight": 2.0, "value": 2},
            {"name": "Rope, Hemp (50 ft)", "weight": 10.0, "value": 1},
            {"name": "Rations", "weight": 5.0, "value": 2.5, "quantity": 5},
        ]
    },
    "Druid": {
        "gold": 70,
        "items": [
            {"name": "Scimitar", "weight": 4.0, "value": 15, "slot": "main_hand", "equipped": True},
            {"name": "Leather Armor", "weight": 15.0, "value": 10, "slot": "body", "equipped": True},
            {"name": "Heavy Wooden Shield", "weight": 10.0, "value": 7, "slot": "off_hand", "equipped": True},
            {"name": "Holly and Mistletoe", "weight": 0.0, "value": 0},
            {"name": "Backpack", "weight": 2.0, "value": 2},
            {"name": "Rations", "weight": 5.0, "value": 2.5, "quantity": 5},
        ]
    },
}

# Starting spells and spell slots by class (Pathfinder 1e level 1)
# Spell slots format: {"level": {"total": X, "used": 0}}
STARTING_SPELLS = {
    "Wizard": {
        "caster_level": 1,
        "spell_slots": {
            "0": {"total": 3, "used": 0},  # Cantrips (at will, but track 3 prepared)
            "1": {"total": 2, "used": 0},  # 1 base + 1 for Int 12+
        },
        "spells_known": [
            # Cantrips - all available to wizards
            "detect magic", "light", "ray of frost", "mage hand", "acid splash",
            # 1st level - starting spellbook spells
            "magic missile", "mage armor", "shield", "sleep", "burning hands",
        ],
    },
    "Sorcerer": {
        "caster_level": 1,
        "spell_slots": {
            "0": {"total": 99, "used": 0},  # Cantrips unlimited
            "1": {"total": 3, "used": 0},
        },
        "spells_known": [
            # 4 cantrips known
            "detect magic", "light", "ray of frost", "acid splash",
            # 2 1st-level spells known
            "magic missile", "burning hands",
        ],
    },
    "Cleric": {
        "caster_level": 1,
        "spell_slots": {
            "0": {"total": 3, "used": 0},
            "1": {"total": 2, "used": 0},  # 1 base + 1 domain
        },
        "spells_known": [
            # Clerics prepare from full list, but give some starting ones
            "detect magic", "light", "guidance", "stabilize",
            "cure light wounds", "bless",
        ],
    },
    "Druid": {
        "caster_level": 1,
        "spell_slots": {
            "0": {"total": 3, "used": 0},
            "1": {"total": 2, "used": 0},
        },
        "spells_known": [
            # Druids prepare from full list
            "detect magic", "light", "guidance", "stabilize",
            "cure light wounds",
        ],
    },
    "Bard": {
        "caster_level": 1,
        "spell_slots": {
            "0": {"total": 99, "used": 0},  # Cantrips unlimited
            "1": {"total": 1, "used": 0},
        },
        "spells_known": [
            # 4 cantrips known
            "detect magic", "light", "mage hand", "ghost sound",
            # 2 1st-level spells known
            "cure light wounds", "sleep",
        ],
    },
    # Paladin and Ranger don't cast at level 1
    "Paladin": None,
    "Ranger": None,
    # Non-casters
    "Fighter": None,
    "Rogue": None,
    "Barbarian": None,
    "Monk": None,
}


@app.get("/api/items")
async def get_item_list(item_type: str = None):
    """Get common items for the item picker."""
    items = COMMON_ITEMS
    if item_type:
        items = [i for i in items if i["type"] == item_type]
    return {"items": items}


# ===== SRD DATA ENDPOINTS =====

@app.get("/api/equipment")
async def get_equipment(category: str = None, search: str = None):
    """
    Get equipment from SRD data.

    Args:
        category: Filter by category (weapons, armor, adventuring_gear, potions)
        search: Search term to filter by name
    """
    equipment = srd_data.get_equipment()
    result = []

    # Flatten equipment into list
    for cat_name, cat_data in equipment.items():
        if category and cat_name != category:
            continue

        if isinstance(cat_data, dict):
            # Nested categories (weapons, armor)
            for subcat_name, items in cat_data.items():
                if isinstance(items, list):
                    for item in items:
                        item_copy = dict(item)
                        item_copy["category"] = cat_name
                        item_copy["subcategory"] = subcat_name
                        result.append(item_copy)
        elif isinstance(cat_data, list):
            # Flat category (adventuring_gear, potions)
            for item in cat_data:
                item_copy = dict(item)
                item_copy["category"] = cat_name
                result.append(item_copy)

    # Apply search filter
    if search:
        search_lower = search.lower()
        result = [i for i in result if search_lower in i.get("name", "").lower()]

    return {"equipment": result, "total": len(result)}


@app.get("/api/equipment/weapons")
async def get_weapons(weapon_type: str = None, search: str = None):
    """Get weapons from SRD data."""
    equipment = srd_data.get_equipment()
    weapons = equipment.get("weapons", {})
    result = []

    for subcat, items in weapons.items():
        if weapon_type and subcat != weapon_type:
            continue
        for item in items:
            item_copy = dict(item)
            item_copy["weapon_category"] = subcat
            if search and search.lower() not in item.get("name", "").lower():
                continue
            result.append(item_copy)

    return {"weapons": result, "total": len(result)}


@app.get("/api/equipment/armor")
async def get_armor(armor_type: str = None, search: str = None):
    """Get armor from SRD data."""
    equipment = srd_data.get_equipment()
    armor = equipment.get("armor", {})
    result = []

    for subcat, items in armor.items():
        if armor_type and subcat != armor_type:
            continue
        for item in items:
            item_copy = dict(item)
            item_copy["armor_category"] = subcat
            if search and search.lower() not in item.get("name", "").lower():
                continue
            result.append(item_copy)

    return {"armor": result, "total": len(result)}


@app.get("/api/equipment/gear")
async def get_adventuring_gear(search: str = None):
    """Get adventuring gear from SRD data."""
    equipment = srd_data.get_equipment()
    gear = equipment.get("adventuring_gear", [])

    if search:
        search_lower = search.lower()
        gear = [i for i in gear if search_lower in i.get("name", "").lower()]

    return {"gear": gear, "total": len(gear)}


@app.get("/api/magic-items")
async def get_magic_items(item_type: str = None, max_price: int = None, search: str = None):
    """
    Get magic items from SRD data.

    Args:
        item_type: Filter by type (wondrous, potions, weapons, rings, armor, rods)
        max_price: Maximum price in GP
        search: Search term to filter by name
    """
    data = srd_data.get_magic_items()
    items = data.get("items", [])

    result = []
    for item in items:
        # Filter by type
        if item_type and item.get("type") != item_type:
            continue

        # Filter by price
        if max_price:
            price_str = item.get("price", "0")
            try:
                # Parse price like "36,000 gp" or "500"
                price_num = int("".join(c for c in str(price_str).split()[0] if c.isdigit()))
                if price_num > max_price:
                    continue
            except (ValueError, IndexError):
                pass

        # Filter by search
        if search and search.lower() not in item.get("name", "").lower():
            continue

        result.append(item)

    return {"items": result, "total": len(result)}


@app.get("/api/feats")
async def get_feats(search: str = None, has_prerequisites: bool = None):
    """
    Get feats from SRD data.

    Args:
        search: Search term to filter by name or benefit
        has_prerequisites: If True, only feats with prerequisites; if False, only feats without
    """
    data = srd_data.get_feats()
    feats = data.get("feats", [])

    result = []
    for feat in feats:
        # Filter by prerequisites
        if has_prerequisites is not None:
            prereq = feat.get("prerequisites", "").strip()
            if has_prerequisites and not prereq:
                continue
            if not has_prerequisites and prereq:
                continue

        # Filter by search
        if search:
            search_lower = search.lower()
            name_match = search_lower in feat.get("name", "").lower()
            benefit_match = search_lower in feat.get("benefit", "").lower()
            if not (name_match or benefit_match):
                continue

        result.append(feat)

    return {"feats": result, "total": len(result)}


@app.get("/api/treasure/tables")
async def get_treasure_tables():
    """Get treasure generation tables."""
    return srd_data.get_treasure_tables()


@app.post("/api/treasure/generate")
async def generate_treasure(cr: float = 1, treasure_type: str = "standard", count: int = 1):
    """
    Generate random treasure based on CR.

    Args:
        cr: Challenge Rating (0.125 to 20)
        treasure_type: Type of treasure (none, incidental, standard, double, triple, npc_gear)
        count: Number of treasure hoards to generate
    """
    tables = srd_data.get_treasure_tables()

    if not tables:
        raise HTTPException(status_code=500, detail="Treasure tables not loaded")

    treasure_by_cr = tables.get("treasure_by_cr", {})
    treasure_types = tables.get("treasure_types", {})
    gems = tables.get("gems", [])
    art_objects = tables.get("art_objects", [])
    mundane_items = tables.get("mundane_items", [])

    # Find appropriate CR tier
    cr_str = str(cr)
    if cr_str not in treasure_by_cr:
        # Find nearest CR
        cr_keys = sorted([float(k) for k in treasure_by_cr.keys()])
        nearest = min(cr_keys, key=lambda x: abs(x - cr))
        cr_str = str(nearest) if nearest != int(nearest) else str(int(nearest))

    base = treasure_by_cr.get(cr_str, {"coins": {"min": 0, "max": 100}, "gems": 0, "items": 0})
    type_mods = treasure_types.get(treasure_type, {"coins_multiplier": 1, "gems_multiplier": 1, "items_multiplier": 1})

    results = []
    for _ in range(count):
        hoard = {"coins": 0, "gems": [], "art": [], "items": [], "total_value": 0}

        # Generate coins
        coin_range = base.get("coins", {"min": 0, "max": 100})
        base_coins = random.randint(coin_range["min"], coin_range["max"])
        hoard["coins"] = int(base_coins * type_mods.get("coins_multiplier", 1))
        hoard["total_value"] = hoard["coins"]

        # Generate gems
        gem_chance = base.get("gems", 0) * type_mods.get("gems_multiplier", 1)
        if random.random() < gem_chance and gems:
            # Select gem tier based on CR
            max_tier = min(6, max(1, int(cr / 3) + 1))
            eligible_gems = [g for g in gems if g.get("tier", 1) <= max_tier]
            if eligible_gems:
                num_gems = random.randint(1, max(1, int(cr / 2)))
                for _ in range(num_gems):
                    gem = random.choice(eligible_gems)
                    hoard["gems"].append(gem["name"])
                    hoard["total_value"] += gem["value"]

        # Generate art objects
        if random.random() < gem_chance * 0.5 and art_objects:
            max_tier = min(8, max(1, int(cr / 2) + 1))
            eligible_art = [a for a in art_objects if a.get("tier", 1) <= max_tier]
            if eligible_art:
                art = random.choice(eligible_art)
                hoard["art"].append(art["name"])
                hoard["total_value"] += art["value"]

        # Generate mundane items
        item_chance = base.get("items", 0) * type_mods.get("items_multiplier", 1)
        if random.random() < item_chance and mundane_items:
            num_items = random.randint(1, max(1, int(cr / 3)))
            for _ in range(num_items):
                item = random.choice(mundane_items)
                hoard["items"].append(item["name"])
                hoard["total_value"] += item["value"]

        results.append(hoard)

    return {"treasure": results if count > 1 else results[0], "cr": cr, "type": treasure_type}


# ===== PARTY ENDPOINTS =====

@app.get("/api/party/treasury")
async def get_party_treasury(session_code: str):
    """Get shared party gold."""
    game_session = session_manager.get_session(session_code)
    if not game_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # For now, use in-memory party treasury
    if not hasattr(game_session, 'party_treasury'):
        game_session.party_treasury = {"platinum": 0, "gold": 0, "silver": 0, "copper": 0}

    return game_session.party_treasury


@app.put("/api/party/treasury")
async def update_party_treasury(session_code: str, update: CurrencyUpdate):
    """Update shared party gold."""
    game_session = session_manager.get_session(session_code)
    if not game_session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not hasattr(game_session, 'party_treasury'):
        game_session.party_treasury = {"platinum": 0, "gold": 0, "silver": 0, "copper": 0}

    treasury = game_session.party_treasury
    if update.operation == "add":
        treasury["platinum"] += update.platinum
        treasury["gold"] += update.gold
        treasury["silver"] += update.silver
        treasury["copper"] += update.copper
    elif update.operation == "subtract":
        treasury["platinum"] = max(0, treasury["platinum"] - update.platinum)
        treasury["gold"] = max(0, treasury["gold"] - update.gold)
        treasury["silver"] = max(0, treasury["silver"] - update.silver)
        treasury["copper"] = max(0, treasury["copper"] - update.copper)
    else:  # set
        treasury["platinum"] = update.platinum
        treasury["gold"] = update.gold
        treasury["silver"] = update.silver
        treasury["copper"] = update.copper

    return treasury


@app.get("/api/party/loot")
async def get_party_loot(session_code: str):
    """Get shared party loot bag."""
    game_session = session_manager.get_session(session_code)
    if not game_session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not hasattr(game_session, 'party_loot'):
        game_session.party_loot = []

    return {"items": game_session.party_loot}


@app.post("/api/party/loot")
async def add_party_loot(session_code: str, item: ItemCreate):
    """Add item to party loot bag."""
    game_session = session_manager.get_session(session_code)
    if not game_session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not hasattr(game_session, 'party_loot'):
        game_session.party_loot = []

    loot_item = {
        "id": len(game_session.party_loot) + 1,
        "name": item.name,
        "description": item.description,
        "item_type": item.item_type,
        "quantity": item.quantity,
        "weight": item.weight,
        "value": item.value,
        "properties": item.properties,
    }
    game_session.party_loot.append(loot_item)

    return loot_item


class LootClaim(BaseModel):
    loot_id: int
    character_id: int


@app.post("/api/party/loot/claim")
async def claim_party_loot(session_code: str, claim: LootClaim):
    """Move item from party loot to character inventory."""
    game_session = session_manager.get_session(session_code)
    if not game_session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not hasattr(game_session, 'party_loot'):
        raise HTTPException(status_code=404, detail="No loot to claim")

    # Find the loot item
    loot_item = None
    for i, item in enumerate(game_session.party_loot):
        if item["id"] == claim.loot_id:
            loot_item = game_session.party_loot.pop(i)
            break

    if not loot_item:
        raise HTTPException(status_code=404, detail="Loot item not found")

    # Add to character inventory
    with session_scope() as session:
        char = session.query(Character).filter_by(id=claim.character_id).first()
        if not char:
            # Put item back
            game_session.party_loot.append(loot_item)
            raise HTTPException(status_code=404, detail="Character not found")

        new_item = InventoryItem(
            character_id=claim.character_id,
            name=loot_item["name"],
            description=loot_item.get("description", ""),
            item_type=loot_item.get("item_type", "gear"),
            quantity=loot_item.get("quantity", 1),
            weight=loot_item.get("weight", 0),
            value=loot_item.get("value", 0),
            properties=loot_item.get("properties", {}),
        )
        session.add(new_item)

    return {"claimed": True, "item": loot_item["name"]}


@app.websocket("/ws/{session_code}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, session_code: str, player_name: str):
    """WebSocket connection for real-time game updates."""
    # Get or validate session
    game_session = session_manager.get_session(session_code)
    if not game_session:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    # Register player
    is_dm = player_name.lower() == "dm"
    if is_dm:
        game_session.dm_socket = websocket
        logger.info(f"[{session_code}] DM connected")
    else:
        game_session.players[player_name] = websocket
        logger.info(f"[{session_code}] Player '{player_name}' connected")

    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "player_name": player_name,
        "is_dm": is_dm,
        "session_code": game_session.code,
        "location": game_session.current_location,
        "ai_available": is_llm_available(),
    })

    # Broadcast player joined
    await game_session.broadcast({
        "type": "player_joined",
        "player_name": player_name,
        "players": list(game_session.players.keys()),
    })

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "player_action":
                await handle_player_action(websocket, player_name, data, game_session)

            elif msg_type == "dice_roll":
                notation = data.get("notation", "1d20")
                reason = data.get("reason", "")
                result = roll(notation)

                await game_session.broadcast({
                    "type": "dice_roll",
                    "player": player_name,
                    "notation": notation,
                    "result": result.total,
                    "rolls": result.rolls,
                    "reason": reason,
                    "timestamp": datetime.now().isoformat(),
                })

            elif msg_type == "chat":
                # Simple chat message (not AI processed)
                await game_session.broadcast({
                    "type": "chat",
                    "player": player_name,
                    "content": data.get("content", ""),
                    "timestamp": datetime.now().isoformat(),
                })

            elif msg_type == "voice_transcription":
                # Voice input transcribed to text
                text = data.get("text", "")
                if text:
                    await handle_player_action(websocket, player_name, {
                        "type": "player_action",
                        "action": text,
                    }, game_session)

    except WebSocketDisconnect:
        # Clean up
        if is_dm:
            game_session.dm_socket = None
            logger.info(f"[{session_code}] DM disconnected")
        else:
            game_session.players.pop(player_name, None)
            logger.info(f"[{session_code}] Player '{player_name}' disconnected")

        await game_session.broadcast({
            "type": "player_left",
            "player_name": player_name,
            "players": list(game_session.players.keys()),
        })

        # Clean up empty sessions
        session_manager.remove_empty_sessions()


async def handle_player_action(websocket: WebSocket, player_name: str, data: dict, game_session: GameSession):
    """Process a player action through the AI."""
    action = data.get("action", "").strip()
    if not action:
        return

    # Broadcast that player is taking action
    await game_session.broadcast({
        "type": "player_action",
        "player": player_name,
        "action": action,
        "timestamp": datetime.now().isoformat(),
    })

    # Build conversation history for context
    history_text = ""
    # Include last 8 exchanges to keep context manageable and TTS faster
    # Convert deque to list for slicing (deque doesn't support slice notation)
    recent_history = list(game_session.conversation_history)[-8:]
    for entry in recent_history:
        history_text += f"\n[{entry['player']}]: {entry['action']}\n"
        history_text += f"[DM]: {entry['response']}\n"

    # Build context for AI
    context = f"""CURRENT SITUATION:
Location: {game_session.current_location}
{game_session.location_description}
Time: {game_session.time_of_day}
In Combat: {"Yes" if game_session.in_combat else "No"}

CONVERSATION HISTORY:{history_text if history_text else " (This is the start of the adventure)"}

CURRENT ACTION:
[{player_name}]: {action}

Respond as the Dungeon Master:"""

    # Get AI response (streaming)
    if llm_client and is_llm_available():
        await websocket.send_json({
            "type": "dm_typing",
            "status": True,
        })

        try:
            # Stream response
            full_response = ""
            sentence_buffer = ""
            sent_sentences = 0
            tts_enabled = tts_available()

            config = GenerationConfig(
                temperature=0.8,
                max_tokens=200,  # Shorter responses for faster TTS
            )

            async def send_tts_chunk(text: str, chunk_index: int):
                """Generate and send TTS for a sentence chunk with voice detection."""
                try:
                    # Parse text for voice segments (e.g., [VOICE:elderly_male])
                    segments = extract_voice_segments(text)
                    sub_index = 0
                    for voice_name, segment_text in segments:
                        if not segment_text.strip():
                            continue
                        audio_bytes = await tts_synthesize(segment_text, voice_name)
                        if audio_bytes:
                            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                            await game_session.broadcast({
                                "type": "dm_audio_chunk",
                                "audio": audio_b64,
                                "format": "wav",
                                "index": chunk_index,
                                "subIndex": sub_index,
                                "voice": voice_name,
                            })
                            sub_index += 1
                except Exception as e:
                    logger.warning(f"TTS chunk failed: {e}")

            async for token in llm_client.agenerate_stream(
                prompt=context,
                system_prompt=DM_SYSTEM_PROMPT,
                config=config,
            ):
                full_response += token
                sentence_buffer += token

                # Send streaming update (strip voice tags for display)
                display_token = strip_voice_tags(token)
                if display_token:  # Only send if there's content after stripping
                    await websocket.send_json({
                        "type": "dm_response_stream",
                        "token": display_token,
                    })

                # Check for sentence completion and generate TTS
                if tts_enabled and token.rstrip().endswith(('.', '!', '?')):
                    sentences = split_into_sentences(sentence_buffer)
                    if len(sentences) > 1 or sentence_buffer.rstrip().endswith(('.', '!', '?')):
                        # Send TTS for complete sentences (keep voice tags for TTS)
                        text_to_speak = sentences[0] if len(sentences) > 1 else sentence_buffer.strip()
                        if text_to_speak and len(text_to_speak) > 3:
                            asyncio.create_task(send_tts_chunk(text_to_speak, sent_sentences))
                            sent_sentences += 1
                            # Keep remainder in buffer
                            sentence_buffer = ' '.join(sentences[1:]) if len(sentences) > 1 else ""

            # Strip voice tags for display and history
            display_response = strip_voice_tags(full_response)

            # Send complete response to all
            await game_session.broadcast({
                "type": "dm_response",
                "content": display_response,
                "timestamp": datetime.now().isoformat(),
            })

            # Generate TTS for any remaining text (use original with tags)
            if tts_enabled and sentence_buffer.strip():
                asyncio.create_task(send_tts_chunk(sentence_buffer.strip(), sent_sentences))

            # Store in history (without voice tags)
            game_session.conversation_history.append({
                "player": player_name,
                "action": action,
                "response": display_response,
                "timestamp": datetime.now().isoformat(),
            })

        except Exception as e:
            logger.error(f"AI error: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"AI error: {str(e)}",
            })

        finally:
            await websocket.send_json({
                "type": "dm_typing",
                "status": False,
            })
    else:
        # Offline mode - simple response
        await game_session.broadcast({
            "type": "dm_response",
            "content": f"[AI Offline] {player_name} attempts to: {action}\n\nThe DM will respond shortly...",
            "timestamp": datetime.now().isoformat(),
        })


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the FastAPI server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
