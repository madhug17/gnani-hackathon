import numpy as np
import scipy.signal
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("voice_emotion")

class VoiceEmotionClassifier:
    """
    Acoustic prosody, pitch, and energy emotion classifier 
    operating on 2-3 second rolling audio windows.
    Zero external heavy model dependencies; ultra-fast <5ms execution.
    """
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def analyze_audio(self, pcm_bytes: bytes) -> Dict[str, Any]:
        """
        Analyzes audio buffer and returns acoustic prosodic features + predicted emotion.
        """
        if not pcm_bytes or len(pcm_bytes) < 1600:  # < 50ms
            return {
                "acoustic_emotion": "neutral",
                "confidence": 0.5,
                "pitch_mean_hz": 160.0,
                "pitch_variance": 10.0,
                "energy_db": -25.0,
                "speech_rate": "normal"
            }

        audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        samples = audio_int16.astype(np.float32) / 32768.0

        # 1. Energy Calculation (RMS in dB)
        rms = float(np.sqrt(np.mean(samples ** 2)))
        energy_db = float(20 * np.log10(max(rms, 1e-6)))

        # 2. Zero Crossing Rate (ZCR)
        zcr = float(np.mean(np.abs(np.diff(np.sign(samples)))) / 2.0)

        # 3. Fast Pitch (F0) estimation via Autocorrelation
        pitch_mean_hz, pitch_variance = self._estimate_pitch_and_variance(samples)

        # 4. Speech rate / Energy fluctuations (syllabic envelope)
        speech_rate = self._estimate_speech_rate(samples)

        # 5. Acoustic Emotion Heuristics
        # High pitch variance + loud energy + high ZCR = Frustration / Agitation
        if (pitch_variance > 50.0 or energy_db > -14.0) and (zcr > 0.08 or pitch_mean_hz > 230.0):
            emotion = "frustrated"
            conf = min(0.98, 0.70 + (pitch_variance / 200.0) + (max(0.0, energy_db + 15) / 50.0))
        # High pitch mean, moderate variance, fast rate = Stressed / Anxious
        elif pitch_mean_hz > 210.0 or (energy_db > -18.0 and speech_rate == "fast"):
            emotion = "stressed"
            conf = 0.82
        # Moderate energy, falling or hesitant intonation, slow rate = Confused
        elif speech_rate == "slow" and pitch_variance > 25.0:
            emotion = "confused"
            conf = 0.78
        # Gentle energy (-28 to -18 dB), low pitch variance (< 20Hz), steady rate = Cooperative
        elif -28.0 <= energy_db <= -16.0 and pitch_variance < 22.0:
            emotion = "cooperative"
            conf = 0.85
        else:
            emotion = "neutral"
            conf = 0.70

        return {
            "acoustic_emotion": emotion,
            "confidence": round(float(conf), 2),
            "pitch_mean_hz": round(float(pitch_mean_hz), 1),
            "pitch_variance": round(float(pitch_variance), 1),
            "energy_db": round(float(energy_db), 1),
            "speech_rate": speech_rate,
            "zcr": round(float(zcr), 3)
        }

    def _estimate_pitch_and_variance(self, samples: np.ndarray) -> tuple[float, float]:
        """Estimates fundamental frequency (F0) and pitch variance using windowed autocorrelation."""
        frame_len = int(self.sample_rate * 0.05)  # 50ms frames
        hop_len = int(frame_len / 2)
        pitches = []

        min_lag = int(self.sample_rate / 350)  # max ~350Hz
        max_lag = int(self.sample_rate / 80)   # min ~80Hz

        for i in range(0, len(samples) - frame_len, hop_len):
            frame = samples[i:i + frame_len]
            # Windowing
            windowed = frame * np.hanning(len(frame))
            # Autocorrelation
            corr = scipy.signal.correlate(windowed, windowed, mode='full')
            corr = corr[len(corr)//2:]
            
            if len(corr) > max_lag:
                segment = corr[min_lag:max_lag]
                if len(segment) > 0:
                    peak_idx = int(np.argmax(segment)) + min_lag
                    if corr[peak_idx] > 0.25 * corr[0]:
                        f0 = float(self.sample_rate / peak_idx)
                        pitches.append(f0)

        if not pitches:
            return 165.0, 12.0
            
        mean_f0 = float(np.mean(pitches))
        var_f0 = float(np.std(pitches))
        return mean_f0, var_f0

    def _estimate_speech_rate(self, samples: np.ndarray) -> str:
        """Estimates speech cadence by counting energy peaks per second."""
        duration_sec = len(samples) / float(self.sample_rate)
        if duration_sec < 0.5:
            return "normal"

        # Syllabic envelope via absolute smoothed amplitude
        rectified = np.abs(samples)
        b, a = scipy.signal.butter(2, 5.0 / (self.sample_rate / 2), btype='low')
        envelope = scipy.signal.filtfilt(b, a, rectified)

        # Count peaks in envelope
        threshold = np.mean(envelope) * 1.3
        peaks, _ = scipy.signal.find_peaks(envelope, height=threshold, distance=int(self.sample_rate * 0.12))
        syllables_per_sec = len(peaks) / max(0.5, duration_sec)

        if syllables_per_sec > 4.5:
            return "fast"
        elif syllables_per_sec < 2.2:
            return "slow"
        return "normal"
