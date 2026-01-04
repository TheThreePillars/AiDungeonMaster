"""FastAPI WebSocket server for AI Dungeon Master."""

import asyncio
import json
import logging
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Game state
class GameSession:
    """Manages a single game session."""

    def __init__(self):
        self.players: dict[str, WebSocket] = {}
        self.dm_socket: Optional[WebSocket] = None
        self.current_location = "The Rusty Dragon Inn"
        self.location_description = "A warm and inviting tavern in Sandpoint."
        self.time_of_day = "evening"
        self.conversation_history: list[dict] = []
        self.initiative_order: list[str] = []
        self.current_turn: int = 0
        self.in_combat = False

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


# Global state
game_session = GameSession()
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
    return {
        "status": "online",
        "ai_available": ai_available,
        "ai_model": "hermes3:3b" if ai_available else None,
        "speech_available": speech_available(),
        "players_connected": len(game_session.players),
        "in_combat": game_session.in_combat,
        "current_location": game_session.current_location,
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


@app.post("/api/roll")
async def roll_dice(request: DiceRollRequest):
    """Roll dice and broadcast result."""
    result = roll(request.notation)

    message = {
        "type": "dice_roll",
        "player": request.player_name,
        "notation": request.notation,
        "result": result.total,
        "rolls": result.rolls,
        "reason": request.reason,
        "timestamp": datetime.now().isoformat(),
    }

    await game_session.broadcast(message)
    return message


@app.websocket("/ws/{player_name}")
async def websocket_endpoint(websocket: WebSocket, player_name: str):
    """WebSocket connection for real-time game updates."""
    await websocket.accept()

    # Register player
    is_dm = player_name.lower() == "dm"
    if is_dm:
        game_session.dm_socket = websocket
        logger.info("DM connected")
    else:
        game_session.players[player_name] = websocket
        logger.info(f"Player '{player_name}' connected")

    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "player_name": player_name,
        "is_dm": is_dm,
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
                await handle_player_action(websocket, player_name, data)

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
                    })

    except WebSocketDisconnect:
        # Clean up
        if is_dm:
            game_session.dm_socket = None
            logger.info("DM disconnected")
        else:
            game_session.players.pop(player_name, None)
            logger.info(f"Player '{player_name}' disconnected")

        await game_session.broadcast({
            "type": "player_left",
            "player_name": player_name,
            "players": list(game_session.players.keys()),
        })


async def handle_player_action(websocket: WebSocket, player_name: str, data: dict):
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
