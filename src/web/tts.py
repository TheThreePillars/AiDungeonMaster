"""Text-to-speech service using Piper TTS."""

import io
import logging
import os
import wave
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Voice models directory
VOICES_DIR = Path(__file__).parent.parent.parent / "models" / "voices"

# Lazy loaded voice models
_voice_models: dict = {}

# Voice profile mappings for NPCs
VOICE_PROFILES = {
    # Default/DM voices - distinguished British storyteller
    "default": "en_GB-alan-medium",
    "dm": "en_GB-alan-medium",
    "narrator": "en_GB-alan-medium",

    # Male character voices
    "elderly_male": "en_US-john-medium",      # Wise old sage, wizard
    "young_male": "en_US-lessac-medium",      # Young adventurer
    "gruff": "en_US-danny-low",               # Dwarf, guard, blacksmith
    "noble_male": "en_GB-alan-medium",        # Lord, elf noble, refined
    "commoner_male": "en_US-danny-low",       # Farmer, merchant, tavern keeper

    # Female character voices
    "elderly_female": "en_GB-southern_english_female-low",  # Old witch, wise woman
    "young_female": "en_US-amy-medium",       # Barmaid, princess, young adventurer
    "noble_female": "en_GB-southern_english_female-low",    # Lady, elf noble
    "commoner_female": "en_US-amy-medium",    # Villager, merchant

    # Special character types
    "mysterious": "en_GB-alan-medium",        # Mysterious stranger, hooded figure
    "menacing": "en_US-danny-low",            # Villain, bandit leader
    "cheerful": "en_US-amy-medium",           # Friendly NPC, happy merchant
    "authoritative": "en_US-john-medium",     # King, commander, priest
}


def is_available() -> bool:
    """Check if Piper TTS is available."""
    try:
        from piper import PiperVoice
        # Check if at least one voice model exists
        if not VOICES_DIR.exists():
            return False
        onnx_files = list(VOICES_DIR.glob("*.onnx"))
        return len(onnx_files) > 0
    except ImportError:
        return False


def list_voices() -> list[dict]:
    """List available voice models."""
    voices = []
    if not VOICES_DIR.exists():
        return voices

    for onnx_file in VOICES_DIR.glob("*.onnx"):
        voice_name = onnx_file.stem
        json_file = onnx_file.with_suffix(".onnx.json")
        if json_file.exists():
            voices.append({
                "id": voice_name,
                "name": voice_name.replace("-", " ").replace("_", " ").title(),
                "path": str(onnx_file),
            })

    return voices


def get_voice(voice_name: str = "default"):
    """Get or load a Piper voice model."""
    global _voice_models

    # Resolve voice profile to actual model name
    model_name = VOICE_PROFILES.get(voice_name, VOICE_PROFILES["default"])

    # Check cache
    if model_name in _voice_models:
        return _voice_models[model_name]

    try:
        from piper import PiperVoice

        # Find the model file
        model_path = VOICES_DIR / f"{model_name}.onnx"
        if not model_path.exists():
            # Try to find any available model as fallback
            available = list(VOICES_DIR.glob("*.onnx"))
            if available:
                model_path = available[0]
                logger.warning(f"Voice '{model_name}' not found, using {model_path.stem}")
            else:
                logger.error("No voice models found")
                return None

        logger.info(f"Loading Piper voice: {model_path.stem}")
        voice = PiperVoice.load(str(model_path))
        _voice_models[model_name] = voice
        return voice

    except ImportError:
        logger.warning("piper-tts not installed. Run: pip install piper-tts")
        return None
    except Exception as e:
        logger.error(f"Failed to load voice model: {e}")
        return None


def synthesize_sync(text: str, voice_name: str = "default") -> Optional[bytes]:
    """
    Synthesize text to speech (synchronous).

    Args:
        text: Text to synthesize
        voice_name: Voice profile name (default, dm, elderly_male, etc.)

    Returns:
        WAV audio bytes or None if failed
    """
    if not text or not text.strip():
        return None

    voice = get_voice(voice_name)
    if voice is None:
        return None

    try:
        # Generate audio chunks
        audio_buffer = io.BytesIO()

        with wave.open(audio_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(voice.config.sample_rate)

            # Synthesize and write audio chunks
            for audio_chunk in voice.synthesize(text):
                wav_file.writeframes(audio_chunk.audio_int16_bytes)

        audio_buffer.seek(0)
        return audio_buffer.read()

    except Exception as e:
        logger.error(f"TTS synthesis error: {e}")
        return None


async def synthesize(text: str, voice_name: str = "default") -> Optional[bytes]:
    """
    Synthesize text to speech (async wrapper).

    Args:
        text: Text to synthesize
        voice_name: Voice profile name

    Returns:
        WAV audio bytes or None if failed
    """
    import asyncio

    # Run synthesis in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, synthesize_sync, text, voice_name)


def extract_voice_segments(text: str) -> list[tuple[str, str]]:
    """
    Extract voice-tagged segments from text.

    Parses text with [VOICE:name] tags and returns segments with their voice.

    Args:
        text: Text potentially containing [VOICE:name] tags

    Returns:
        List of (voice_name, text_segment) tuples

    Example:
        Input: '[VOICE:elderly_male] "Hello there!" The old man smiled.'
        Output: [("elderly_male", '"Hello there!" The old man smiled.')]
    """
    import re

    segments = []
    current_voice = "dm"

    # Pattern to match [VOICE:name] tags
    pattern = r'\[VOICE:(\w+)\]'

    # Split by voice tags
    parts = re.split(pattern, text)

    for i, part in enumerate(parts):
        if i % 2 == 0:
            # This is text content
            if part.strip():
                segments.append((current_voice, part.strip()))
        else:
            # This is a voice name
            current_voice = part.lower()

    # If no segments found, return the whole text with default voice
    if not segments and text.strip():
        segments = [("dm", text.strip())]

    return segments


async def synthesize_with_voices(text: str) -> list[tuple[str, bytes]]:
    """
    Synthesize text that may contain multiple voice segments.

    Args:
        text: Text potentially containing [VOICE:name] tags

    Returns:
        List of (voice_name, audio_bytes) tuples
    """
    segments = extract_voice_segments(text)
    results = []

    for voice_name, segment_text in segments:
        audio = await synthesize(segment_text, voice_name)
        if audio:
            results.append((voice_name, audio))

    return results


# Download helper for voice models
def download_voice(voice_id: str = "en_US-lessac-medium") -> bool:
    """
    Download a Piper voice model from Hugging Face.

    Args:
        voice_id: Voice identifier (e.g., "en_US-lessac-medium")

    Returns:
        True if successful, False otherwise
    """
    import urllib.request

    VOICES_DIR.mkdir(parents=True, exist_ok=True)

    # Parse voice ID
    parts = voice_id.split("-")
    if len(parts) < 3:
        logger.error(f"Invalid voice ID format: {voice_id}")
        return False

    lang_code = parts[0]  # e.g., "en_US"
    lang_parts = lang_code.split("_")
    lang = lang_parts[0]  # e.g., "en"

    speaker = parts[1]  # e.g., "lessac"
    quality = parts[2]  # e.g., "medium"

    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

    files_to_download = [
        f"{lang}/{lang_code}/{speaker}/{quality}/{voice_id}.onnx",
        f"{lang}/{lang_code}/{speaker}/{quality}/{voice_id}.onnx.json",
    ]

    try:
        for file_path in files_to_download:
            url = f"{base_url}/{file_path}"
            local_path = VOICES_DIR / file_path.split("/")[-1]

            if local_path.exists():
                logger.info(f"Voice file already exists: {local_path.name}")
                continue

            logger.info(f"Downloading {local_path.name}...")
            urllib.request.urlretrieve(url, local_path)
            logger.info(f"Downloaded: {local_path.name}")

        return True

    except Exception as e:
        logger.error(f"Failed to download voice: {e}")
        return False
