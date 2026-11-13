import asyncio
import re
import json
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from backend.config import settings
from backend.brain.prompts import build_negotiation_prompt
from backend.brain.tools import (
    BFSI_TOOL_DEFINITIONS,
    get_borrower_details,
    offer_split_emi_plan,
    apply_late_fee_waiver
)

logger = logging.getLogger("negotiation_agent")

class GeminiBFSIgent:
    """
    Streaming Gemini 2.5 Flash Negotiator for Code-Switched BFSI Collections.
    Integrates live function calling, emotional prosody adaptation, and sentence chunk streaming.
    """
    def __init__(self):
        self.gemini_client = None
        self._init_client()

    def _init_client(self):
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info("Initialized Gemini 2.5 Flash Client in BFSI Agent.")
            except Exception as err:
                logger.warning(f"Could not initialize Gemini Client: {err}")

    async def generate_response_stream(
        self,
        conversation_history: List[Dict[str, str]],
        borrower_profile: Dict[str, Any],
        fused_emotion: Optional[Dict[str, Any]] = None,
        bot_mode: str = "empathetic",
        interrupted: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Yields sentence tokens/chunks and tool call events in real-time.
        Yields dict with:
          {"type": "sentence", "text": "...", "timbre_tag": "..."}
          {"type": "tool_call", "name": "...", "args": {...}, "result": {...}}
        """
        borrower_name = borrower_profile.get("name", "Rahul Sharma")
        overdue_amt = borrower_profile.get("overdue_amount", 24500.0)
        loan_type = borrower_profile.get("loan_type", "Personal Loan")
        borrower_id = borrower_profile.get("borrower_id", "LN-98231")

        system_instruction = build_negotiation_prompt(
            bot_mode=bot_mode,
            borrower_name=borrower_name,
            overdue_amount=overdue_amt,
            loan_type=loan_type,
            fused_emotion=fused_emotion if bot_mode == "empathetic" else None,
            interrupted=interrupted
        )

        timbre_tag = fused_emotion.get("timbre_tag", "[calm_empathetic]") if (fused_emotion and bot_mode == "empathetic") else "[neutral]"

        # Format message history for Gemini
        formatted_contents = []
        for turn in conversation_history[-8:]:
            role = "user" if turn.get("role") == "user" else "model"
            content = turn.get("content", "")
            formatted_contents.append({"role": role, "parts": [{"text": content}]})

        # Try live streaming with Gemini 2.5 Flash
        if self.gemini_client and "your_" not in settings.GEMINI_API_KEY:
            try:
                from google.genai import types

                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2,
                    max_output_tokens=200,
                    tools=BFSI_TOOL_DEFINITIONS if bot_mode == "empathetic" else None
                )

                response_stream = await self.gemini_client.aio.models.generate_content_stream(
                    model=settings.GEMINI_BRAIN_MODEL,
                    contents=formatted_contents,
                    config=config
                )

                sentence_buffer = ""
                delimiters = re.compile(r'([.?!।\n]+)')

                async for chunk in response_stream:
                    # Check for tool/function calls
                    if chunk.function_calls:
                        for fc in chunk.function_calls:
                            tool_name = fc.name
                            args = dict(fc.args) if fc.args else {}
                            tool_result = self._execute_local_tool(tool_name, args, borrower_id)
                            
                            yield {
                                "type": "tool_call",
                                "name": tool_name,
                                "args": args,
                                "result": tool_result
                            }

                    if chunk.text:
                        sentence_buffer += chunk.text
                        parts = delimiters.split(sentence_buffer)
                        
                        while len(parts) > 2:
                            sentence = (parts[0] + parts[1]).strip()
                            parts = parts[2:]
                            sentence_buffer = "".join(parts)
                            
                            if sentence:
                                yield {
                                    "type": "sentence",
                                    "text": sentence,
                                    "timbre_tag": timbre_tag
                                }

                # Flush any leftover sentence
                leftover = sentence_buffer.strip()
                if leftover:
                    yield {
                        "type": "sentence",
                        "text": leftover,
                        "timbre_tag": timbre_tag
                    }
                return

            except Exception as err:
                logger.warning(f"Gemini live stream error or rate-limit ({err}), engaging smart conversational fallback.")

        # Smart Code-Switched Conversational Fallback
        async for item in self._smart_fallback_stream(
            borrower_profile,
            fused_emotion,
            bot_mode,
            interrupted,
            timbre_tag
        ):
            yield item

    def _execute_local_tool(self, tool_name: str, args: Dict[str, Any], default_borrower_id: str) -> Dict[str, Any]:
        """Executes the Python tool call safely."""
        borrower_id = args.get("borrower_id") or default_borrower_id
        if tool_name == "get_borrower_details":
            return get_borrower_details(borrower_id)
        elif tool_name == "offer_split_emi_plan":
            installments = int(args.get("split_installments", 2))
            return offer_split_emi_plan(borrower_id, installments)
        elif tool_name == "apply_late_fee_waiver":
            waiver = int(args.get("waiver_percentage", 100))
            return apply_late_fee_waiver(borrower_id, waiver)
        return {"status": "error", "message": f"Unknown tool {tool_name}"}

    async def _smart_fallback_stream(
        self,
        borrower_profile: Dict[str, Any],
        fused_emotion: Optional[Dict[str, Any]],
        bot_mode: str,
        interrupted: bool,
        timbre_tag: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Provides instant, realistic code-switched streaming responses when offline."""
        borrower_name = borrower_profile.get("name", "Rahul Sharma")
        first_name = borrower_name.split()[0]
        overdue = borrower_profile.get("overdue_amount", 24500)
        borrower_id = borrower_profile.get("borrower_id", "LN-98231")

        if bot_mode == "normal":
            yield {
                "type": "sentence",
                "text": f"Namaste. Main recovery department se baat kar raha hoon. Aapka overdue amount ₹{overdue:,} aaj shaam 5 baje tak pay hona anivarya hai.",
                "timbre_tag": "[neutral]"
            }
            await asyncio.sleep(0.08)
            yield {
                "type": "sentence",
                "text": "Agar aaj payment nahi hoti hai to hum CIBIL score default mark karenge aur legal notice issue hoga.",
                "timbre_tag": "[neutral]"
            }
            return

        # Empathetic mode fallback logic
        emotion = fused_emotion.get("emotion", "neutral") if fused_emotion else "neutral"
        sarcasm = fused_emotion.get("sarcasm_detected", False) if fused_emotion else False

        if sarcasm or emotion == "frustrated":
            # Fire tool call to apply late fee waiver
            waiver_res = apply_late_fee_waiver(borrower_id, 100)
            yield {
                "type": "tool_call",
                "name": "apply_late_fee_waiver",
                "args": {"borrower_id": borrower_id, "waiver_percentage": 100},
                "result": waiver_res
            }
            await asyncio.sleep(0.05)
            yield {
                "type": "sentence",
                "text": f"{first_name} ji, main samajh sakta hoon salary delay ya technical issues ki wajah se pareshani ho sakti hai.",
                "timbre_tag": "[calm_empathetic]"
            }
            await asyncio.sleep(0.08)
            yield {
                "type": "sentence",
                "text": f"Aap bilkul stress mat lijiye, maine aapki late penalty ₹2,400 turant waive kar di hai. Kya hum remaining amount ko 2 aasan split installments mein set karein?",
                "timbre_tag": "[calm_empathetic]"
            }

        elif emotion == "stressed" or interrupted:
            yield {
                "type": "sentence",
                "text": f"Arre {first_name} ji, please shant ho jaiye. Health aur family emergency hamesha pehle aati hai.",
                "timbre_tag": "[reassuring]"
            }
            await asyncio.sleep(0.08)
            yield {
                "type": "sentence",
                "text": "Hum aapko notice nahi bhej rahe hain. Hum bas aapki suvidha ke anusaar payment plan customize karne ke liye call kiya tha.",
                "timbre_tag": "[reassuring]"
            }

        elif emotion == "confused":
            yield {
                "type": "sentence",
                "text": f"{first_name} ji, main saaf shabdon mein bata deta hoon. Aapka regular EMI ₹12,250 hai, aur 2 months ka total ₹24,500 pending hai.",
                "timbre_tag": "[calm_empathetic]"
            }
            await asyncio.sleep(0.08)
            yield {
                "type": "sentence",
                "text": "Koi bhi extra hidden charge nahi hai. Kya main iska breakup aapko WhatsApp par bhej doon?",
                "timbre_tag": "[calm_empathetic]"
            }

        elif emotion == "cooperative":
            split_res = offer_split_emi_plan(borrower_id, 2)
            yield {
                "type": "tool_call",
                "name": "offer_split_emi_plan",
                "args": {"borrower_id": borrower_id, "split_installments": 2},
                "result": split_res
            }
            await asyncio.sleep(0.05)
            yield {
                "type": "sentence",
                "text": f"Bahut dhanyawaad {first_name} ji aapke sahyog ke liye. Maine split EMI plan confirm kar diya hai.",
                "timbre_tag": "[upbeat]"
            }
            await asyncio.sleep(0.08)
            yield {
                "type": "sentence",
                "text": "Aapke registered mobile number par direct payment link bhej diya gaya hai.",
                "timbre_tag": "[upbeat]"
            }

        else:
            yield {
                "type": "sentence",
                "text": f"Namaste {first_name} ji, main Axis Premier Finance se bol raha hoon. Aapke Personal Loan account par ₹{overdue:,} overdue hai.",
                "timbre_tag": "[neutral]"
            }
            await asyncio.sleep(0.08)
            yield {
                "type": "sentence",
                "text": "Kya hum is payment ko aasan installments mein adjust kar sakte hain?",
                "timbre_tag": "[neutral]"
            }
