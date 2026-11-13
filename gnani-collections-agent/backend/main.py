import asyncio
import base64
import json
import logging
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.metrics import SessionMetrics
from backend.audio.vad import ContinuousSileroVAD, BargeInDetector
from backend.audio.stt import CodeSwitchedSTT
from backend.audio.tts import ExpressiveIndianTTS
from backend.emotion.fusion import MultimodalEmotionFusion
from backend.brain.tools import _load_borrowers, get_borrower_details
from backend.brain.agent import GeminiBFSIgent
from backend.brain.escalation import GnaniAssistEscalationEngine

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("main_server")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-grade, ultra-low-latency Code-Switched Empathetic BFSI Collections Voice Agent"
)

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared In-Memory State
active_borrower = {
    "borrower_id": "LN-98231",
    "name": "Rahul Sharma",
    "loan_type": "Personal Loan",
    "overdue_amount": 24500,
    "emi_amount": 12250,
    "days_overdue": 42
}

@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "gemini_api_configured": bool(settings.GEMINI_API_KEY and "your_" not in settings.GEMINI_API_KEY),
        "gnani_api_configured": bool(settings.GNANI_API_KEY and "your_" not in settings.GNANI_API_KEY)
    }

@app.get("/api/borrowers")
async def list_borrowers():
    borrowers = _load_borrowers()
    return JSONResponse(content=borrowers)

@app.get("/api/scenarios")
async def get_scenarios():
    if settings.DEMO_SCRIPTS_PATH.exists():
        with open(settings.DEMO_SCRIPTS_PATH, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    return JSONResponse(content=[])


class VoiceAgentSession:
    """
    Manages a single bidirectional WebSocket voice session, state machine,
    and sub-300ms continuous barge-in pipeline.
    """
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.session_id = f"SES-{int(time.time()*1000)%1000000}"
        self.metrics = SessionMetrics(self.session_id)
        
        # Audio components
        self.vad = ContinuousSileroVAD(sample_rate=settings.SAMPLE_RATE)
        self.barge_in = BargeInDetector(self.vad, self.handle_barge_in_event)
        self.stt = CodeSwitchedSTT()
        self.tts = ExpressiveIndianTTS()
        
        # Emotion & Brain
        self.fusion = MultimodalEmotionFusion()
        self.agent = GeminiBFSIgent()
        self.escalation = GnaniAssistEscalationEngine()
        
        # State tracking
        self.state = "IDLE"  # IDLE, LISTENING, THINKING, SPEAKING
        self.bot_mode = "empathetic"  # empathetic vs normal (legacy)
        self.noise_simulation_active = False
        self.conversation_history: List[Dict[str, str]] = []
        
        # Active playback tasks & partial utterance tracking
        self.active_tts_task: Optional[asyncio.Task] = None
        self.current_bot_utterance: str = ""
        self.pcm_audio_buffer: bytearray = bytearray()
        self.turn_start_timestamp: float = 0.0

    async def broadcast_state(self, new_state: str):
        self.state = new_state
        self.barge_in.set_bot_speaking(new_state == "SPEAKING")
        await self.send_json({"type": "STATE_CHANGE", "state": new_state})

    async def send_json(self, payload: Dict[str, Any]):
        try:
            await self.ws.send_text(json.dumps(payload))
        except Exception:
            pass

    async def handle_barge_in_event(self, vad_speech_timestamp: float):
        """
        SUB-300ms CRITICAL BARGE-IN HANDLER.
        Executes immediately when borrower speech is detected while bot is speaking.
        """
        # 1. Cancel active TTS synthesis task immediately
        self.tts.cancel_current_speech()
        if self.active_tts_task and not self.active_tts_task.done():
            self.active_tts_task.cancel()

        # 2. Record high-precision barge-in latency in metrics
        barge_in_latency_ms = self.metrics.record_barge_in_flush()
        logger.info(f"⚡ BARGE-IN DETECTED! Latency: {barge_in_latency_ms:.2f}ms. Emitting FLUSH_AUDIO.")

        # 3. Transmit FLUSH_AUDIO event so browser clears its Web Audio buffer instantly
        await self.send_json({
            "type": "FLUSH_AUDIO",
            "barge_in_latency_ms": barge_in_latency_ms,
            "timestamp": time.time()
        })

        # 4. Save partial bot utterance and append [INTERRUPTED BY BORROWER]
        if self.current_bot_utterance:
            interrupted_text = f"{self.current_bot_utterance.strip()} [INTERRUPTED BY BORROWER]"
            # Update last turn in conversation history
            if self.conversation_history and self.conversation_history[-1]["role"] == "assistant":
                self.conversation_history[-1]["content"] = interrupted_text
            else:
                self.conversation_history.append({"role": "assistant", "content": interrupted_text})

            await self.send_json({
                "type": "TRANSCRIPT_UPDATE",
                "speaker": "bot",
                "text": interrupted_text,
                "interrupted": True
            })
            self.current_bot_utterance = ""

        # 5. Switch directly back to LISTENING
        await self.broadcast_state("LISTENING")
        
        # 6. Push updated telemetry snapshot
        await self.send_json({
            "type": "TELEMETRY_UPDATE",
            "metrics": self.metrics.get_latest_telemetry()
        })

    async def process_user_turn(
        self,
        audio_bytes: bytes,
        transcript_override: Optional[str] = None,
        simulated_acoustic: Optional[Dict[str, Any]] = None,
        is_interruption: bool = False
    ):
        """
        Full Turn Lifecycle: STT -> Multimodal Fusion -> Agent Reasoning -> Streaming TTS.
        """
        self.turn_start_timestamp = time.perf_counter()
        turn_metric = self.metrics.start_turn()

        await self.broadcast_state("THINKING")

        # 1. Speech Recognition (Gemini 2.5 Flash / Gnani Prisma / Fallback)
        if transcript_override:
            user_text = transcript_override
            stt_latency_ms = 45.0
            stt_engine = "Direct / Demo Prompt"
        else:
            user_text, stt_latency_ms, stt_engine = await self.stt.transcribe(audio_bytes)

        self.metrics.record_stt_end(stt_latency_ms)

        # Append to transcript
        self.conversation_history.append({"role": "user", "content": user_text})
        await self.send_json({
            "type": "TRANSCRIPT_UPDATE",
            "speaker": "user",
            "text": user_text,
            "interrupted": is_interruption,
            "stt_engine": stt_engine,
            "stt_latency_ms": round(stt_latency_ms, 1)
        })

        # 2. Multimodal Emotion & Sarcasm Fusion
        if self.bot_mode == "empathetic":
            fusion_result = await self.fusion.fuse(
                pcm_bytes=audio_bytes,
                transcript_text=user_text,
                interrupted=is_interruption,
                simulated_acoustic=simulated_acoustic
            )
        else:
            # Legacy bot ignores prosodic cues
            fusion_result = {
                "emotion": "neutral",
                "confidence": 0.50,
                "interrupted": is_interruption,
                "speech_rate": "normal",
                "sarcasm_detected": False,
                "timbre_tag": "[neutral]"
            }

        self.metrics.record_emotion_fusion(fusion_result)
        await self.send_json({
            "type": "EMOTION_UPDATE",
            "data": fusion_result
        })

        # 3. Escalation Check
        should_escalate, reason = self.escalation.evaluate_escalation_triggers(
            fused_emotion=fusion_result,
            transcript_text=user_text,
            was_interrupted=is_interruption
        )

        if should_escalate and self.bot_mode == "empathetic":
            handoff_card = await self.escalation.generate_handoff_card(
                borrower_profile=active_borrower,
                conversation_history=self.conversation_history,
                escalation_reason=reason
            )
            await self.send_json({
                "type": "ESCALATION_CARD",
                "card": handoff_card
            })

        # 4. Stream Gemini BFSI Negotiator Response directly into TTS
        await self.broadcast_state("SPEAKING")
        self.current_bot_utterance = ""
        first_token_marked = False
        first_audio_marked = False
        timbre_tag = fusion_result.get("timbre_tag", "[calm_empathetic]")

        try:
            agent_stream = self.agent.generate_response_stream(
                conversation_history=self.conversation_history,
                borrower_profile=active_borrower,
                fused_emotion=fusion_result,
                bot_mode=self.bot_mode,
                interrupted=is_interruption
            )

            async for item in agent_stream:
                if self.state != "SPEAKING":
                    logger.info("Bot speech aborted due to state shift / interruption.")
                    break

                if item["type"] == "tool_call":
                    # Emit tool call badge for UI
                    await self.send_json({
                        "type": "TOOL_CALL",
                        "tool": item["name"],
                        "args": item.get("args", {}),
                        "result": item.get("result", {})
                    })

                elif item["type"] == "sentence":
                    sentence_text = item["text"]
                    self.current_bot_utterance += " " + sentence_text
                    
                    if not first_token_marked:
                        self.metrics.record_llm_first_token(self.turn_start_timestamp)
                        first_token_marked = True

                    # Push text transcript chunk to client
                    await self.send_json({
                        "type": "TRANSCRIPT_CHUNK",
                        "speaker": "bot",
                        "text": sentence_text,
                        "timbre_tag": timbre_tag
                    })

                    # Stream synthesized audio chunks immediately
                    async for audio_chunk in self.tts.stream_speech(
                        text=sentence_text,
                        timbre_tag=timbre_tag
                    ):
                        if self.state != "SPEAKING":
                            break

                        if not first_audio_marked:
                            self.metrics.record_first_audio_chunk(self.turn_start_timestamp)
                            first_audio_marked = True

                        if audio_chunk:
                            chunk_b64 = base64.b64encode(audio_chunk).decode("ascii")
                            await self.send_json({
                                "type": "AUDIO_CHUNK",
                                "audio_base64": chunk_b64,
                                "timbre_tag": timbre_tag
                            })

            # Record final bot turn in history if not interrupted
            if self.state == "SPEAKING" and self.current_bot_utterance:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": self.current_bot_utterance.strip()
                })
                await self.broadcast_state("LISTENING")

        except asyncio.CancelledError:
            logger.info("process_user_turn cancelled.")
        except Exception as err:
            logger.error(f"Error during bot turn generation: {err}")
            await self.broadcast_state("LISTENING")

        # Telemetry update
        await self.send_json({
            "type": "TELEMETRY_UPDATE",
            "metrics": self.metrics.get_latest_telemetry()
        })


@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    await websocket.accept()
    session = VoiceAgentSession(websocket)
    logger.info(f"WebSocket Client connected. Session ID: {session.session_id}")

    # Send initial handshakes
    await session.send_json({
        "type": "SESSION_INIT",
        "session_id": session.session_id,
        "borrower": active_borrower,
        "bot_mode": session.bot_mode,
        "state": session.state
    })
    await session.broadcast_state("LISTENING")

    try:
        while True:
            raw_msg = await websocket.receive_text()
            data = json.loads(raw_msg)
            msg_type = data.get("type")

            if msg_type == "AUDIO_FRAME":
                # Continuous incoming microphone PCM chunk (16kHz 16-bit mono)
                pcm_b64 = data.get("pcm_base64")
                if pcm_b64:
                    pcm_bytes = base64.b64decode(pcm_b64)
                    session.pcm_audio_buffer.extend(pcm_bytes)

                    # Continuous Silero VAD Barge-In detection
                    barge_in_fired, latency = await session.barge_in.process_frame(pcm_bytes)
                    if barge_in_fired:
                        logger.info(f"Barge-In triggered from audio frame in {latency:.1f}ms")

            elif msg_type == "END_OF_SPEECH":
                # User finished speaking an utterance
                buffer_bytes = bytes(session.pcm_audio_buffer)
                session.pcm_audio_buffer.clear()
                
                asyncio.create_task(
                    session.process_user_turn(
                        audio_bytes=buffer_bytes,
                        transcript_override=data.get("transcript_hint"),
                        simulated_acoustic=data.get("simulated_acoustic"),
                        is_interruption=data.get("is_interruption", False)
                    )
                )

            elif msg_type == "USER_UTTERANCE":
                # Direct trigger for text or demo simulation
                text = data.get("text", "")
                sim_ac = data.get("simulated_acoustic")
                is_intr = data.get("is_interruption", False)
                dummy_pcm = bytes(session.pcm_audio_buffer)
                session.pcm_audio_buffer.clear()

                asyncio.create_task(
                    session.process_user_turn(
                        audio_bytes=dummy_pcm,
                        transcript_override=text,
                        simulated_acoustic=sim_ac,
                        is_interruption=is_intr
                    )
                )

            elif msg_type == "SET_BOT_MODE":
                new_mode = data.get("mode", "empathetic")
                session.bot_mode = new_mode
                logger.info(f"Switched Bot Mode to: {new_mode}")
                await session.send_json({"type": "BOT_MODE_CHANGED", "mode": new_mode})

            elif msg_type == "SIMULATE_NOISE":
                enabled = bool(data.get("enabled", False))
                session.noise_simulation_active = enabled
                logger.info(f"8kHz Street Noise Simulation toggled: {enabled}")
                await session.send_json({"type": "NOISE_SIMULATION_CHANGED", "enabled": enabled})

            elif msg_type == "RESET_SESSION":
                session.conversation_history.clear()
                session.metrics = SessionMetrics(session.session_id)
                session.escalation = GnaniAssistEscalationEngine()
                await session.send_json({"type": "SESSION_RESET_COMPLETE"})
                await session.broadcast_state("LISTENING")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session.session_id}")
    except Exception as err:
        logger.error(f"WebSocket session error: {err}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
