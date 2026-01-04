"""FastAPI WebSocket server for AI Dungeon Master."""

import asyncio
import json
import logging
import random
import string
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..llm.client import OllamaClient, GenerationConfig
from .speech import transcribe_audio, is_available as speech_available
from ..game.dice import roll
from ..database.session import init_db, session_scope
from ..database.models import Campaign, Party, Character
from ..characters.races import RACES
from ..characters.classes import CLASSES

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
        self.conversation_history: list[dict] = []
        self.initiative_order: list[str] = []
        self.current_turn: int = 0
        self.in_combat = False
        self.created_at = datetime.now()

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        for player_name, ws in self.players.items():
            try:
                await ws.send_json(message)
            except:
                pass
        if self.dm_socket:
            try:
                await self.dm_socket.send_json(message)
            except:
                pass

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

    yield

    # Cleanup
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
DM_SYSTEM_PROMPT = """You are an expert Dungeon Master for a Pathfinder 1st Edition tabletop RPG game.

Your role is to:
1. Narrate the story and describe scenes vividly but concisely
2. Control NPCs and monsters with distinct personalities
3. Adjudicate rules fairly (but storytelling comes first)
4. Create dramatic tension and memorable moments
5. Respond to player actions with consequences

Keep responses concise (2-4 paragraphs max) since players are on mobile devices.
Use present tense for narration. Be descriptive but not verbose.

When players attempt actions, describe the outcome. If dice rolls are needed, indicate what roll is required.
Format: "Roll [skill/attack] (DC X)" or "Roll [damage dice]"

Current game state will be provided before each player action."""


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
    ai_available = llm_client.is_available() if llm_client else False
    total_players = sum(len(s.players) for s in session_manager.sessions.values())
    return {
        "status": "online",
        "ai_available": ai_available,
        "ai_model": "hermes3:3b" if ai_available else None,
        "speech_available": speech_available(),
        "active_sessions": len(session_manager.sessions),
        "total_players": total_players,
    }


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
                ac=ac,
            )
            session.add(new_char)
            session.flush()

            return {
                "id": new_char.id,
                "name": new_char.name,
                "race": new_char.race,
                "character_class": new_char.character_class,
                "level": new_char.level,
                "max_hp": new_char.max_hp,
                "ac": new_char.ac,
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
        "ai_available": llm_client.is_available() if llm_client else False,
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

    # Build context for AI
    context = f"""CURRENT SITUATION:
Location: {game_session.current_location}
{game_session.location_description}
Time: {game_session.time_of_day}
In Combat: {"Yes" if game_session.in_combat else "No"}

PLAYER: {player_name}
ACTION: {action}"""

    # Get AI response (streaming)
    if llm_client and llm_client.is_available():
        await websocket.send_json({
            "type": "dm_typing",
            "status": True,
        })

        try:
            # Stream response
            full_response = ""
            config = GenerationConfig(
                temperature=0.8,
                max_tokens=300,  # Keep responses concise for mobile
            )

            async for token in llm_client.agenerate_stream(
                prompt=context,
                system_prompt=DM_SYSTEM_PROMPT,
                config=config,
            ):
                full_response += token
                # Send streaming update
                await websocket.send_json({
                    "type": "dm_response_stream",
                    "token": token,
                })

            # Send complete response to all
            await game_session.broadcast({
                "type": "dm_response",
                "content": full_response,
                "timestamp": datetime.now().isoformat(),
            })

            # Store in history
            game_session.conversation_history.append({
                "player": player_name,
                "action": action,
                "response": full_response,
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
