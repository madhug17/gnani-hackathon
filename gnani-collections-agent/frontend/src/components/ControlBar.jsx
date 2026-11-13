import React from 'react';
import { 
  Mic, 
  MicOff, 
  Volume2, 
  VolumeX, 
  Radio, 
  RefreshCw, 
  Zap, 
  ShieldAlert, 
  User, 
  Sparkles,
  Play
} from 'lucide-react';

export default function ControlBar({
  isConnected,
  isRecording,
  audioLevel,
  botMode,
  noiseSimulated,
  selectedBorrower,
  borrowers,
  scenarios,
  selectedScenario,
  selectedVoice = "hi_madhur",
  availableVoices = [],
  onToggleMic,
  onToggleBotMode,
  onToggleNoise,
  onSelectBorrower,
  onSelectScenario,
  onSelectVoice,
  onTriggerScenario,
  onResetSession
}) {
  return (
    <header className="bg-[#0B0F19] border-b border-slate-800/80 px-6 py-4 shadow-xl">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
        
        {/* Brand & Connection State */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-cyan-500 to-teal-400 p-0.5 shadow-lg shadow-cyan-500/20">
              <div className="w-full h-full bg-[#080C14] rounded-[10px] flex items-center justify-center">
                <Radio className="w-5 h-5 text-cyan-400 animate-pulse" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-extrabold tracking-tight text-white">
                  Gnani<span className="text-cyan-400">.ai</span>
                </h1>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800/60 text-cyan-300">
                  BFSI Collections Voice Agent
                </span>
              </div>
              <p className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
                <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-ping' : 'bg-rose-500'}`} />
                <span className="text-[11px] font-medium text-slate-300">
                  {isConnected ? 'WebSocket Online (sub-300ms duplex)' : 'Connecting to Server...'}
                </span>
              </p>
            </div>
          </div>
        </div>

        {/* Borrower Selection */}
        <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-xl">
          <User className="w-4 h-4 text-cyan-400" />
          <div className="flex flex-col text-left">
            <span className="text-[9px] uppercase tracking-wider text-slate-400 font-semibold">Active Account</span>
            <select
              value={selectedBorrower?.borrower_id || ''}
              onChange={(e) => {
                const found = borrowers.find(b => b.borrower_id === e.target.value);
                if (found) onSelectBorrower(found);
              }}
              className="bg-transparent text-xs font-semibold text-slate-200 outline-none cursor-pointer pr-2"
            >
              {borrowers.map((b) => (
                <option key={b.borrower_id} value={b.borrower_id} className="bg-slate-900 text-slate-200">
                  {b.name} (Overdue: ₹{b.overdue_amount.toLocaleString()})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Studio Neural Voice Selector */}
        <div className="flex items-center gap-2 bg-slate-900/90 border border-cyan-900/50 px-3 py-1.5 rounded-xl shadow-sm">
          <Volume2 className="w-4 h-4 text-purple-400" />
          <div className="flex flex-col text-left">
            <span className="text-[9px] uppercase tracking-wider text-purple-300 font-bold">Neural Voice Profile</span>
            <select
              value={selectedVoice}
              onChange={(e) => onSelectVoice && onSelectVoice(e.target.value)}
              className="bg-transparent text-xs font-bold text-slate-100 outline-none cursor-pointer pr-2"
            >
              {(availableVoices.length > 0 ? availableVoices : [
                { id: "hi_madhur", name: "Madhur (Warm Hindi/Hinglish Male)" },
                { id: "hi_swara", name: "Swara (Expressive Hindi/Hinglish Female)" },
                { id: "en_neerja", name: "Neerja (Professional Indian English Female)" },
                { id: "en_prabhat", name: "Prabhat (Executive Indian English Male)" }
              ]).map((v) => (
                <option key={v.id} value={v.id} className="bg-slate-900 text-slate-200 font-medium">
                  {v.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Toggle Mode: Legacy vs Gnani Empathetic */}
        <div className="flex items-center bg-slate-900/90 border border-slate-800 p-1 rounded-xl">
          <button
            onClick={() => onToggleBotMode('normal')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              botMode === 'normal'
                ? 'bg-rose-950/80 text-rose-400 border border-rose-800/80 shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Rigid legacy telecalling script, ignores borrower emotions, threatens legal action"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            Legacy Bot
          </button>
          <button
            onClick={() => onToggleBotMode('empathetic')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              botMode === 'empathetic'
                ? 'bg-gradient-to-r from-cyan-900/80 to-blue-900/80 text-cyan-300 border border-cyan-700/80 shadow-lg shadow-cyan-900/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Adaptive Code-switched Hinglish, multimodal sarcasm detection, late-fee waivers & split EMIs"
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            Gnani Empathetic Bot
          </button>
        </div>

        {/* Controls: Noise Simulator & Mic Button */}
        <div className="flex items-center gap-3">
          {/* 8kHz Street Noise Simulator */}
          <button
            onClick={onToggleNoise}
            className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all flex items-center gap-2 ${
              noiseSimulated
                ? 'bg-amber-950/70 border-amber-600/80 text-amber-300 shadow-md shadow-amber-900/20'
                : 'bg-slate-900/80 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
            title="Injects 8kHz filtered traffic and telephonic background noise to test noise-robust VAD"
          >
            {noiseSimulated ? <Volume2 className="w-4 h-4 text-amber-400 animate-pulse" /> : <VolumeX className="w-4 h-4" />}
            <span>8kHz Street Noise</span>
          </button>

          {/* Primary Push-to-Talk / Continuous Mic Toggle */}
          <button
            onClick={onToggleMic}
            className={`px-5 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2.5 shadow-lg ${
              isRecording
                ? 'bg-rose-600 hover:bg-rose-500 text-white animate-pulse shadow-rose-600/30'
                : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-extrabold shadow-cyan-500/25'
            }`}
          >
            {isRecording ? (
              <>
                <MicOff className="w-4 h-4 text-white" />
                <span>Stop Mic ({audioLevel}%)</span>
              </>
            ) : (
              <>
                <Mic className="w-4 h-4 text-slate-950" />
                <span>Start Talking</span>
              </>
            )}
          </button>

          {/* Reset Call Session */}
          <button
            onClick={onResetSession}
            className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-400 hover:text-slate-100 hover:border-slate-700 transition"
            title="Reset conversation state & metrics"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

      </div>

      {/* Demo Scenario Quick-Launcher Bar */}
      <div className="max-w-7xl mx-auto mt-3 pt-3 border-t border-slate-800/50 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 text-slate-400">
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          <span className="font-semibold text-slate-300">Hackathon Demo Scenarios:</span>
          <select
            value={selectedScenario?.scenario_id || ''}
            onChange={(e) => {
              const sc = scenarios.find(s => s.scenario_id === e.target.value);
              if (sc) onSelectScenario(sc);
            }}
            className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 font-medium outline-none cursor-pointer"
          >
            {scenarios.map(sc => (
              <option key={sc.scenario_id} value={sc.scenario_id}>
                {sc.title}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={onTriggerScenario}
          className="px-3.5 py-1 rounded-lg bg-cyan-950/70 border border-cyan-700/80 hover:bg-cyan-900 text-cyan-300 font-semibold transition flex items-center gap-1.5 shadow-sm"
        >
          <Play className="w-3 h-3 text-cyan-400" />
          Simulate Selected Turn
        </button>
      </div>
    </header>
  );
}

