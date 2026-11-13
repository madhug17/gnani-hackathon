import React, { useState } from 'react';
import { 
  Zap, 
  Activity, 
  Clock, 
  Sliders, 
  ChevronDown, 
  ChevronUp, 
  Code,
  ShieldCheck,
  Flame,
  Volume2
} from 'lucide-react';

export default function TelemetryBar({ metrics, emotionData, currentState }) {
  const [showJsonViewer, setShowJsonViewer] = useState(false);

  const bargeInMs = metrics?.barge_in_latency_ms || 0;
  const isBargeInSub300 = bargeInMs > 0 && bargeInMs <= 300;
  const e2eMs = metrics?.e2e_latency_ms || 0;
  const timbreTag = emotionData?.timbre_tag || metrics?.timbre_tag || "[calm_empathetic]";
  const emotion = emotionData?.emotion || metrics?.current_emotion || "neutral";
  const sarcasm = emotionData?.sarcasm_detected ?? metrics?.sarcasm_detected ?? false;
  const speechRate = emotionData?.speech_rate || metrics?.speech_rate || "normal";
  const confidence = emotionData?.confidence || metrics?.confidence || 0.0;

  // State badge styling
  const stateColors = {
    IDLE: 'bg-slate-800 text-slate-400 border-slate-700',
    LISTENING: 'bg-emerald-950/80 text-emerald-400 border-emerald-800 animate-pulse',
    THINKING: 'bg-amber-950/80 text-amber-300 border-amber-800 animate-bounce',
    SPEAKING: 'bg-cyan-950/80 text-cyan-300 border-cyan-800 animate-pulse'
  };

  return (
    <div className="bg-[#0D1322] border-b border-slate-800 px-6 py-3 shadow-inner">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
        
        {/* Core Latency Metrics Strip */}
        <div className="flex flex-wrap items-center gap-6">
          
          {/* Agent State */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Agent State:</span>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold border ${stateColors[currentState] || stateColors.IDLE}`}>
              {currentState}
            </span>
          </div>

          {/* Barge-In Latency Counter */}
          <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-xl">
            <div className={`p-1 rounded-lg ${isBargeInSub300 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'}`}>
              <Zap className="w-3.5 h-3.5" />
            </div>
            <div>
              <div className="text-[9px] uppercase tracking-wider text-slate-400 font-bold">Barge-In Latency</div>
              <div className="flex items-baseline gap-1.5">
                <span className={`text-sm font-black mono-metric ${
                  bargeInMs === 0 
                    ? 'text-slate-400' 
                    : isBargeInSub300 
                    ? 'text-emerald-400' 
                    : 'text-amber-400'
                }`}>
                  {bargeInMs > 0 ? `${bargeInMs} ms` : '—'}
                </span>
                {bargeInMs > 0 && isBargeInSub300 && (
                  <span className="text-[10px] font-bold text-emerald-400 uppercase">
                    (&lt;300ms SLA Pass)
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* E2E Turn Latency */}
          <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-xl">
            <div className="p-1 rounded-lg bg-cyan-500/20 text-cyan-400">
              <Clock className="w-3.5 h-3.5" />
            </div>
            <div>
              <div className="text-[9px] uppercase tracking-wider text-slate-400 font-bold">E2E Turn Latency</div>
              <div className="text-sm font-black text-cyan-300 mono-metric">
                {e2eMs > 0 ? `${e2eMs} ms` : '—'}
              </div>
            </div>
          </div>

          {/* Active Vocal Timbre Tag */}
          <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-xl">
            <div className="p-1 rounded-lg bg-purple-500/20 text-purple-400">
              <Volume2 className="w-3.5 h-3.5" />
            </div>
            <div>
              <div className="text-[9px] uppercase tracking-wider text-slate-400 font-bold">Active Timbre Tag</div>
              <div className="text-xs font-extrabold text-purple-300 mono-metric">
                {timbreTag}
              </div>
            </div>
          </div>

          {/* Fused Emotion Snapshot */}
          <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-xl">
            <div className="p-1 rounded-lg bg-orange-500/20 text-orange-400">
              <Activity className="w-3.5 h-3.5" />
            </div>
            <div>
              <div className="text-[9px] uppercase tracking-wider text-slate-400 font-bold">Fused Emotion</div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold text-slate-200 capitalize">{emotion}</span>
                <span className="text-[10px] font-semibold text-slate-400">({Math.round(confidence * 100)}%)</span>
                {sarcasm && (
                  <span className="px-1.5 py-0.2 rounded bg-rose-950/80 border border-rose-700/80 text-rose-300 text-[9px] font-black tracking-wider uppercase animate-pulse">
                    Sarcasm
                  </span>
                )}
              </div>
            </div>
          </div>

        </div>

        {/* Fused Emotion JSON Toggle Button */}
        <div>
          <button
            onClick={() => setShowJsonViewer(!showJsonViewer)}
            className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-semibold text-slate-300 flex items-center gap-1.5 transition shadow-sm"
          >
            <Code className="w-3.5 h-3.5 text-cyan-400" />
            <span>Fused Emotion JSON</span>
            {showJsonViewer ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

      </div>

      {/* Expandable Live Fused Emotion JSON Viewer */}
      {showJsonViewer && (
        <div className="max-w-7xl mx-auto mt-3 p-3 bg-black/80 rounded-xl border border-cyan-900/40 shadow-2xl animate-fadeIn">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs text-slate-400 font-semibold">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              Live Multimodal Fusion Payload (Acoustic Prosody + Lexical Sentiment)
            </span>
            <span className="text-[10px] text-slate-500 font-mono">2-3s Rolling Audio Window</span>
          </div>
          <pre className="mt-2 text-xs font-mono text-cyan-300 overflow-x-auto p-2 bg-slate-950 rounded-lg max-h-48">
            {JSON.stringify(emotionData || {
              emotion: "frustrated",
              confidence: 0.91,
              interrupted: metrics?.interrupted || false,
              speech_rate: "fast",
              sarcasm_detected: true,
              timbre_tag: "[calm_empathetic]"
            }, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
