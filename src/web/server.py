"""FastAPI WebSocket server for Mobile DM."""

import asyncio
import base64
import json
import logging
import random
import string
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Callable, Awaitable
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..llm.client import OpenAIClient, GenerationConfig
from .speech import transcribe_audio, is_available as speech_available
from .tts import (
    synthesize as tts_synthesize,
    is_available as tts_available,
    list_voices as tts_list_voices,
    split_into_sentences,
    extract_voice_segments,
    strip_voice_tags,
    prewarm_voices_async,
    coalesce_segments,
)
from .timing import timed_async, get_tracker, record_timing
from ..game.dice import roll
from ..game.session_state import SessionState
from ..game.scene_packet import ScenePacket, build_scene_from_game_state
from ..prompts.builder import (
    build_prompt,
    build_opening_prompt,
    build_action_prompt,
    parse_dm_response,
)
from ..prompts.dm_contract import DM_CONTRACT
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


# XP extraction utilities
def extract_xp_award(text: str) -> Optional[int]:
    """Extract XP award from DM response text.

    Looks for patterns like [XP:500] or [XP: 500]

    Returns:
        XP amount if found, None otherwise
    """
    import re
    match = re.search(r'\[XP:\s*(\d+)\]', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def strip_xp_tags(text: str) -> str:
    """Remove XP tags from text for display."""
    import re
    return re.sub(r'\s*\[XP:\s*\d+\]\s*', '', text, flags=re.IGNORECASE).strip()


# Generate session codes
def generate_session_code() -> str:
    """Generate a random 4-letter session code."""
    return ''.join(random.choices(string.ascii_uppercase, k=4))


class TokenBatcher:
    """Batches streaming tokens for efficient mobile delivery.

    Instead of sending each token individually (100-400 WebSocket messages per response),
    this batches tokens and sends them at intervals for better mobile performance.
    """

    def __init__(
        self,
        broadcast_fn: Callable[[dict], Awaitable[None]],
        batch_size: int = 10,
        interval_ms: int = 150,
    ):
        self.broadcast_fn = broadcast_fn
        self.batch_size = batch_size
        self.interval_ms = interval_ms
        self.buffer: list[str] = []
        self.last_flush = time.monotonic()
        self._flush_task: Optional[asyncio.Task] = None

    async def add_token(self, token: str) -> None:
        """Add a token to the buffer, flushing if batch size or interval reached."""
        self.buffer.append(token)
        elapsed_ms = (time.monotonic() - self.last_flush) * 1000

        # Flush if batch size reached OR interval elapsed
        if len(self.buffer) >= self.batch_size or elapsed_ms >= self.interval_ms:
            await self.flush()

    async def flush(self) -> None:
        """Send all buffered tokens as a single batch message."""
        if not self.buffer:
            return

        combined = "".join(self.buffer)
        self.buffer.clear()
        self.last_flush = time.monotonic()

        await self.broadcast_fn({
            "type": "dm_response_batch",
            "tokens": combined,
        })

    async def start_interval_flush(self) -> None:
        """Start a background task that flushes at regular intervals."""
        async def _interval_loop():
            while True:
                await asyncio.sleep(self.interval_ms / 1000)
                if self.buffer:
                    await self.flush()

        self._flush_task = asyncio.create_task(_interval_loop())

    def stop_interval_flush(self) -> None:
        """Stop the interval flush task."""
        if self._flush_task:
            self._flush_task.cancel()
            self._flush_task = None


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
        # Narrator voice preference (dm_male = old wizard, dm_female = old witch)
        self.narrator_voice: str = "dm_male"
        # Turn-based action collection
        self.all_characters: list[str] = []  # All individual character names
        self.pending_actions: dict[str, str] = {}  # char_name -> action
        self.current_character_index: int = 0  # Whose turn to ask
        self.awaiting_actions: bool = False  # Are we waiting for player actions?
        self.opening_scene_done: bool = False  # Has the DM set the opening scene?
        # Backpressure tracking for slow clients (removed after 3 consecutive timeouts)
        self.slow_client_counts: dict[str, int] = {}
        # Structured prompt state management
        self.session_state = SessionState()
        self.visible_elements: list[str] = []  # Current scene visible elements
        self.environmental: list[str] = []  # Current environmental factors

    def parse_characters_from_players(self):
        """Extract all individual character names from player names (handles 'Name1 & Name2' format)."""
        chars = []
        for player_name in self.players.keys():
            if " & " in player_name:
                chars.extend(player_name.split(" & "))
            else:
                chars.append(player_name)
        self.all_characters = chars
        return chars

    def get_current_character(self) -> Optional[str]:
        """Get the character whose turn it is to act."""
        if not self.all_characters:
            return None
        if self.current_character_index >= len(self.all_characters):
            return None
        return self.all_characters[self.current_character_index]

    def submit_action(self, character_name: str, action: str) -> bool:
        """Submit an action for a character. Returns True if all characters have acted."""
        self.pending_actions[character_name] = action
        # Check if all characters have submitted
        return len(self.pending_actions) >= len(self.all_characters)

    def get_all_pending_actions(self) -> list[tuple[str, str]]:
        """Get all pending actions as (character_name, action) tuples in character order."""
        return [(char, self.pending_actions.get(char, "")) for char in self.all_characters if char in self.pending_actions]

    def reset_round(self):
        """Reset for a new round of actions."""
        self.pending_actions.clear()
        self.current_character_index = 0
        self.awaiting_actions = True

    def advance_to_next_character(self) -> Optional[str]:
        """Move to the next character and return their name, or None if round complete."""
        self.current_character_index += 1
        if self.current_character_index >= len(self.all_characters):
            return None
        return self.all_characters[self.current_character_index]

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

    async def broadcast(self, message: dict, timeout_ms: int = 100):
        """Send message to all connected clients in parallel with timeout.

        Args:
            message: The message dict to broadcast
            timeout_ms: Per-client send timeout in milliseconds (default 100ms)
        """
        if not self.players and not self.dm_socket:
            return

        async def send_to_client(name: str, ws: WebSocket) -> tuple[str, bool]:
            """Send to a single client with timeout. Returns (name, success)."""
            try:
                async with asyncio.timeout(timeout_ms / 1000):
                    await ws.send_json(message)
                return (name, True)
            except asyncio.TimeoutError:
                logger.warning(f"[{self.code}] Send timeout to '{name}' ({timeout_ms}ms)")
                # Track slow client but don't remove on first timeout
                self.slow_client_counts[name] = self.slow_client_counts.get(name, 0) + 1
                if self.slow_client_counts[name] >= 3:
                    logger.warning(f"[{self.code}] Removing slow client '{name}' after 3 timeouts")
                    return (name, False)
                return (name, True)  # Keep client, just skip this message
            except Exception as e:
                logger.warning(f"[{self.code}] Failed to send to '{name}': {e}")
                return (name, False)

        # Build list of send tasks for all players
        tasks = [send_to_client(name, ws) for name, ws in self.players.items()]

        # Add DM socket if present
        if self.dm_socket:
            tasks.append(send_to_client("__DM__", self.dm_socket))

        # Execute all sends in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and remove failed clients
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"[{self.code}] Broadcast exception: {result}")
                    continue
                name, success = result
                if not success:
                    if name == "__DM__":
                        self.dm_socket = None
                    else:
                        self.players.pop(name, None)
                        self.slow_client_counts.pop(name, None)
                elif name != "__DM__" and name in self.slow_client_counts:
                    # Reset slow count on successful send
                    self.slow_client_counts[name] = max(0, self.slow_client_counts.get(name, 0) - 1)

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
llm_client: Optional[OpenAIClient] = None

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

    # Initialize LLM client with OpenAI GPT-4o-mini (fast cloud inference)
    llm_client = OpenAIClient(model="gpt-4o-mini")
    if llm_client.is_available():
        logger.info("AI connected: gpt-4o-mini (OpenAI)")
    else:
        logger.warning("AI not available - check OPENAI_API_KEY env variable")

    # Start auto-save background task
    auto_save_task = asyncio.create_task(auto_save_loop())
    logger.info("Auto-save enabled (every 5 minutes)")

    # Pre-warm TTS voice models in background
    if tts_available():
        asyncio.create_task(prewarm_voices_async())

    yield

    # Cleanup
    auto_save_task.cancel()
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Mobile DM",
    description="Pathfinder 1e tabletop companion",
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
    alignment: Optional[str] = None
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    selected_spells: Optional[List[str]] = None  # Player-selected starting spells


# DM_CONTRACT is now imported from ..prompts.dm_contract


@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the main game page."""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(template_path):
        return FileResponse(template_path)
    return HTMLResponse("<h1>Mobile DM</h1><p>Loading...</p>")


@app.get("/api/status")
async def get_status():
    """Get server and AI status."""
    ai_available = is_llm_available()
    total_players = sum(len(s.players) for s in session_manager.sessions.values())
    return {
        "status": "online",
        "ai_available": ai_available,
        "ai_model": "gpt-4o-mini" if ai_available else None,
        "speech_available": speech_available(),
        "tts_available": tts_available(),
        "active_sessions": len(session_manager.sessions),
        "total_players": total_players,
    }


@app.get("/api/timing")
async def get_timing():
    """Get latency timing statistics for performance monitoring."""
    tracker = get_tracker()
    return {
        "stats": tracker.get_all_stats(),
        "stages": list(tracker._metrics.keys()),
    }


@app.get("/api/voices")
async def get_voices():
    """Get available TTS voices."""
    return {"voices": tts_list_voices(), "available": tts_available()}


@app.post("/api/tts/test")
async def test_tts(voice: str = "dm_male"):
    """Generate test TTS audio with specified voice."""
    if not tts_available():
        raise HTTPException(status_code=503, detail="TTS not available")

    test_phrases = [
        "Welcome, brave adventurer, to the realm of endless possibilities.",
        "Roll for initiative! The goblins are upon you!",
        "You find a dusty tome in the ancient library.",
        "The dragon's eyes gleam with ancient wisdom.",
    ]
    import random
    phrase = random.choice(test_phrases)

    # Map voice preference to actual voice name
    voice_name = "dm_male" if voice in ("male", "dm_male") else "dm_female"
    logger.info(f"TTS test using voice: {voice_name}")

    audio_bytes = await tts_synthesize(phrase, voice_name)
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="TTS generation failed")

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    return {"audio": audio_b64, "format": "wav", "text": phrase, "voice": voice_name}


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


@app.get("/api/monsters")
async def get_monsters():
    """Get all available monsters for the bestiary."""
    import json
    monsters_file = Path(__file__).parent.parent.parent / "data" / "srd" / "monsters.json"
    try:
        with open(monsters_file, "r") as f:
            data = json.load(f)
        # Sort by CR then name
        monsters = sorted(data.get("monsters", []), key=lambda m: (m.get("cr", 0), m.get("name", "")))
        return {"monsters": monsters}
    except FileNotFoundError:
        return {"monsters": [], "error": "Monsters data not found"}
    except Exception as e:
        logger.error(f"Error loading monsters: {e}")
        return {"monsters": [], "error": str(e)}


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
            "alignment": char.alignment,
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
            "feats": char.feats or [],
            "platinum": char.platinum or 0,
            "gold": char.gold or 0,
            "silver": char.silver or 0,
            "copper": char.copper or 0,
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
                alignment=char.alignment,
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
                currency_history=[{
                    "timestamp": datetime.utcnow().isoformat(),
                    "operation": "add",
                    "reason": "Starting gold",
                    "platinum": 0,
                    "gold": starting["gold"],
                    "silver": 0,
                    "copper": 0,
                    "balance_after": {"platinum": 0, "gold": starting["gold"], "silver": 0, "copper": 0}
                }]
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
                # Use player-selected spells if provided, otherwise use defaults
                if char.selected_spells and len(char.selected_spells) > 0:
                    new_char.spells_known = char.selected_spells
                else:
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
    reason: Optional[str] = None  # e.g., "Starting gold", "Bought sword", "Found treasure"


@app.put("/api/characters/{character_id}/currency")
async def update_character_currency(character_id: int, update: CurrencyUpdate):
    """Update character's currency."""
    from datetime import datetime

    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        # Calculate change for history
        old_values = {
            "platinum": char.platinum or 0,
            "gold": char.gold or 0,
            "silver": char.silver or 0,
            "copper": char.copper or 0
        }

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

        # Record transaction in history
        history = char.currency_history or []
        transaction = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": update.operation,
            "reason": update.reason or ("Adjustment" if update.operation == "set" else "Earned" if update.operation == "add" else "Spent"),
            "platinum": update.platinum,
            "gold": update.gold,
            "silver": update.silver,
            "copper": update.copper,
            "balance_after": {
                "platinum": char.platinum,
                "gold": char.gold,
                "silver": char.silver,
                "copper": char.copper
            }
        }
        history.append(transaction)
        # Keep last 50 transactions
        char.currency_history = history[-50:]

        return {
            "platinum": char.platinum,
            "gold": char.gold,
            "silver": char.silver,
            "copper": char.copper,
            "transaction": transaction
        }


@app.get("/api/characters/{character_id}/currency/history")
async def get_currency_history(character_id: int):
    """Get character's currency transaction history."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        return {
            "history": char.currency_history or [],
            "current": {
                "platinum": char.platinum or 0,
                "gold": char.gold or 0,
                "silver": char.silver or 0,
                "copper": char.copper or 0
            }
        }


# ===== ALIGNMENT ENDPOINTS =====

class AlignmentShift(BaseModel):
    new_alignment: str
    reason: str  # e.g., "Saved innocents", "Broke oath", "Act of cruelty"


@app.put("/api/characters/{character_id}/alignment")
async def update_character_alignment(character_id: int, shift: AlignmentShift):
    """Update character's alignment with tracking."""
    valid_alignments = [
        "Lawful Good", "Neutral Good", "Chaotic Good",
        "Lawful Neutral", "True Neutral", "Chaotic Neutral",
        "Lawful Evil", "Neutral Evil", "Chaotic Evil"
    ]
    if shift.new_alignment not in valid_alignments:
        raise HTTPException(status_code=400, detail=f"Invalid alignment: {shift.new_alignment}")

    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        old_alignment = char.alignment or "Unaligned"
        char.alignment = shift.new_alignment

        return {
            "success": True,
            "old_alignment": old_alignment,
            "new_alignment": shift.new_alignment,
            "reason": shift.reason
        }


@app.get("/api/characters/{character_id}/alignment")
async def get_character_alignment(character_id: int):
    """Get character's current alignment."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        return {
            "alignment": char.alignment or "Unaligned",
            "name": char.name
        }


@app.post("/api/detect-alignment")
async def detect_alignment(target_names: List[str], detection_type: str = "evil"):
    """
    Simulates alignment detection spells (Detect Evil, Detect Good, etc.)
    detection_type: "evil", "good", "law", "chaos", or "all"
    """
    results = []
    with session_scope() as session:
        for name in target_names:
            char = session.query(Character).filter_by(name=name).first()
            if char and char.alignment:
                alignment = char.alignment
                detected = False
                aura_strength = "none"

                # Calculate detection based on type
                if detection_type == "evil":
                    detected = "Evil" in alignment
                elif detection_type == "good":
                    detected = "Good" in alignment
                elif detection_type == "law":
                    detected = "Lawful" in alignment
                elif detection_type == "chaos":
                    detected = "Chaotic" in alignment
                elif detection_type == "all":
                    detected = True

                # Aura strength based on level (simplified)
                if detected:
                    level = char.level or 1
                    if level >= 11:
                        aura_strength = "overwhelming"
                    elif level >= 5:
                        aura_strength = "strong"
                    elif level >= 2:
                        aura_strength = "moderate"
                    else:
                        aura_strength = "faint"

                results.append({
                    "name": name,
                    "detected": detected,
                    "aura_strength": aura_strength if detected else "none",
                    "alignment": alignment if detection_type == "all" else None
                })
            else:
                results.append({
                    "name": name,
                    "detected": False,
                    "aura_strength": "none",
                    "error": "Target not found or has no alignment"
                })

    return {"results": results, "detection_type": detection_type}


# ===== SPELLS ENDPOINTS =====

@app.get("/api/characters/{character_id}/spells")
async def get_character_spells(character_id: int):
    """Get character's known spells and spell slots."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        # Get spell names from character
        spell_names = char.spells_known or []

        # Build full spell objects by looking up each spell in SRD data
        spell_data = srd_data.get_spells()
        all_spells = spell_data.get("spells", [])
        cantrips = spell_data.get("cantrips", [])

        # Build lookup dict for quick access
        spell_lookup = {}
        for spell in cantrips:
            spell_lookup[spell["name"].lower()] = {
                "name": spell["name"],
                "level": 0,
                "school": spell.get("school", "universal"),
                "description": spell.get("description", "")[:200] if spell.get("description") else "",
            }
        for spell in all_spells:
            # Get the level for this character's class
            level_info = spell.get("level", {})
            spell_level = 1  # Default
            if isinstance(level_info, dict):
                class_lower = char.character_class.lower() if char.character_class else ""
                spell_level = level_info.get(class_lower, level_info.get("sorcerer", level_info.get("wizard", 1)))
            spell_lookup[spell["name"].lower()] = {
                "name": spell["name"],
                "level": spell_level,
                "school": spell.get("school", "universal"),
                "description": spell.get("description", "")[:200] if spell.get("description") else "",
            }

        # Convert spell names to full spell objects
        spells_with_data = []
        for name in spell_names:
            if isinstance(name, str):
                spell_info = spell_lookup.get(name.lower())
                if spell_info:
                    spells_with_data.append(spell_info)
                else:
                    # Spell not found in SRD - create basic entry
                    spells_with_data.append({
                        "name": name,
                        "level": 0 if "cantrip" in name.lower() else 1,
                        "school": "universal",
                        "description": "",
                    })
            elif isinstance(name, dict):
                # Already a full spell object
                spells_with_data.append(name)

        return {
            "spells_known": spells_with_data,
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


# ===== EXPERIENCE & LEVELING =====

# Pathfinder 1e XP thresholds (Medium progression)
XP_THRESHOLDS = {
    1: 0,
    2: 2000,
    3: 5000,
    4: 9000,
    5: 15000,
    6: 23000,
    7: 35000,
    8: 51000,
    9: 75000,
    10: 105000,
    11: 155000,
    12: 220000,
    13: 315000,
    14: 445000,
    15: 635000,
    16: 890000,
    17: 1300000,
    18: 1800000,
    19: 2550000,
    20: 3600000,
}


def get_level_for_xp(xp: int) -> int:
    """Determine character level based on XP total."""
    level = 1
    for lvl, threshold in XP_THRESHOLDS.items():
        if xp >= threshold:
            level = lvl
    return level


def get_xp_for_next_level(current_level: int) -> int:
    """Get XP required for next level."""
    if current_level >= 20:
        return 0  # Max level
    return XP_THRESHOLDS.get(current_level + 1, 0)


@app.get("/api/characters/{character_id}/experience")
async def get_character_experience(character_id: int):
    """Get character's experience and level progress."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        current_xp = char.experience or 0
        current_level = char.level or 1
        xp_for_current = XP_THRESHOLDS.get(current_level, 0)
        xp_for_next = get_xp_for_next_level(current_level)

        return {
            "experience": current_xp,
            "level": current_level,
            "xp_for_current_level": xp_for_current,
            "xp_for_next_level": xp_for_next,
            "xp_to_next": max(0, xp_for_next - current_xp) if xp_for_next > 0 else 0,
            "can_level_up": current_xp >= xp_for_next and current_level < 20,
        }


class XPAward(BaseModel):
    amount: int
    reason: Optional[str] = None


@app.post("/api/characters/{character_id}/experience/award")
async def award_experience(character_id: int, award: XPAward):
    """Award XP to a character and check for level up."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        old_xp = char.experience or 0
        old_level = char.level or 1
        new_xp = old_xp + award.amount
        char.experience = new_xp

        # Check for level up
        new_level = get_level_for_xp(new_xp)
        leveled_up = new_level > old_level

        if leveled_up:
            char.level = new_level

        return {
            "experience": new_xp,
            "old_level": old_level,
            "new_level": new_level,
            "leveled_up": leveled_up,
            "xp_awarded": award.amount,
            "reason": award.reason,
            "xp_for_next_level": get_xp_for_next_level(new_level),
        }


@app.post("/api/characters/{character_id}/level-up")
async def level_up_character(character_id: int):
    """Apply level up to a character (increase HP, update spell slots, etc.)."""
    with session_scope() as session:
        char = session.query(Character).filter_by(id=character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")

        # Check if character has enough XP
        current_xp = char.experience or 0
        current_level = char.level or 1
        xp_needed = get_xp_for_next_level(current_level)

        if current_level >= 20:
            raise HTTPException(status_code=400, detail="Already at maximum level")

        if current_xp < xp_needed:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough XP. Need {xp_needed}, have {current_xp}"
            )

        new_level = current_level + 1
        char.level = new_level

        # Increase HP based on class hit die
        hit_dice = {
            "Barbarian": 12, "Fighter": 10, "Paladin": 10, "Ranger": 10,
            "Cleric": 8, "Druid": 8, "Monk": 8, "Rogue": 8, "Bard": 8,
            "Sorcerer": 6, "Wizard": 6,
        }
        hit_die = hit_dice.get(char.character_class, 8)
        con_mod = ((char.constitution or 10) - 10) // 2

        # Average HP gain (half die + 1 + con mod, minimum 1)
        hp_gain = max(1, (hit_die // 2) + 1 + con_mod)
        char.max_hp = (char.max_hp or 0) + hp_gain
        char.current_hp = (char.current_hp or 0) + hp_gain

        # Update BAB based on class
        full_bab = ["Barbarian", "Fighter", "Paladin", "Ranger"]
        three_quarter_bab = ["Bard", "Cleric", "Druid", "Monk", "Rogue"]
        # Half BAB: Sorcerer, Wizard

        if char.character_class in full_bab:
            char.base_attack_bonus = new_level
        elif char.character_class in three_quarter_bab:
            char.base_attack_bonus = (new_level * 3) // 4
        else:
            char.base_attack_bonus = new_level // 2

        # Update spell slots for casters
        if char.spellcaster and char.character_class in STARTING_SPELLS:
            # This would need more complex logic for accurate spell slot progression
            # For now, just add a slot at the highest known level
            slots = char.spell_slots or {}
            for level_key in sorted(slots.keys(), key=int, reverse=True):
                if int(level_key) > 0:
                    slots[level_key]["total"] = slots[level_key].get("total", 0) + 1
                    break
            char.spell_slots = slots
            char.caster_level = (char.caster_level or 0) + 1

        return {
            "level": new_level,
            "hp_gained": hp_gain,
            "new_max_hp": char.max_hp,
            "base_attack_bonus": char.base_attack_bonus,
            "message": f"Congratulations! You are now level {new_level}!",
        }


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

# Starting spell allowances by class (how many the player can pick)
STARTING_SPELL_ALLOWANCES = {
    "Wizard": {"cantrips": 3, "spells": 3, "info": "Choose 3 cantrips and 3 1st-level spells for your spellbook"},
    "Sorcerer": {"cantrips": 4, "spells": 2, "info": "Choose 4 cantrips and 2 1st-level spells known"},
    "Cleric": {"cantrips": 3, "spells": 2, "info": "Choose 3 orisons and 2 1st-level spells to prepare"},
    "Druid": {"cantrips": 3, "spells": 2, "info": "Choose 3 orisons and 2 1st-level spells to prepare"},
    "Bard": {"cantrips": 4, "spells": 2, "info": "Choose 4 cantrips and 2 1st-level spells known"},
}


@app.get("/api/classes/{class_name}/starting-spells")
async def get_starting_spells(class_name: str):
    """Get available starting spells for a class."""
    # Check if class exists and is a spellcaster
    if class_name not in CLASSES:
        raise HTTPException(status_code=404, detail="Class not found")

    cls = CLASSES[class_name]
    if not cls.is_spellcaster():
        return {
            "available_spells": [],
            "cantrips_allowed": 0,
            "spells_allowed": 0,
            "info": "This class does not cast spells at level 1"
        }

    # Get spell allowances
    allowances = STARTING_SPELL_ALLOWANCES.get(class_name, {"cantrips": 0, "spells": 0, "info": ""})

    # Get available spells for this class from SRD
    spell_data = srd_data.get_spells()
    all_spells = spell_data.get("spells", [])
    cantrips = spell_data.get("cantrips", [])  # Cantrips are in a separate array
    available = []

    class_lower = class_name.lower()

    # Process cantrips first (level 0)
    for spell in cantrips:
        level_info = spell.get("level", {})
        if isinstance(level_info, dict) and class_lower in level_info:
            available.append({
                "name": spell["name"],
                "level": 0,
                "school": spell.get("school", ""),
                "description": spell.get("description", "")[:100] + "..." if spell.get("description", "") else ""
            })

    # Then process 1st level spells
    for spell in all_spells:
        level_info = spell.get("level", {})
        if isinstance(level_info, dict) and class_lower in level_info:
            spell_level = level_info[class_lower]
            # Only include 1st level spells for starting
            if spell_level == 1:
                available.append({
                    "name": spell["name"],
                    "level": spell_level,
                    "school": spell.get("school", ""),
                    "description": spell.get("description", "")[:100] + "..." if spell.get("description", "") else ""
                })

    # Sort by level, then name
    available.sort(key=lambda s: (s["level"], s["name"]))

    return {
        "available_spells": available,
        "cantrips_allowed": allowances["cantrips"],
        "spells_allowed": allowances["spells"],
        "info": allowances["info"]
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

    # Update character list for turn-based system
    game_session.parse_characters_from_players()

    # If this is the first player, initialize the turn system and generate opening scene
    if len(game_session.all_characters) > 0 and not game_session.opening_scene_done:
        game_session.reset_round()

        # Generate the opening scene (DM sets the stage)
        await generate_opening_scene(game_session)

        # Now tell the first character it's their turn
        first_char = game_session.get_current_character()
        if first_char:
            await game_session.broadcast({
                "type": "character_turn",
                "character": first_char,
                "all_characters": game_session.all_characters,
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

            elif msg_type == "set_narrator_voice":
                # Set the narrator voice preference (dm_male = wizard, dm_female = witch)
                voice = data.get("voice", "dm_male")
                if voice in ("dm_male", "dm_female", "male", "female"):
                    # Normalize voice name
                    if voice == "male":
                        voice = "dm_male"
                    elif voice == "female":
                        voice = "dm_female"
                    game_session.narrator_voice = voice
                    logger.info(f"[{session_code}] Narrator voice set to: {voice}")

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


async def generate_opening_scene(game_session: GameSession):
    """Generate the opening scene for a new game."""
    if game_session.opening_scene_done:
        return

    if not llm_client or not is_llm_available():
        # Fallback for offline mode
        await game_session.broadcast({
            "type": "dm_response",
            "content": f"Welcome to the Rusty Dragon Inn! The smell of roasted meat and fresh bread fills the air. What do you do, {game_session.all_characters[0]}?",
            "timestamp": datetime.now().isoformat(),
        })
        game_session.opening_scene_done = True
        return

    game_session.opening_scene_done = True

    # Build detailed character info including alignment
    party_details = []
    with session_scope() as db_session:
        for char_name in game_session.all_characters:
            char = db_session.query(Character).filter_by(name=char_name).first()
            if char:
                align = char.alignment or "Unaligned"
                party_details.append(f"- {char.name}: {char.race} {char.character_class} ({align})")
            else:
                party_details.append(f"- {char_name}")

    party_text = "\n".join(party_details) if party_details else ", ".join(game_session.all_characters)

    # Roll initiative for all characters
    import random
    initiative_rolls = {}
    for char_name in game_session.all_characters:
        roll = random.randint(1, 20)
        initiative_rolls[char_name] = roll

    # Sort by initiative (highest first)
    sorted_initiative = sorted(initiative_rolls.items(), key=lambda x: x[1], reverse=True)
    game_session.initiative_order = [name for name, _ in sorted_initiative]

    # Build initiative announcement
    init_text = "\n".join([f"- {name}: {roll}" for name, roll in sorted_initiative])
    first_player = game_session.initiative_order[0]
    first_roll = initiative_rolls[first_player]

    # Initialize session state with party info
    game_session.session_state.party_summary = party_text
    game_session.session_state.initiative_order = game_session.initiative_order
    game_session.session_state.location = "The Rusty Dragon Inn"
    game_session.session_state.location_detail = "Main hall, evening"
    game_session.session_state.current_objective = "Begin your adventure"

    # Set initial visible elements for the tavern
    game_session.visible_elements = [
        "Warm tavern with crackling fireplace",
        "Local patrons drinking quietly",
        "Bar counter with Ameiko polishing glasses",
        "Stairs leading to guest rooms",
    ]
    game_session.environmental = ["Warm atmosphere", "Normal lighting"]

    # Build structured opening prompt
    opening_prompt = build_opening_prompt(
        session_state=game_session.session_state,
        party_text=party_text,
        initiative_text=init_text,
        first_player=first_player,
        first_roll=first_roll,
    )

    try:
        # Broadcast typing indicator
        await game_session.broadcast({"type": "dm_typing", "status": True})

        full_response = ""
        config = GenerationConfig(temperature=0.8, max_tokens=300)

        # Token batcher for efficient mobile streaming (10 tokens or 150ms intervals)
        token_batcher = TokenBatcher(
            broadcast_fn=game_session.broadcast,
            batch_size=10,
            interval_ms=150,
        )
        await token_batcher.start_interval_flush()

        # Track LLM timing
        llm_start = time.perf_counter()
        first_token_time = None
        token_count = 0

        async for token in llm_client.agenerate_stream(
            prompt=opening_prompt,
            system_prompt=DM_CONTRACT,
            config=config,
        ):
            if first_token_time is None:
                first_token_time = time.perf_counter()
                record_timing("llm.first_token", (first_token_time - llm_start) * 1000, context="opening")

            token_count += 1
            full_response += token
            display_token = strip_voice_tags(token)
            if display_token:
                await token_batcher.add_token(display_token)

        # Record total LLM time
        llm_total_ms = (time.perf_counter() - llm_start) * 1000
        record_timing("llm.total", llm_total_ms, context="opening", tokens=token_count)

        # Flush any remaining batched tokens and stop the interval task
        token_batcher.stop_interval_flush()
        await token_batcher.flush()

        # Parse structured response for player text and state update
        player_text, state_update = parse_dm_response(full_response)
        display_response = strip_voice_tags(player_text)

        # Apply state update if present
        if state_update:
            game_session.session_state.apply_state_update(state_update)
            logger.debug(f"[{game_session.code}] Applied state update: {state_update}")

        await game_session.broadcast({
            "type": "dm_response",
            "content": display_response,
            "timestamp": datetime.now().isoformat(),
        })

        # Generate TTS for opening (parallel for faster audio delivery)
        if tts_available():
            segments = extract_voice_segments(full_response, game_session.narrator_voice)
            # Coalesce short segments to reduce TTS calls
            segments = coalesce_segments(segments)

            async def synthesize_and_broadcast(idx: int, voice: str, text: str):
                """Synthesize and broadcast a single TTS segment."""
                if not text.strip():
                    return
                audio_bytes = await tts_synthesize(text, voice)
                if audio_bytes:
                    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                    await game_session.broadcast({
                        "type": "dm_audio_chunk",
                        "audio": audio_b64,
                        "format": "wav",
                        "index": idx,
                        "voice": voice,
                    })

            # Run TTS tasks in parallel (semaphore in tts.py limits concurrency)
            tts_tasks = [
                synthesize_and_broadcast(i, voice_name, segment_text)
                for i, (voice_name, segment_text) in enumerate(segments)
            ]
            await asyncio.gather(*tts_tasks)

        # Store in history
        game_session.conversation_history.append({
            "player": "System",
            "action": "Game started",
            "response": display_response,
            "timestamp": datetime.now().isoformat(),
        })

        # Broadcast initiative order and first turn
        await game_session.broadcast({
            "type": "initiative_order",
            "order": game_session.initiative_order,
        })
        await game_session.broadcast({
            "type": "character_turn",
            "character": first_player,
            "all_characters": game_session.all_characters,
        })

    except Exception as e:
        logger.error(f"Opening scene error: {e}")
        # Roll initiative even in error case
        import random
        for char_name in game_session.all_characters:
            if char_name not in initiative_rolls:
                initiative_rolls[char_name] = random.randint(1, 20)
        sorted_init = sorted(initiative_rolls.items(), key=lambda x: x[1], reverse=True)
        game_session.initiative_order = [name for name, _ in sorted_init]
        first_player = game_session.initiative_order[0] if game_session.initiative_order else game_session.all_characters[0]

        await game_session.broadcast({
            "type": "dm_response",
            "content": f"Welcome, adventurers! You find yourselves in the Rusty Dragon Inn. {first_player}, it's your turn. What do you do?",
            "timestamp": datetime.now().isoformat(),
        })
        await game_session.broadcast({
            "type": "initiative_order",
            "order": game_session.initiative_order,
        })
        await game_session.broadcast({
            "type": "character_turn",
            "character": first_player,
            "all_characters": game_session.all_characters,
        })

    finally:
        await game_session.broadcast({"type": "dm_typing", "status": False})


async def handle_player_action(websocket: WebSocket, player_name: str, data: dict, game_session: GameSession):
    """Process a player action through the AI with turn-based system."""
    action = data.get("action", "").strip()
    character_name = data.get("character", player_name)  # Which character is acting
    if not action:
        return

    # Broadcast that this character is taking action
    await game_session.broadcast({
        "type": "player_action",
        "player": character_name,
        "action": action,
        "timestamp": datetime.now().isoformat(),
    })

    # Submit action for this character
    all_acted = game_session.submit_action(character_name, action)

    if not all_acted:
        # Not everyone has acted yet - move to next character
        next_char = game_session.advance_to_next_character()
        if next_char:
            await game_session.broadcast({
                "type": "action_submitted",
                "character": character_name,
            })
            await game_session.broadcast({
                "type": "character_turn",
                "character": next_char,
                "all_characters": game_session.all_characters,
            })
            return
    else:
        # All characters have acted - notify and proceed to DM narration
        await game_session.broadcast({
            "type": "all_actions_received",
        })

    # Build combined actions from all characters
    all_actions = game_session.get_all_pending_actions()

    # Build detailed character info for party summary
    party_details = []
    with session_scope() as db_session:
        for char_name in game_session.all_characters:
            char = db_session.query(Character).filter_by(name=char_name).first()
            if char:
                hp_str = f"{char.current_hp}/{char.max_hp} HP" if char.max_hp else "full HP"
                party_details.append(f"{char.name} ({char.character_class} {hp_str})")
            else:
                party_details.append(char_name)

    # Update session state with current party info
    game_session.session_state.party_summary = ", ".join(party_details)
    game_session.session_state.in_combat = game_session.in_combat
    game_session.session_state.initiative_order = game_session.initiative_order
    game_session.session_state.time_of_day = game_session.time_of_day
    game_session.session_state.location = game_session.current_location

    # Determine next player in initiative order
    initiative_order = game_session.initiative_order if game_session.initiative_order else game_session.all_characters
    next_player = initiative_order[0] if initiative_order else game_session.all_characters[0]

    # Build scene packet with current context
    scene = ScenePacket()
    scene.immediate_location = f"{game_session.current_location} - {game_session.location_description}"
    scene.visible_elements = game_session.visible_elements
    scene.environmental = game_session.environmental
    scene.in_combat = game_session.in_combat
    scene.initiative_order = initiative_order
    scene.current_turn = next_player
    scene.player_actions = all_actions

    # Build structured action prompt
    context = build_action_prompt(
        session_state=game_session.session_state,
        scene=scene,
        next_player=next_player,
    )

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

            # Soft token cap for response length control
            SOFT_TOKEN_CAP = 250   # Start looking for natural exit point
            HARD_TOKEN_CAP = 350   # Absolute maximum

            config = GenerationConfig(
                temperature=0.8,
                max_tokens=HARD_TOKEN_CAP,
            )

            # Token batcher for efficient mobile streaming (10 tokens or 150ms intervals)
            token_batcher = TokenBatcher(
                broadcast_fn=game_session.broadcast,
                batch_size=10,
                interval_ms=150,
            )
            await token_batcher.start_interval_flush()

            async def send_tts_chunk(text: str, chunk_index: int):
                """Generate and send TTS for a sentence chunk with voice detection."""
                try:
                    # Parse text for voice segments, using session narrator voice preference
                    segments = extract_voice_segments(text, game_session.narrator_voice)
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

            # Track LLM timing
            llm_start = time.perf_counter()
            first_token_time = None
            token_count = 0

            async for token in llm_client.agenerate_stream(
                prompt=context,
                system_prompt=DM_CONTRACT,
                config=config,
            ):
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                    record_timing("llm.first_token", (first_token_time - llm_start) * 1000, context="action")

                token_count += 1
                full_response += token
                sentence_buffer += token

                # Send streaming update (strip voice tags for display)
                display_token = strip_voice_tags(token)
                if display_token:  # Only send if there's content after stripping
                    await token_batcher.add_token(display_token)

                # Soft cap: stop at sentence boundary after SOFT_TOKEN_CAP
                if token_count >= SOFT_TOKEN_CAP:
                    if full_response.rstrip().endswith(('.', '!', '?')):
                        # Check if we have a turn prompt in last 60 chars
                        last_chunk = full_response.lower()[-60:]
                        if "what do you do" in last_chunk or "your turn" in last_chunk:
                            break

                # Check for TTS trigger points - start audio earlier for better UX
                should_speak = False
                text_to_speak = ""

                if tts_enabled:
                    # Trigger on sentence endings
                    if token.rstrip().endswith(('.', '!', '?')):
                        sentences = split_into_sentences(sentence_buffer)
                        if len(sentences) > 1 or sentence_buffer.rstrip().endswith(('.', '!', '?')):
                            text_to_speak = sentences[0] if len(sentences) > 1 else sentence_buffer.strip()
                            sentence_buffer = ' '.join(sentences[1:]) if len(sentences) > 1 else ""
                            should_speak = True
                    # For first chunk, also trigger on comma or after 80+ chars to start audio sooner
                    elif sent_sentences == 0 and len(sentence_buffer) > 80:
                        if ',' in sentence_buffer:
                            comma_idx = sentence_buffer.rfind(',')
                            text_to_speak = sentence_buffer[:comma_idx + 1].strip()
                            sentence_buffer = sentence_buffer[comma_idx + 1:].strip()
                            should_speak = True

                if should_speak and text_to_speak and len(text_to_speak) > 3:
                    asyncio.create_task(send_tts_chunk(text_to_speak, sent_sentences))
                    sent_sentences += 1

            # Record total LLM time
            llm_total_ms = (time.perf_counter() - llm_start) * 1000
            record_timing("llm.total", llm_total_ms, context="action", tokens=token_count)

            # Flush any remaining batched tokens and stop the interval task
            token_batcher.stop_interval_flush()
            await token_batcher.flush()

            # Parse structured response for player text and state update
            player_text, state_update = parse_dm_response(full_response)

            # Apply state update if present
            if state_update:
                game_session.session_state.apply_state_update(state_update)
                logger.debug(f"[{game_session.code}] Applied state update: {state_update}")

            # Strip voice tags and XP tags for display and history
            display_response = strip_voice_tags(player_text)
            display_response = strip_xp_tags(display_response)

            # Extract and award XP if present
            xp_award = extract_xp_award(full_response)
            if xp_award and xp_award > 0:
                # Award XP to all characters in the party
                num_chars = len(game_session.all_characters)
                xp_per_char = xp_award // max(1, num_chars)

                with session_scope() as db_session:
                    for char_name in game_session.all_characters:
                        char = db_session.query(Character).filter_by(name=char_name).first()
                        if char:
                            old_level = char.level or 1
                            char.experience = (char.experience or 0) + xp_per_char
                            new_level = get_level_for_xp(char.experience)
                            if new_level > old_level:
                                char.level = new_level

                # Broadcast XP award to all players
                await game_session.broadcast({
                    "type": "xp_awarded",
                    "total_xp": xp_award,
                    "xp_per_character": xp_per_char,
                    "characters": game_session.all_characters,
                    "timestamp": datetime.now().isoformat(),
                })
                logger.info(f"[{game_session.code}] Awarded {xp_award} XP ({xp_per_char} each to {num_chars} characters)")

            # Send complete response to all
            await game_session.broadcast({
                "type": "dm_response",
                "content": display_response,
                "timestamp": datetime.now().isoformat(),
            })

            # Generate TTS for any remaining text (use original with tags)
            if tts_enabled and sentence_buffer.strip():
                asyncio.create_task(send_tts_chunk(sentence_buffer.strip(), sent_sentences))

            # Store in history (all actions from this round)
            all_actions_text = "; ".join([f"{char}: {act}" for char, act in all_actions])
            game_session.conversation_history.append({
                "player": "Party",
                "action": all_actions_text,
                "response": display_response,
                "timestamp": datetime.now().isoformat(),
            })

            # Start a new round - reset and ask the first character in initiative order
            game_session.reset_round()
            first_char = game_session.initiative_order[0] if game_session.initiative_order else game_session.all_characters[0]
            await game_session.broadcast({
                "type": "character_turn",
                "character": first_char,
                "all_characters": game_session.all_characters,
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
            "content": f"[Offline] Actions submitted. The DM will respond when online.",
            "timestamp": datetime.now().isoformat(),
        })


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the FastAPI server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
