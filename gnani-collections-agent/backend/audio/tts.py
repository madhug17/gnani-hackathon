import asyncio
import io
import time
import httpx
import logging
from typing import AsyncGenerator, Optional, Dict, Any
from backend.config import settings

logger = logging.getLogger("tts")

# Voice profiles
VOICE_EN_IN = "en-IN-NeerjaExpressiveNeural"
VOICE_HI_IN = "hi-IN-SwaraNeural"

TIMBRE_PRESETS: Dict[str, Dict[str, str]] = {
    "[calm_empathetic]": {
        "rate": "-12%",
        "pitch": "-4Hz",
        "volume": "+0%",
        "voice": VOICE_EN_IN
    },
    "[reassuring]": {
        "rate": "-6%",
        "pitch": "-2Hz",
        "volume": "+0%",
        "voice": VOICE_EN_IN
    },
    "[upbeat]": {
        "rate": "+5%",
        "pitch": "+3Hz",
        "volume": "+5%",
        "voice": VOICE_EN_IN
    },
    "[neutral]": {
        "rate": "+0%",
        "pitch": "+0Hz",
        "volume": "+0%",
        "voice": VOICE_EN_IN
    }
}

class ExpressiveIndianTTS:
    """
    Expressive Indian-accent TTS Engine.
    Uses edge-tts with dynamic pitch/rate modification per timbre_tag.
    Includes Gnani Timbre v3.0 adapter and instant asyncio Task cancellation.
    """
    def __init__(self):
        self._current_task: Optional[asyncio.Task] = None
        self._is_cancelled: bool = False

    def cancel_current_speech(self):
        """Immediately interrupts and cancels active speech synthesis."""
        self._is_cancelled = True
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            logger.info("Cancelled active TTS speech synthesis task.")

    async def stream_speech(
        self,
        text: str,
        timbre_tag: str = "[calm_empathetic]",
        language_hint: str = "Hinglish"
    ) -> AsyncGenerator[bytes, None]:
        """
        Streams audio chunks (MP3 format) for the given text snippet.
        Stops immediately if cancel_current_speech() is triggered.
        """
        self._is_cancelled = False
        if not text or not text.strip():
            return

        # 1. Check Gnani Timbre v3.0 Adapter
        if settings.GNANI_API_KEY and settings.GNANI_TIMBRE_ENDPOINT and "your_" not in settings.GNANI_API_KEY:
            try:
                gnani_audio = await self._synthesize_gnani_timbre(text, timbre_tag)
                if gnani_audio:
                    yield gnani_audio
                    return
            except Exception as err:
                logger.warning(f"Gnani Timbre v3.0 failed, falling back to edge-tts: {err}")

        # 2. edge-tts streaming with dynamic prosody presets
        preset = TIMBRE_PRESETS.get(timbre_tag, TIMBRE_PRESETS["[calm_empathetic]"])
        
        # Select voice based on language and code-mixing
        voice = preset["voice"]
        if language_hint.lower() == "hindi" or any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in text):
            voice = VOICE_HI_IN

        rate = preset["rate"]
        pitch = preset["pitch"]
        volume = preset["volume"]

        try:
            import edge_tts
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume=volume
            )

            async for chunk in communicate.stream():
                if self._is_cancelled:
                    logger.info("TTS stream aborted due to barge-in.")
                    break
                if chunk["type"] == "audio":
                    yield chunk["data"]

        except asyncio.CancelledError:
            logger.info("TTS stream task cancelled during barge-in.")
            raise
        except Exception as err:
            logger.error(f"Error in edge-tts stream: {err}")
            # Generate minimal synthetic chime or beep fallback if needed
            yield b""

    async def _synthesize_gnani_timbre(self, text: str, timbre_tag: str) -> Optional[bytes]:
        """Gnani Timbre v3.0 Enterprise TTS Adapter."""
        headers = {
            "Authorization": f"Bearer {settings.GNANI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "timbre": timbre_tag.replace("[", "").replace("]", ""),
            "language": "hin-eng",
            "audio_format": "mp3"
        }
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                settings.GNANI_TIMBRE_ENDPOINT,
                headers=headers,
                json=payload
            )
            if resp.status_code == 200:
                return resp.content
        return None
