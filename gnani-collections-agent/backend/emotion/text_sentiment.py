import re
import logging
from typing import Dict, Any, Optional
from backend.config import settings

logger = logging.getLogger("text_sentiment")

class CodeSwitchedTextSentiment:
    """
    Code-switched (Hinglish + Telugu/Hindi + Indian English) text sentiment analyzer.
    Combines high-speed specialized BFSI lexicon parsing with Gemini 2.5 Flash.
    """
    def __init__(self):
        self.gemini_client = None
        self._init_gemini_client()

        # Hinglish & English Lexicons
        self.frustrated_keywords = [
            "bakwaas", "dimag kharab", "harass", "dhamki", "stop calling", "police",
            "chor", "manager", "senior", "court", "complaint", "shame", "fucking",
            "gussa", "pareshan mat karo", "kitni baar", "band karo", "fraud", "badtameez"
        ]
        self.stressed_keywords = [
            "salary nahi aayi", "salary delay", "hospital", "emergency", "medical",
            "job chali gayi", "paise nahi hain", "mushkil", "majboori", "illness",
            "treatment", "crisis", "loan default", "gareeb", "accident"
        ]
        self.confused_keywords = [
            "kya matlab", "samajh nahi aaya", "itna kyun", "charges kyun", "hidden charge",
            "breakup do", "explain karo", "kaise ho gaya", "kaise", "what is this",
            "why so much", "confused", "galat lagaya"
        ]
        self.polite_agreement_keywords = [
            "haan haan bilkul", "haan haan", "bilkul", "sure", "fine whatever", "whatever",
            "kal pay kar dunga", "abhi kar deta hoon na", "no problem", "obviously", "of course"
        ]
        self.cooperative_keywords = [
            "payment link bhejo", "pay kar dunga", "link bhejo", "gpay", "upi",
            "ready to pay", "half pay kar sakta hoon", "split kar do", "i will pay",
            "clearing today", "theek hai", "accha theek hai"
        ]

    def _init_gemini_client(self):
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as err:
                logger.warning(f"Could not init Gemini client in text sentiment: {err}")

    async def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyzes code-switched text.
        Returns:
            {
               "text_emotion": "frustrated | stressed | confused | cooperative | neutral",
               "text_confidence": 0.85,
               "surface_politeness": bool,
               "apparent_agreement": bool
            }
        """
        if not text or not text.strip():
            return {
                "text_emotion": "neutral",
                "text_confidence": 0.5,
                "surface_politeness": False,
                "apparent_agreement": False
            }

        cleaned = text.lower()

        # Fast Rule-based analysis
        has_polite_agree = any(kw in cleaned for kw in self.polite_agreement_keywords)
        has_frustration = any(kw in cleaned for kw in self.frustrated_keywords)
        has_stress = any(kw in cleaned for kw in self.stressed_keywords)
        has_confusion = any(kw in cleaned for kw in self.confused_keywords)
        has_cooperative = any(kw in cleaned for kw in self.cooperative_keywords)

        if has_frustration:
            emotion = "frustrated"
            conf = 0.90
        elif has_stress:
            emotion = "stressed"
            conf = 0.88
        elif has_confusion:
            emotion = "confused"
            conf = 0.85
        elif has_cooperative or (has_polite_agree and not has_frustration):
            emotion = "cooperative"
            conf = 0.82
        else:
            emotion = "neutral"
            conf = 0.60

        return {
            "text_emotion": emotion,
            "text_confidence": conf,
            "surface_politeness": has_polite_agree or "please" in cleaned or "thank" in cleaned,
            "apparent_agreement": has_polite_agree or has_cooperative
        }
