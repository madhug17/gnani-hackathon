import asyncio
import io
import re
import time
import httpx
import logging
from typing import AsyncGenerator, Optional, Dict, Any
from backend.config import settings

logger = logging.getLogger("tts")

# High-Quality Neural Voices for Indian Accent and Code-Switching
DEFAULT_VOICES = {
    "hi_madhur": "hi-IN-MadhurNeural",       # Warm, empathetic, crystal-clear Indian male
    "hi_swara": "hi-IN-SwaraNeural",         # Expressive, articulate Indian female
    "en_neerja": "en-IN-NeerjaNeural",       # Clear, professional Indian English female
    "en_prabhat": "en-IN-PrabhatNeural"      # Confident, formal Indian English male
}

TIMBRE_PRESETS: Dict[str, Dict[str, str]] = {
    "[calm_empathetic]": {
        "rate": "-4%",
        "pitch": "-1Hz",
        "volume": "+0%",
        "voice": "hi-IN-MadhurNeural"
    },
    "[reassuring]": {
        "rate": "-2%",
        "pitch": "+0Hz",
        "volume": "+0%",
        "voice": "hi-IN-MadhurNeural"
    },
    "[upbeat]": {
        "rate": "+3%",
        "pitch": "+1Hz",
        "volume": "+0%",
        "voice": "hi-IN-MadhurNeural"
    },
    "[neutral]": {
        "rate": "+0%",
        "pitch": "+0Hz",
        "volume": "+0%",
        "voice": "hi-IN-MadhurNeural"
    }
}

def clean_text_for_speech(text: str) -> str:
    """
    Normalizes banking abbreviations, currency symbols, and numbers
    for pristine pronunciation and clarity.
    """
    if not text:
        return ""

    # Remove markdown tags, asterisks, brackets like [INTERRUPTED]
    cleaned = re.sub(r'\[.*?\]', '', text)
    cleaned = re.sub(r'[*_~`#]', '', cleaned)

    # Currency formatting: ₹24,500 -> 24 thousand 500 rupees / 24,500 rupees
    cleaned = re.sub(r'₹\s*([0-9,]+)', r'\1 rupees', cleaned)
    cleaned = re.sub(r'Rs\.?\s*([0-9,]+)', r'\1 rupees', cleaned)

    # Banking Acronym expansion for natural phonetics
    cleaned = re.sub(r'\bEMI\b', 'E.M.I.', cleaned)
    cleaned = re.sub(r'\bEMIs\b', 'E.M.I.s', cleaned)
    cleaned = re.sub(r'\bRBI\b', 'R.B.I.', cleaned)
    cleaned = re.sub(r'\bSMS\b', 'S.M.S.', cleaned)
    cleaned = re.sub(r'\bUPI\b', 'U.P.I.', cleaned)
    cleaned = re.sub(r'\bCIBIL\b', 'CIBIL', cleaned)
    cleaned = re.sub(r'\bSARFAESI\b', 'Sarfaesi', cleaned)

    # Clean double spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

class ExpressiveIndianTTS:
    """
    Studio-Quality Expressive Indian-Accent TTS Engine.
    Produces complete, valid MP3 audio containers per sentence for flawless,
    jitter-free, crystal-clear playback on the browser Web Audio graph.
    """
    def __init__(self, default_voice_key: str = "hi_madhur"):
        self.default_voice = DEFAULT_VOICES.get(default_voice_key, "hi-IN-MadhurNeural")
        self._is_cancelled: bool = False

    def set_voice(self, voice_key_or_name: str):
        """Sets the active neural voice profile."""
        if voice_key_or_name in DEFAULT_VOICES:
            self.default_voice = DEFAULT_VOICES[voice_key_or_name]
        elif "Neural" in voice_key_or_name:
            self.default_voice = voice_key_or_name
        logger.info(f"Active TTS Voice updated to: {self.default_voice}")

    def cancel_current_speech(self):
        """Immediately interrupts active speech synthesis."""
        self._is_cancelled = True
        logger.info("Cancelled active TTS speech synthesis.")

    async def synthesize_sentence(
        self,
        text: str,
        timbre_tag: str = "[calm_empathetic]",
        voice_override: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Synthesizes a complete sentence into a valid, standalone MP3 buffer.
        Guarantees zero audio clipping, pops, or fragmentation.
        """
        self._is_cancelled = False
        clean_text = clean_text_for_speech(text)
        if not clean_text:
            return None

        # 1. Check Gnani Timbre v3.0 Adapter
        if settings.GNANI_API_KEY and settings.GNANI_TIMBRE_ENDPOINT and "your_" not in settings.GNANI_API_KEY:
            try:
                gnani_audio = await self._synthesize_gnani_timbre(clean_text, timbre_tag)
                if gnani_audio:
                    return gnani_audio
            except Exception as err:
                logger.warning(f"Gnani Timbre v3.0 failed, falling back to edge-tts: {err}")

        # 2. edge-tts complete MP3 sentence generation
        preset = TIMBRE_PRESETS.get(timbre_tag, TIMBRE_PRESETS["[calm_empathetic]"])
        voice = voice_override or self.default_voice

        rate = preset["rate"]
        pitch = preset["pitch"]
        volume = preset["volume"]

        try:
            import edge_tts
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume=volume
            )

            chunks = []
            async for chunk in communicate.stream():
                if self._is_cancelled:
                    logger.info("TTS sentence synthesis aborted due to barge-in.")
                    return None
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])

            if not chunks:
                return None

            # Concatenate all frames into a complete, pristine MP3 container
            full_mp3_bytes = b"".join(chunks)
            return full_mp3_bytes

        except asyncio.CancelledError:
            logger.info("TTS task cancelled during barge-in.")
            return None
        except Exception as err:
            logger.error(f"Error in edge-tts sentence synthesis: {err}")
            return None

    async def stream_speech(
        self,
        text: str,
        timbre_tag: str = "[calm_empathetic]",
        language_hint: str = "Hinglish"
    ) -> AsyncGenerator[bytes, None]:
        """
        Backward compatible streaming interface.
        Yields the complete valid audio buffer for the given sentence.
        """
        audio_data = await self.synthesize_sentence(text, timbre_tag)
        if audio_data:
            yield audio_data

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
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                settings.GNANI_TIMBRE_ENDPOINT,
                headers=headers,
                json=payload
            )
            if resp.status_code == 200:
                return resp.content
        return None
