"""Text-to-speech service using Piper TTS."""

import asyncio
import io
import logging
import threading
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Set

from .timing import timed_sync, record_timing

logger = logging.getLogger(__name__)

# Voice models directory
VOICES_DIR = Path(__file__).parent.parent.parent / "models" / "voices"

# Thread-safe voice model cache
_voice_models: dict = {}
_voice_lock = threading.Lock()
_prewarmed_voices: Set[str] = set()

# TTS concurrency control
_tts_semaphore: Optional[asyncio.Semaphore] = None
_tts_executor: Optional[ThreadPoolExecutor] = None

# Voice profile mappings for NPCs
VOICE_PROFILES = {
    # Default narrator voices - elderly wizard/witch storyteller
    "default": "en_US-john-medium",           # Old wizard by default
    "dm": "en_US-john-medium",                # Old wizard narrator (male)
    "dm_male": "en_US-john-medium",           # Old wizard narrator
    "dm_female": "en_GB-southern_english_female-low",  # Old witch narrator
    "narrator": "en_US-john-medium",          # Same as dm

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

# Core voices to pre-warm at startup (deduplicated from VOICE_PROFILES)
CORE_VOICES = {
    "en_US-john-medium",       # dm, narrator, elderly_male, authoritative
    "en_US-danny-low",         # gruff, menacing, commoner_male
    "en_US-amy-medium",        # young_female, cheerful, commoner_female
    "en_GB-alan-medium",       # noble_male, mysterious
    "en_GB-southern_english_female-low",  # dm_female, elderly_female, noble_female
}

# Minimum characters before emitting a TTS segment
MIN_SEGMENT_CHARS = 20


def get_tts_semaphore() -> asyncio.Semaphore:
    """Get or create the TTS semaphore (lazy initialization)."""
    global _tts_semaphore
    if _tts_semaphore is None:
        # Allow 2 concurrent TTS operations (balances latency vs resource usage)
        _tts_semaphore = asyncio.Semaphore(2)
    return _tts_semaphore


def get_tts_executor() -> ThreadPoolExecutor:
    """Get or create a dedicated thread pool for TTS."""
    global _tts_executor
    if _tts_executor is None:
        # Dedicated pool with 3 workers for TTS
        _tts_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="tts")
    return _tts_executor


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


def prewarm_voices(voices: Optional[Set[str]] = None) -> int:
    """
    Pre-load voice models to eliminate first-use latency.

    Args:
        voices: Set of model names to load. Defaults to CORE_VOICES.

    Returns:
        Number of voices successfully loaded
    """
    global _prewarmed_voices
    voices = voices or CORE_VOICES
    loaded = 0

    for model_name in voices:
        if model_name in _prewarmed_voices:
            continue

        with _voice_lock:
            if model_name in _voice_models:
                _prewarmed_voices.add(model_name)
                continue

            try:
                from piper import PiperVoice

                model_path = VOICES_DIR / f"{model_name}.onnx"
                if model_path.exists():
                    start = time.perf_counter()
                    logger.info(f"Pre-warming voice: {model_name}")
                    voice = PiperVoice.load(str(model_path))
                    _voice_models[model_name] = voice
                    _prewarmed_voices.add(model_name)
                    duration_ms = (time.perf_counter() - start) * 1000
                    record_timing("tts.prewarm", duration_ms, voice=model_name)
                    loaded += 1
                else:
                    logger.warning(f"Voice model not found: {model_path}")
            except Exception as e:
                logger.warning(f"Failed to prewarm {model_name}: {e}")

    logger.info(f"Pre-warmed {loaded} voice models")
    return loaded


async def prewarm_voices_async(voices: Optional[Set[str]] = None) -> int:
    """Async wrapper for voice pre-warming."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, prewarm_voices, voices)


def get_voice(voice_name: str = "default"):
    """Get or load a Piper voice model (thread-safe)."""
    # Resolve voice profile to actual model name
    model_name = VOICE_PROFILES.get(voice_name, VOICE_PROFILES["default"])

    # Fast path: check cache without lock
    if model_name in _voice_models:
        return _voice_models[model_name]

    # Slow path: acquire lock and load
    with _voice_lock:
        # Double-check after acquiring lock
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

            start = time.perf_counter()
            logger.info(f"Loading Piper voice: {model_path.stem}")
            voice = PiperVoice.load(str(model_path))
            _voice_models[model_name] = voice
            duration_ms = (time.perf_counter() - start) * 1000
            record_timing("tts.load_voice", duration_ms, voice=model_name)
            return voice

        except ImportError:
            logger.warning("piper-tts not installed. Run: pip install piper-tts")
            return None
        except Exception as e:
            logger.error(f"Failed to load voice model: {e}")
            return None


def synthesize_sync(text: str, voice_name: str = "default", add_pause: bool = True) -> Optional[bytes]:
    """
    Synthesize text to speech (synchronous).

    Args:
        text: Text to synthesize
        voice_name: Voice profile name (default, dm, elderly_male, etc.)
        add_pause: Add dramatic pause at end of sentences (default True)

    Returns:
        WAV audio bytes or None if failed
    """
    if not text or not text.strip():
        return None

    start_time = time.perf_counter()

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

            # Add brief pause at end (150ms for natural speech rhythm)
            if add_pause:
                pause_samples = int(voice.config.sample_rate * 0.15)  # 150ms pause
                silence = b'\x00\x00' * pause_samples  # 16-bit silence
                wav_file.writeframes(silence)

        audio_buffer.seek(0)
        result = audio_buffer.read()

        # Record timing
        duration_ms = (time.perf_counter() - start_time) * 1000
        record_timing("tts.synthesize", duration_ms, chars=len(text), voice=voice_name)

        return result

    except Exception as e:
        logger.error(f"TTS synthesis error: {e}")
        return None


async def synthesize(text: str, voice_name: str = "default") -> Optional[bytes]:
    """
    Synthesize text to speech (async wrapper with concurrency control).

    Args:
        text: Text to synthesize
        voice_name: Voice profile name

    Returns:
        WAV audio bytes or None if failed
    """
    semaphore = get_tts_semaphore()

    async with semaphore:
        loop = asyncio.get_event_loop()
        executor = get_tts_executor()
        return await loop.run_in_executor(executor, synthesize_sync, text, voice_name)


def coalesce_segments(segments: list[tuple[str, str]], min_chars: int = MIN_SEGMENT_CHARS) -> list[tuple[str, str]]:
    """
    Combine short segments with the same voice to reduce TTS calls.

    Args:
        segments: List of (voice_name, text) tuples
        min_chars: Minimum character count before emitting a segment

    Returns:
        Coalesced segments
    """
    if not segments:
        return segments

    result = []
    current_voice = None
    current_text = ""

    for voice, text in segments:
        text = text.strip()
        if not text:
            continue

        if voice == current_voice:
            # Same voice: accumulate
            current_text += " " + text
        else:
            # Voice change: emit current if long enough
            if current_text and len(current_text) >= min_chars:
                result.append((current_voice, current_text.strip()))
            elif current_text and result:
                # Too short but we have previous segments - append to last if same voice
                if result[-1][0] == current_voice:
                    prev_voice, prev_text = result[-1]
                    result[-1] = (prev_voice, prev_text + " " + current_text.strip())
                else:
                    # Different voice, emit anyway
                    result.append((current_voice, current_text.strip()))
            elif current_text:
                result.append((current_voice, current_text.strip()))

            current_voice = voice
            current_text = text

    # Emit final segment
    if current_text:
        result.append((current_voice, current_text.strip()))

    return result


def extract_voice_segments(text: str, narrator_voice: str = "dm") -> list[tuple[str, str]]:
    """
    Extract voice-tagged segments from text.

    Parses text with various voice tag formats and returns segments with their voice.
    Handles [VOICE:name], [DM], [Cheerful Voice], etc.

    Args:
        text: Text potentially containing voice tags
        narrator_voice: Voice to use for narrator/DM segments (dm_male or dm_female)

    Returns:
        List of (voice_name, text_segment) tuples
    """
    import re

    # Map various tag names to actual voice IDs
    VOICE_ALIASES = {
        # Direct mappings
        "dm": "dm_male",
        "narrator": "dm_male",
        "gm": "dm_male",
        "npc": "dm_male",
        # Character types
        "elderly_male": "elderly_male",
        "elderly": "elderly_male",
        "old_man": "elderly_male",
        "wizard": "elderly_male",
        "sage": "elderly_male",
        "gruff": "gruff",
        "dwarf": "gruff",
        "guard": "gruff",
        "young_female": "young_female",
        "barmaid": "young_female",
        "young_woman": "young_female",
        "menacing": "menacing",
        "villain": "menacing",
        "monster": "menacing",
        "evil": "menacing",
        "cheerful": "cheerful",
        "friendly": "cheerful",
        "happy": "cheerful",
        # Fallbacks
        "male": "dm_male",
        "female": "dm_female",
    }

    def normalize_voice(tag_content: str) -> str:
        """Convert a tag like 'Cheerful Voice' or 'elderly_male' to a voice ID."""
        # Remove 'voice' suffix and normalize
        normalized = tag_content.lower().replace(" voice", "").replace("voice", "").strip()
        normalized = normalized.replace(" ", "_")
        return VOICE_ALIASES.get(normalized, narrator_voice)

    segments = []
    current_voice = narrator_voice

    # Pattern to match various voice tag formats:
    # [VOICE:name], [VOICE: name], [DM], [Cheerful Voice], [Old Man], etc.
    pattern = r'\[(?:VOICE:\s*)?([^\]]+)\]'

    # Find all tags and their positions
    last_end = 0
    for match in re.finditer(pattern, text):
        # Add text before this tag with current voice
        before_text = text[last_end:match.start()].strip()
        if before_text:
            segments.append((current_voice, before_text))

        # Update voice based on tag content
        tag_content = match.group(1).strip()
        current_voice = normalize_voice(tag_content)
        last_end = match.end()

    # Add remaining text after last tag
    remaining = text[last_end:].strip()
    if remaining:
        segments.append((current_voice, remaining))

    # If no segments found, return the whole text with narrator voice
    if not segments and text.strip():
        # Strip any tags that might have been missed
        clean_text = strip_voice_tags(text).strip()
        if clean_text:
            segments = [(narrator_voice, clean_text)]

    return segments


def strip_voice_tags(text: str) -> str:
    """
    Remove voice/speaker tags from text for display.

    Handles multiple formats the LLM might generate:
    - [VOICE:name] - intended format
    - [DM], [NPC] - simple labels
    - [Cheerful Voice], [Old Man] - multi-word labels
    - [VOICE: name] - with space after colon

    Args:
        text: Text potentially containing voice tags

    Returns:
        Text with voice tags removed
    """
    import re
    # Match various bracket tag formats:
    # [VOICE:word], [VOICE: word], [Word], [Multiple Words], [DM], etc.
    # But NOT [action descriptions in lowercase]
    patterns = [
        r'\[VOICE:\s*\w+\]\s*',           # [VOICE:name] or [VOICE: name]
        r'\[(?:DM|NPC|GM|NARRATOR)\]\s*',  # [DM], [NPC], [GM], [NARRATOR]
        r'\[[A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*\s*(?:Voice|voice)?\]\s*',  # [Cheerful Voice], [Old Man], etc.
    ]
    result = text
    for pattern in patterns:
        result = re.sub(pattern, '', result)
    return result


def split_into_sentences(text: str) -> list[str]:
    """
    Split text into sentences for streaming TTS.

    Args:
        text: Input text

    Returns:
        List of sentences
    """
    # Simple split on sentence-ending punctuation
    sentences = []
    current = ""

    for char in text:
        current += char
        if char in '.!?' and len(current.strip()) > 1:
            # Check if this looks like end of sentence (followed by space or end)
            sentences.append(current.strip())
            current = ""

    # Add any remaining text
    if current.strip():
        sentences.append(current.strip())

    return sentences


async def synthesize_with_voices(text: str) -> list[tuple[str, bytes]]:
    """
    Synthesize text that may contain multiple voice segments.

    Args:
        text: Text potentially containing [VOICE:name] tags

    Returns:
        List of (voice_name, audio_bytes) tuples
    """
    segments = extract_voice_segments(text)
    segments = coalesce_segments(segments)  # Combine short segments
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
