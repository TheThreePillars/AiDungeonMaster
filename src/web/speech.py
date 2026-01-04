"""Speech-to-text service using faster-whisper."""

import io
import logging
import tempfile
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy load whisper model
_whisper_model = None


def get_whisper_model():
    """Get or create the Whisper model (lazy loading)."""
    global _whisper_model

    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel

            # Use tiny model for speed - good enough for commands
            # Options: tiny, base, small, medium, large-v2
            logger.info("Loading Whisper model (tiny)...")
            _whisper_model = WhisperModel(
                "tiny",
                device="cpu",  # Use CPU for compatibility
                compute_type="int8",  # Quantized for speed
            )
            logger.info("Whisper model loaded successfully")
        except ImportError:
            logger.warning(
                "faster-whisper not installed. "
                "Run: pip install faster-whisper"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            return None

    return _whisper_model


def is_available() -> bool:
    """Check if speech-to-text is available."""
    try:
        from faster_whisper import WhisperModel
        return True
    except ImportError:
        return False


async def transcribe_audio(audio_data: bytes, format: str = "webm") -> Optional[str]:
    """
    Transcribe audio data to text.

    Args:
        audio_data: Raw audio bytes
        format: Audio format (webm, wav, mp3, etc.)

    Returns:
        Transcribed text or None if failed
    """
    model = get_whisper_model()
    if model is None:
        return None

    try:
        # Write audio to temp file (faster-whisper needs a file path)
        with tempfile.NamedTemporaryFile(
            suffix=f".{format}",
            delete=False
        ) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            # Transcribe with speed optimizations
            segments, info = model.transcribe(
                tmp_path,
                beam_size=1,  # Faster, slightly less accurate
                best_of=1,  # Only one candidate
                language="en",  # Force English for gaming
                vad_filter=True,  # Filter out silence
                without_timestamps=True,  # Skip timestamp computation
                condition_on_previous_text=False,  # Don't use context
                compression_ratio_threshold=None,  # Skip quality check
                log_prob_threshold=None,  # Skip quality check
                no_speech_threshold=None,  # Skip quality check
            )

            # Combine segments (convert generator to list for speed)
            text = " ".join(segment.text.strip() for segment in segments)

            logger.info(f"Transcribed: {text[:50]}..." if len(text) > 50 else f"Transcribed: {text}")
            return text.strip()

        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None
