import logging
from typing import Dict, Any, Optional
from backend.emotion.voice_emotion import VoiceEmotionClassifier
from backend.emotion.text_sentiment import CodeSwitchedTextSentiment

logger = logging.getLogger("emotion_fusion")

class MultimodalEmotionFusion:
    """
    Multimodal Dual-Stream Fusion Engine.
    Fuses real-time acoustic prosody/energy with code-switched text sentiment
    to detect covert frustration, stress, and sarcasm.
    """
    def __init__(self):
        self.voice_classifier = VoiceEmotionClassifier()
        self.text_analyzer = CodeSwitchedTextSentiment()

    async def fuse(
        self,
        pcm_bytes: bytes,
        transcript_text: str,
        interrupted: bool = False,
        simulated_acoustic: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes dual-stream acoustic + text fusion.
        """
        # 1. Acoustic stream analysis (or simulated profile if demo)
        if simulated_acoustic:
            acoustic_data = {
                "acoustic_emotion": simulated_acoustic.get("acoustic_emotion", "frustrated"),
                "confidence": simulated_acoustic.get("acoustic_confidence", 0.88),
                "pitch_variance": simulated_acoustic.get("pitch_variance", 70.0),
                "energy_db": simulated_acoustic.get("energy_db", -12.0),
                "speech_rate": simulated_acoustic.get("speech_rate", "fast")
            }
        else:
            acoustic_data = self.voice_classifier.analyze_audio(pcm_bytes)

        # 2. Text sentiment stream analysis
        text_data = await self.text_analyzer.analyze(transcript_text)

        ac_emotion = acoustic_data.get("acoustic_emotion", "neutral")
        ac_conf = acoustic_data.get("confidence", 0.5)
        speech_rate = acoustic_data.get("speech_rate", "normal")

        txt_emotion = text_data.get("text_emotion", "neutral")
        txt_conf = text_data.get("text_confidence", 0.5)
        surface_polite = text_data.get("surface_politeness", False)
        apparent_agree = text_data.get("apparent_agreement", False)

        # 3. Multimodal Sarcasm Rule
        # If acoustic emotion is angry/frustrated (conf > 0.70) while transcript words appear polite/agreeable:
        sarcasm_detected = False
        final_emotion = ac_emotion
        final_conf = ac_conf

        if ac_emotion in ["frustrated", "stressed"] and ac_conf >= 0.70 and (surface_polite or apparent_agree):
            sarcasm_detected = True
            final_emotion = "frustrated"
            final_conf = max(ac_conf, 0.91)
            logger.info("MULTIMODAL SARCASM DETECTED: Acoustic irritation overrides polite lexical agreement.")
        elif interrupted and ac_emotion != "frustrated":
            # An abrupt interruption often indicates urgent stress or rising agitation
            final_emotion = "stressed" if ac_emotion != "frustrated" else "frustrated"
            final_conf = max(final_conf, 0.85)
        elif ac_emotion == "neutral" and txt_emotion != "neutral":
            # Text carries stronger explicit sentiment
            final_emotion = txt_emotion
            final_conf = (ac_conf + txt_conf) / 2.0
        elif ac_emotion == txt_emotion:
            final_emotion = ac_emotion
            final_conf = min(0.99, max(ac_conf, txt_conf) + 0.05)
        else:
            # Weighted blending: acoustic weight 0.6, lexical weight 0.4
            final_emotion = ac_emotion if ac_conf >= txt_conf else txt_emotion
            final_conf = round(float(ac_conf * 0.6 + txt_conf * 0.4), 2)

        # 4. Dynamic Timbre Tag Selection
        timbre_tag = self._select_timbre_tag(final_emotion, sarcasm_detected)

        return {
            "emotion": final_emotion,
            "confidence": round(float(final_conf), 2),
            "interrupted": interrupted,
            "speech_rate": speech_rate,
            "sarcasm_detected": sarcasm_detected,
            "timbre_tag": timbre_tag,
            "acoustic_breakdown": {
                "pitch_variance": acoustic_data.get("pitch_variance"),
                "energy_db": acoustic_data.get("energy_db"),
                "raw_acoustic_emotion": ac_emotion
            },
            "text_breakdown": {
                "surface_polite": surface_polite,
                "raw_text_emotion": txt_emotion
            }
        }

    def _select_timbre_tag(self, emotion: str, sarcasm_detected: bool) -> str:
        if sarcasm_detected or emotion == "frustrated":
            return "[calm_empathetic]"
        elif emotion == "stressed":
            return "[reassuring]"
        elif emotion == "confused":
            return "[calm_empathetic]"
        elif emotion == "cooperative":
            return "[upbeat]"
        return "[neutral]"

