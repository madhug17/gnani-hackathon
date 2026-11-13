import math
import time
import numpy as np
from typing import Optional, Callable, Awaitable
import logging

logger = logging.getLogger("vad")

class ContinuousSileroVAD:
    """
    Sub-300ms Continuous Voice Activity Detector using Silero VAD 
    with ONNX/PyTorch backend and adaptive energy fallback.
    """
    def __init__(self, sample_rate: int = 16000, threshold: float = 0.55):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.model = None
        self.is_onnx = False
        self.consecutive_speech_frames = 0
        self.min_speech_frames = 2  # 2 frames * 32ms ~ 64ms trigger latency
        self._init_silero()

    def _init_silero(self):
        # 1. Try silero_vad package
        try:
            from silero_vad import load_silero_vad
            self.model = load_silero_vad(onnx=True)
            self.is_onnx = True
            logger.info("Loaded Silero VAD via silero_vad ONNX.")
            return
        except Exception:
            pass

        # 2. Try torch.hub silero_vad
        try:
            import torch
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=True
            )
            self.model = model
            self.is_onnx = True
            logger.info("Loaded Silero VAD via torch.hub ONNX.")
            return
        except Exception:
            pass

        # 3. Fallback to adaptive energy + zero-crossing VAD
        logger.info("Initialized high-speed adaptive Energy/ZCR VAD fallback.")
        self.energy_noise_floor = 0.015

    def is_speech_frame(self, pcm_bytes: bytes) -> tuple[bool, float]:
        """
        Evaluates a 16kHz 16-bit mono PCM frame (e.g. 512 samples = 32ms).
        Returns (is_speech, probability).
        """
        if not pcm_bytes:
            return False, 0.0

        audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        if len(audio_int16) == 0:
            return False, 0.0

        # Convert to float32 in [-1.0, 1.0]
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        # Try ML inference if model is available
        if self.model is not None:
            try:
                import torch
                # Ensure tensor length is valid for Silero (minimum 512 samples)
                if len(audio_float32) < 512:
                    audio_float32 = np.pad(audio_float32, (0, 512 - len(audio_float32)))
                tensor = torch.from_numpy(audio_float32[:512]).float()
                prob = float(self.model(tensor, self.sample_rate).item())
                return prob >= self.threshold, prob
            except Exception as err:
                logger.debug(f"Silero inference error, falling back to energy: {err}")

        # High-performance acoustic energy & zero-crossing fallback
        # Sub-millisecond compute overhead
        rms = float(np.sqrt(np.mean(audio_float32 ** 2)))
        zcr = float(np.mean(np.abs(np.diff(np.sign(audio_float32)))) / 2.0)
        
        # Adaptive noise floor tracking
        if rms < self.energy_noise_floor * 1.2:
            self.energy_noise_floor = 0.95 * self.energy_noise_floor + 0.05 * rms

        # Speech criteria: substantial energy over noise floor with normal vocal ZCR range
        snr_ratio = rms / max(self.energy_noise_floor, 1e-4)
        prob = min(1.0, max(0.0, (snr_ratio - 1.5) / 5.0))
        
        is_speech = prob >= self.threshold and (0.02 <= zcr <= 0.65)
        return is_speech, prob


class BargeInDetector:
    """
    Sub-300ms Barge-In Detector.
    Monitors incoming audio continuously during bot speech playback.
    Immediately dispatches cancellation on user vocalization.
    """
    def __init__(self, vad: ContinuousSileroVAD, on_barge_in_cb: Callable[[float], Awaitable[None]]):
        self.vad = vad
        self.on_barge_in_cb = on_barge_in_cb
        self.bot_speaking = False
        self.speech_start_time: Optional[float] = None
        self.consecutive_speech = 0
        self.min_consecutive_frames = 2  # ~60ms validation window

    def set_bot_speaking(self, speaking: bool):
        self.bot_speaking = speaking
        if not speaking:
            self.consecutive_speech = 0
            self.speech_start_time = None

    async def process_frame(self, pcm_bytes: bytes) -> tuple[bool, Optional[float]]:
        """
        Processes an incoming mic PCM frame.
        If bot is speaking and user begins talking, triggers barge-in callback.
        Returns (barge_in_triggered, barge_in_latency_ms).
        """
        is_speech, prob = self.vad.is_speech_frame(pcm_bytes)
        now = time.perf_counter()

        if is_speech:
            if self.consecutive_speech == 0:
                self.speech_start_time = now
            self.consecutive_speech += 1

            if self.consecutive_speech >= self.min_consecutive_frames:
                # User is speaking!
                if self.bot_speaking:
                    # BARGE-IN DETECTED!
                    trigger_stamp = self.speech_start_time or now
                    self.bot_speaking = False  # immediately suppress further triggers
                    self.consecutive_speech = 0
                    
                    # Execute instant cancellation callback
                    await self.on_barge_in_cb(trigger_stamp)
                    latency_ms = (time.perf_counter() - trigger_stamp) * 1000.0
                    return True, latency_ms
        else:
            self.consecutive_speech = max(0, self.consecutive_speech - 1)
            if self.consecutive_speech == 0:
                self.speech_start_time = None

        return False, None

