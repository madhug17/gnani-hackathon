import React, { useState, useEffect, useRef, useCallback } from 'react';
import ControlBar from './components/ControlBar';
import TelemetryBar from './components/TelemetryBar';
import EmotionChart from './components/EmotionChart';
import Transcript from './components/Transcript';
import AssistCard from './components/AssistCard';
import { useAudioStream } from './hooks/useAudioStream';

export default function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [currentState, setCurrentState] = useState('IDLE');
  const [botMode, setBotMode] = useState('empathetic'); // empathetic vs normal
  const [metrics, setMetrics] = useState({
    barge_in_latency_ms: 0,
    e2e_latency_ms: 0,
    total_interruptions: 0,
    current_emotion: 'neutral',
    confidence: 0.70,
    sarcasm_detected: false,
    timbre_tag: '[calm_empathetic]',
    speech_rate: 'normal'
  });
  const [emotionData, setEmotionData] = useState(null);
  const [emotionHistory, setEmotionHistory] = useState([]);
  const [transcriptMessages, setTranscriptMessages] = useState([]);
  const [borrowers, setBorrowers] = useState([]);
  const [selectedBorrower, setSelectedBorrower] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [scenarioTurnIndex, setScenarioTurnIndex] = useState(0);
  const [escalationCard, setEscalationCard] = useState(null);
  const [selectedVoice, setSelectedVoice] = useState('hi_madhur');
  const [availableVoices, setAvailableVoices] = useState([
    { id: "hi_madhur", name: "Madhur (Empathetic Hindi/Hinglish Male)" },
    { id: "hi_swara", name: "Swara (Expressive Hindi/Hinglish Female)" },
    { id: "en_neerja", name: "Neerja (Professional Indian English Female)" },
    { id: "en_prabhat", name: "Prabhat (Executive Indian English Male)" }
  ]);

  // WebSocket Ref
  const wsRef = useRef(null);

  // WebSocket sender
  const sendWebSocketMessage = useCallback((msgObj) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msgObj));
    }
  }, []);

  // Web Audio Stream Hook
  const {
    isRecording,
    audioLevel,
    noiseSimulated,
    startRecording,
    stopRecording,
    enqueueAudioChunk,
    flushAudioPlayback,
    toggleStreetNoiseSimulation
  } = useAudioStream(sendWebSocketMessage);

  // Establish WebSocket Connection
  useEffect(() => {
    const wsUrl = `ws://${window.location.hostname || 'localhost'}:8000/ws/audio`;
    let socket;
    let reconnectTimer;

    const connect = () => {
      socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
        console.log("WebSocket connected to BFSI Collections Agent server.");
      };

      socket.onclose = () => {
        setIsConnected(false);
        reconnectTimer = setTimeout(connect, 2500);
      };

      socket.onerror = (err) => {
        console.warn("WebSocket error:", err);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleServerMessage(data);
        } catch (err) {
          console.error("Message parse error:", err);
        }
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      if (socket) socket.close();
    };
  }, []);

  // Fetch initial data (borrowers & demo scenarios)
  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const bRes = await fetch('http://localhost:8000/api/borrowers');
        if (bRes.ok) {
          const bData = await bRes.json();
          setBorrowers(bData);
          if (bData.length > 0) setSelectedBorrower(bData[0]);
        }
      } catch (err) {
        console.warn("Could not fetch borrowers:", err);
      }

      try {
        const sRes = await fetch('http://localhost:8000/api/scenarios');
        if (sRes.ok) {
          const sData = await sRes.json();
          setScenarios(sData);
          if (sData.length > 0) setSelectedScenario(sData[0]);
        }
      } catch (err) {
        console.warn("Could not fetch scenarios:", err);
      }
    };

    fetchMetadata();
  }, []);

  // Dispatch and handle incoming messages
  const handleServerMessage = useCallback((msg) => {
    switch (msg.type) {
      case 'SESSION_INIT':
        setBotMode(msg.bot_mode || 'empathetic');
        setCurrentState(msg.state || 'LISTENING');
        if (msg.borrower) setSelectedBorrower(msg.borrower);
        if (msg.current_voice) setSelectedVoice(msg.current_voice);
        if (msg.available_voices) setAvailableVoices(msg.available_voices);
        break;

      case 'VOICE_CHANGED':
        if (msg.voice) setSelectedVoice(msg.voice);
        break;

      case 'AUDIO_CHUNK':
        if (msg.audio_base64) {
          enqueueAudioChunk(msg.audio_base64);
        }
        break;

      case 'FLUSH_AUDIO':
        // SUB-300MS BARGE-IN EVENT!
        console.warn(`⚡ FLUSH_AUDIO received! Barge-In Latency: ${msg.barge_in_latency_ms}ms`);
        flushAudioPlayback();
        setMetrics((prev) => ({
          ...prev,
          barge_in_latency_ms: msg.barge_in_latency_ms,
          total_interruptions: prev.total_interruptions + 1
        }));
        break;

      case 'TRANSCRIPT_CHUNK':
        setTranscriptMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.speaker === 'bot' && !last.finalized) {
            return [
              ...prev.slice(0, -1),
              { ...last, text: `${last.text} ${msg.text}`.trim(), timbre_tag: msg.timbre_tag }
            ];
          } else {
            return [
              ...prev,
              { speaker: 'bot', text: msg.text, timbre_tag: msg.timbre_tag, finalized: false }
            ];
          }
        });
        break;

      case 'TRANSCRIPT_UPDATE':
        setTranscriptMessages((prev) => {
          if (msg.speaker === 'bot' && msg.interrupted) {
            // Replace last bot message with interrupted tag
            return [
              ...prev.slice(0, -1),
              { speaker: 'bot', text: msg.text, interrupted: true, finalized: true }
            ];
          }
          return [
            ...prev,
            { 
              speaker: msg.speaker, 
              text: msg.text, 
              interrupted: msg.interrupted,
              stt_latency_ms: msg.stt_latency_ms,
              finalized: true 
            }
          ];
        });
        break;

      case 'TOOL_CALL':
        setTranscriptMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.speaker === 'bot') {
            const existingTools = last.tool_calls || [];
            return [
              ...prev.slice(0, -1),
              { ...last, tool_calls: [...existingTools, msg] }
            ];
          }
          return prev;
        });
        break;

      case 'EMOTION_UPDATE':
        setEmotionData(msg.data);
        setEmotionHistory((prev) => [
          ...prev,
          {
            turn_id: prev.length + 1,
            emotion: msg.data.emotion,
            confidence: msg.data.confidence,
            interrupted: msg.data.interrupted,
            sarcasm_detected: msg.data.sarcasm_detected,
            barge_in_latency_ms: metrics.barge_in_latency_ms
          }
        ]);
        break;

      case 'TELEMETRY_UPDATE':
        setMetrics(msg.metrics);
        break;

      case 'STATE_CHANGE':
        setCurrentState(msg.state);
        break;

      case 'BOT_MODE_CHANGED':
        setBotMode(msg.mode);
        break;

      case 'ESCALATION_CARD':
        setEscalationCard(msg.card);
        break;

      case 'SESSION_RESET_COMPLETE':
        setTranscriptMessages([]);
        setEmotionHistory([]);
        setEscalationCard(null);
        setScenarioTurnIndex(0);
        break;

      default:
        break;
    }
  }, [enqueueAudioChunk, flushAudioPlayback, metrics.barge_in_latency_ms]);

  // Handlers
  const handleToggleMic = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const handleToggleBotMode = (mode) => {
    setBotMode(mode);
    sendWebSocketMessage({
      type: 'SET_BOT_MODE',
      mode: mode
    });
  };

  const handleToggleNoise = () => {
    const nextVal = !noiseSimulated;
    toggleStreetNoiseSimulation(nextVal);
    sendWebSocketMessage({
      type: 'SIMULATE_NOISE',
      enabled: nextVal
    });
  };

  const handleSelectVoice = (voiceId) => {
    setSelectedVoice(voiceId);
    sendWebSocketMessage({
      type: 'SET_VOICE',
      voice: voiceId
    });
  };

  const handleResetSession = () => {
    flushAudioPlayback();
    sendWebSocketMessage({
      type: 'RESET_SESSION'
    });
  };

  // Trigger next turn from selected scenario
  const handleTriggerScenario = () => {
    if (!selectedScenario || !selectedScenario.turns) return;

    const turns = selectedScenario.turns;
    const currentTurn = turns[scenarioTurnIndex % turns.length];
    setScenarioTurnIndex((prev) => prev + 1);

    if (currentTurn.speaker === 'borrower') {
      sendWebSocketMessage({
        type: 'USER_UTTERANCE',
        text: currentTurn.text,
        simulated_acoustic: currentTurn.simulated_acoustic,
        is_interruption: currentTurn.is_interruption || false
      });
    } else {
      // Direct mock bot response preview
      setTranscriptMessages((prev) => [
        ...prev,
        { speaker: 'bot', text: currentTurn.text, finalized: true }
      ]);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-[#080C14] text-slate-100 overflow-hidden">
      
      {/* Top Navigation & Controls */}
      <ControlBar
        isConnected={isConnected}
        isRecording={isRecording}
        audioLevel={audioLevel}
        botMode={botMode}
        noiseSimulated={noiseSimulated}
        selectedBorrower={selectedBorrower}
        borrowers={borrowers}
        scenarios={scenarios}
        selectedScenario={selectedScenario}
        selectedVoice={selectedVoice}
        availableVoices={availableVoices}
        onToggleMic={handleToggleMic}
        onToggleBotMode={handleToggleBotMode}
        onToggleNoise={handleToggleNoise}
        onSelectBorrower={setSelectedBorrower}
        onSelectScenario={(sc) => {
          setSelectedScenario(sc);
          setScenarioTurnIndex(0);
        }}
        onSelectVoice={handleSelectVoice}
        onTriggerScenario={handleTriggerScenario}
        onResetSession={handleResetSession}
      />

      {/* Latency & Fused Emotion Telemetry Strip */}
      <TelemetryBar
        metrics={metrics}
        emotionData={emotionData}
        currentState={currentState}
      />

      {/* Main Operational Split-View */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 p-4 min-h-0 overflow-hidden">
        
        {/* Left Side: Real-Time Transcript & Code-Switched Chat (7 Cols) */}
        <section className="lg:col-span-7 h-full flex flex-col min-h-0">
          <Transcript messages={transcriptMessages} />
        </section>

        {/* Right Side: Live Emotion Trajectory & Telemetry Analysis (5 Cols) */}
        <section className="lg:col-span-5 h-full flex flex-col min-h-0 gap-4">
          
          {/* Top Half: Emotion Timeline with Barge-In Markers */}
          <div className="flex-1 min-h-[220px]">
            <EmotionChart history={emotionHistory} />
          </div>

          {/* Bottom Half: Active Account & Negotiation Telemetry Info */}
          <div className="bg-[#0B0F19] border border-slate-800 rounded-2xl p-4 shadow-xl flex flex-col justify-between">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs">
              <span className="font-bold text-slate-300">Account Negotiation Card</span>
              <span className="font-mono text-cyan-400 font-bold">{selectedBorrower?.borrower_id || 'LN-98231'}</span>
            </div>

            <div className="grid grid-cols-3 gap-2 my-3 text-center">
              <div className="bg-slate-900/90 border border-slate-800 p-2 rounded-xl">
                <div className="text-[9px] uppercase font-bold text-slate-400">Total Overdue</div>
                <div className="text-sm font-black text-rose-400 mt-0.5">
                  ₹{selectedBorrower?.overdue_amount?.toLocaleString() || '24,500'}
                </div>
              </div>
              <div className="bg-slate-900/90 border border-slate-800 p-2 rounded-xl">
                <div className="text-[9px] uppercase font-bold text-slate-400">Monthly EMI</div>
                <div className="text-sm font-black text-cyan-300 mt-0.5">
                  ₹{selectedBorrower?.emi_amount?.toLocaleString() || '12,250'}
                </div>
              </div>
              <div className="bg-slate-900/90 border border-slate-800 p-2 rounded-xl">
                <div className="text-[9px] uppercase font-bold text-slate-400">Late Penalty Fee</div>
                <div className="text-sm font-black text-amber-400 mt-0.5">
                  ₹{selectedBorrower?.late_fee_accrued?.toLocaleString() || '2,400'}
                </div>
              </div>
            </div>

            <div className="text-[11px] text-slate-400 bg-slate-950/80 p-2.5 rounded-xl border border-slate-800/80 leading-relaxed">
              <span className="text-cyan-400 font-bold">Empathetic Strategy: </span>
              {botMode === 'empathetic' ? (
                <span>
                  Active Hinglish prosodic adaptation. Sarcastic polite agreement triggers immediate late fee waiver and split EMI offering. Continuous Silero VAD enforces &lt;300ms speech barge-in.
                </span>
              ) : (
                <span className="text-rose-400 font-semibold">
                  Legacy collections mode active. Robotic formal script, zero late-fee waiver, immediate full payment demands, and credit downgrade warnings.
                </span>
              )}
            </div>
          </div>

        </section>

      </main>

      {/* Gnani Assist Sub-500ms Human Escalation Modal Card */}
      {escalationCard && (
        <AssistCard
          card={escalationCard}
          onDismiss={() => setEscalationCard(null)}
        />
      )}

    </div>
  );
}

