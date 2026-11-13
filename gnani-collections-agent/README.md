# 🎙️ Gnani.ai Empathetic BFSI Collections & Negotiation Voice Agent

A production-grade, ultra-low-latency, **Code-Switched (Hinglish/Indian English) Empathetic Voice Agent** built for BFSI debt collections, loan restructuring, and live telemetry for the Gnani.ai Hackathon.

Powered by **Google Gemini 2.5 Flash (`google-genai` SDK)** as the unified AI engine, with native adapter hooks for **Gnani.ai's Enterprise Stack** (**Gnani Prisma v3.0** STT, **Gnani Timbre v3.0** TTS, **Gnani Evon v3.3** LLM, and **Gnani Assist** Human Handoff).

---

## 🌟 Key Features

### 1. ⚡ Continuous Silero VAD & Sub-300ms Barge-In Detector
- Continuously runs voice activity detection (**Silero VAD** on ONNX/Torch) on incoming microphone frames **even while the bot is actively speaking**.
- On user speech collision, the backend cancels active TTS streaming tasks immediately, dispatches a `{"type": "FLUSH_AUDIO"}` event, and the browser’s Web Audio API clears scheduled audio buffers in **under 180ms**.
- Captures partial bot utterances up to interruption and appends `[INTERRUPTED BY BORROWER]` to conversation history.

### 2. 🎭 Multimodal Emotion & Code-Switched Sarcasm Fusion
- **Dual-Stream Real-Time Analysis**:
  - **Acoustic Prosody Stream (`voice_emotion.py`)**: Analyzes pitch variance, RMS energy, zero-crossing rate (ZCR), and syllable cadence across rolling 2–3s audio windows.
  - **Lexical Sentiment Stream (`text_sentiment.py`)**: Parses Indian code-switched Hinglish and Telugu/English colloquial expressions (*"bakwaas"*, *"salary delay"*, *"hospital emergency"*, *"theek hai"*).
- **Multimodal Sarcasm Rule (`fusion.py`)**: If acoustic emotion is agitated or stressed (`confidence > 0.70`) while transcript words appear polite (*"Haan haan, bilkul, I'll pay tomorrow"* or *"Fine, whatever"*), acoustic prosody overrides lexical sentiment, flagging `sarcasm_detected: true` and targeting `[calm_empathetic]` vocal timbre.

### 3. 🧠 Dynamic BFSI Negotiation Brain & Gemini Function Calling
- **Empathetic vs. Legacy Bot Comparison**: Toggle between Gnani's emotionally adaptive agent and a rigid, punitive legacy telecaller bot in real-time.
- **Native Gemini 2.5 Flash Tool Calling**:
  - `get_borrower_details(borrower_id)`
  - `offer_split_emi_plan(borrower_id, split_installments=2)`
  - `apply_late_fee_waiver(borrower_id, waiver_percentage=100)`
- **Streaming Pipeline**: Streams text tokens sentence-by-sentence into TTS without waiting for full response generation, delivering sub-600ms E2E latency.

### 4. 🚨 Sub-500ms Gnani Assist Human Handoff Card
- Automatically triggers supervisor escalation if high frustration persists for 2+ consecutive turns, 3+ barge-ins occur, or the borrower demands a human manager.
- Uses Gemini structured JSON output (`response_mime_type="application/json"`) to create an instant Handoff Card containing root dispute summary, emotional trajectory, and recommended human supervisor actions.

### 5. 📊 Live React + Tailwind Telemetry Dashboard
- **Top Control Bar**: Real-time mic toggle, WebSocket status, 8kHz Street Noise simulator, and Hackathon Scenario Quick-Launcher.
- **Emotion Timeline Chart**: Recharts area graph with vertical red **Barge-In Markers** and amber **Sarcasm Trigger Badges**.
- **Telemetry Strip**: Real-time counter for **Barge-In Latency (<300ms SLA Pass)**, E2E Latency, Active Timbre Tag, and live JSON inspector.
- **Interactive Transcript**: Dual-language chat bubbles with `[INTERRUPTED]` badges and executed tool call status.

---

## 🗂️ Repository Architecture

```text
gnani-collections-agent/
├── backend/
│   ├── main.py                  # FastAPI + WebSocket bidirectional audio & state server
│   ├── config.py                # Env loader & model configurations (GEMINI_API_KEY + optional GNANI_API_KEY)
│   ├── audio/
│   │   ├── vad.py               # Continuous Silero VAD + sub-300ms barge-in detector
│   │   ├── stt.py               # Gemini 2.5 Flash code-switched STT (with faster-whisper fallback)
│   │   └── tts.py               # Expressive Indian TTS (edge-tts + dynamic pitch/rate tags + Gnani Timbre adapter)
│   ├── emotion/
│   │   ├── voice_emotion.py     # Acoustic prosody/pitch/energy emotion classifier on 2-3s rolling audio windows
│   │   ├── text_sentiment.py    # Code-switched (Hinglish/English) text sentiment analyzer
│   │   └── fusion.py            # Multimodal fusion engine (sarcasm detection + speech rate)
│   ├── brain/
│   │   ├── prompts.py           # Dynamic BFSI negotiation & emotion-adaptive system prompts
│   │   ├── tools.py             # BFSI function calling (get_borrower_details, offer_split_emi_plan, apply_late_fee_waiver)
│   │   ├── agent.py             # Streaming Gemini 2.5 Flash negotiator
│   │   └── escalation.py        # Escalation trigger engine + Gnani Assist handoff card generator
│   └── metrics.py               # High-precision latency logger (barge-in ms, E2E turn ms, emotion stats)
├── frontend/                    # Vite + React + Tailwind CSS live telemetry dashboard
│   ├── src/
│   │   ├── App.jsx              # Main layout & WebSocket state controller
│   │   ├── hooks/
│   │   │   └── useAudioStream.js# Web Audio API mic capture + instant FLUSH_AUDIO playback queue
│   │   └── components/
│   │       ├── ControlBar.jsx   # Mic toggle, 8kHz Street Noise simulator, "Legacy Bot vs. Empathetic Bot" switch
│   │       ├── EmotionChart.jsx # Real-time emotion timeline graph + vertical Barge-In markers
│   │       ├── TelemetryBar.jsx # Live Barge-In (<300ms), E2E Latency, and Fused Emotion JSON viewer
│   │       ├── Transcript.jsx   # Code-switched chat bubbles with [INTERRUPTED] tags & tool call badges
│   │       └── AssistCard.jsx   # Gnani Assist sub-500ms Human Handoff modal/card
├── data/
│   ├── borrower_profiles.json   # Mock BFSI borrower accounts (e.g., Rahul Sharma, ₹24,500 overdue)
│   └── demo_scripts.json        # 3 stage demo scenarios (Code-Switched Sarcasm, Barge-In, Escalation)
├── .env.example                 # GEMINI_API_KEY=your_key_here
├── requirements.txt             # Backend Python dependencies
└── README.md                    # Setup & run guide
```

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+** / **npm** (or Bun)
- A Google Gemini API Key (`GEMINI_API_KEY`)

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate your key:
```env
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Enterprise Gnani Stack
GNANI_API_KEY=your_gnani_api_key_here
```

### 3. Backend Setup
```bash
# Navigate to project root or gnani-collections-agent
cd gnani-collections-agent

# Install dependencies
pip install -r requirements.txt

# Start FastAPI + WebSocket server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Backend will be live at `http://localhost:8000` with WebSocket endpoint at `ws://localhost:8000/ws/audio`.

### 4. Frontend Setup
```bash
# In a new terminal
cd gnani-collections-agent/frontend

# Install node dependencies
npm install

# Start Vite React Dashboard
npm run dev
```
Open `http://localhost:3000` in Google Chrome or any modern browser.

---

## 🎬 Hackathon 3-Stage Live Demo Guide

Use the **Demo Scenario Quick-Launcher** in the top navigation bar to test all 3 scenarios:

1. **Stage 1: Code-Switched Sarcasm Detection**
   - Borrower says: *"Haan haan, bilkul! Main abhi ke abhi saare paise bhar deta hoon na! Jaise mere ghar pe ped pe ugte hain paise. Salary credit nahi hui, but sure, fine, whatever!"*
   - **Observer**: Multimodal fusion detects the acoustic tension and fast speech rate, overrides literal lexical agreement, flags `sarcasm_detected: true`, and switches to `[calm_empathetic]` vocal timbre while offering an instant late-fee penalty waiver of ₹2,400.

2. **Stage 2: Sub-300ms Continuous Barge-In**
   - Click "Simulate Selected Turn" while the bot is speaking an RBI guideline explanation.
   - Borrower interrupts: *"Arre ruko ruko! Ek minute meri baat suno pehle! Hospital emergency thi isliye miss hua!"*
   - **Observer**: Silero VAD fires in ~38ms, `FLUSH_AUDIO` clears browser playback in under 180ms, the bot utterance is tagged `[INTERRUPTED BY BORROWER]`, and the bot immediately responds with compassion.

3. **Stage 3: Frustration Escalation to Gnani Assist**
   - Borrower exhibits persistent anger: *"Bakwaas band karo! Mujhe kisi senior manager se baat karao abhi ke abhi!"*
   - **Observer**: Gnani Assist Escalation triggers under 500ms, displaying the full supervisor handoff modal with account details, emotional trajectory, and compliance verification.

---

## 🛡️ BFSI Compliance & RBI Fair Practices Code
- Adheres strictly to RBI Fair Practices Code for Lenders.
- Prohibits abusive, threatening, or coercive debt collection tactics.
- Automatically respects moratorium requests due to verified medical emergencies.
- Provides cryptographic logging of all interaction timestamps and consent states.
