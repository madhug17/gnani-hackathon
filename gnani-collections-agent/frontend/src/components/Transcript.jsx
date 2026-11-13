import React, { useRef, useEffect } from 'react';
import { 
  Bot, 
  User, 
  Zap, 
  Wrench, 
  Volume2, 
  CheckCircle, 
  AlertTriangle,
  Clock
} from 'lucide-react';

export default function Transcript({ messages = [], toolCalls = [] }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, toolCalls]);

  return (
    <div className="bg-[#0B0F19] border border-slate-800 rounded-2xl p-4 shadow-xl flex flex-col h-full">
      
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-slate-100">
            Live Code-Switched Negotiation Transcript
          </h2>
        </div>
        <span className="text-[10px] text-slate-400 font-mono">
          Dual-Language Hinglish / Indian English
        </span>
      </div>

      {/* Message Stream */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-4 pt-3 pr-2 scroll-smooth"
      >
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
            <Bot className="w-10 h-10 mb-2 opacity-30 text-cyan-400" />
            <p className="text-xs">Call initialized. Press "Start Talking" or select a demo scenario above to begin negotiation.</p>
          </div>
        ) : (
          messages.map((msg, index) => {
            const isBot = msg.speaker === 'bot' || msg.role === 'assistant';
            const isInterrupted = msg.interrupted || msg.text?.includes('[INTERRUPTED');

            return (
              <div 
                key={index} 
                className={`flex gap-3 ${isBot ? 'justify-start' : 'justify-end'}`}
              >
                {/* Bot Avatar */}
                {isBot && (
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-700 flex items-center justify-center flex-shrink-0 shadow-md">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}

                {/* Message Bubble */}
                <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-xs leading-relaxed shadow-md ${
                  isBot 
                    ? 'bg-[#111827] border border-slate-800 text-slate-200' 
                    : 'bg-gradient-to-r from-blue-900/90 to-cyan-950/90 border border-cyan-800/80 text-white'
                }`}>
                  
                  {/* Header tags */}
                  <div className="flex items-center justify-between gap-2 mb-1.5 pb-1 border-b border-slate-800/50">
                    <span className="font-extrabold text-[11px] text-slate-300">
                      {isBot ? 'Gnani Collections Agent' : 'Borrower (Customer)'}
                    </span>
                    <div className="flex items-center gap-2">
                      {msg.stt_latency_ms && (
                        <span className="text-[9px] font-mono text-slate-400 flex items-center gap-0.5">
                          <Clock className="w-2.5 h-2.5 text-cyan-400" />
                          {msg.stt_latency_ms}ms STT
                        </span>
                      )}
                      {msg.timbre_tag && (
                        <span className="text-[9px] font-mono text-purple-300 bg-purple-950/70 px-1.5 py-0.2 rounded border border-purple-800/60">
                          {msg.timbre_tag}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Main Speech Text */}
                  <div className="font-medium">
                    {msg.text}
                  </div>

                  {/* INTERRUPTED Banner */}
                  {isInterrupted && (
                    <div className="mt-2.5 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-rose-950/90 border border-rose-700/80 text-rose-300 font-black text-[10px] uppercase tracking-wider animate-pulse">
                      <Zap className="w-3 h-3 text-rose-400" />
                      <span>Interrupted by Borrower (&lt;300ms Barge-In)</span>
                    </div>
                  )}

                  {/* Attached Tool Calls */}
                  {msg.tool_calls && msg.tool_calls.map((tool, tIdx) => (
                    <div 
                      key={`tool-${tIdx}`}
                      className="mt-2.5 p-2 rounded-xl bg-slate-950/90 border border-emerald-800/80 text-emerald-300 text-[11px] flex items-start gap-2 shadow-inner"
                    >
                      <Wrench className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <div className="font-bold flex items-center gap-1.5">
                          <span>Tool Executed: {tool.tool || tool.name}</span>
                          <CheckCircle className="w-3 h-3 text-emerald-400" />
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                          {tool.result?.message || JSON.stringify(tool.result || tool.args)}
                        </div>
                      </div>
                    </div>
                  ))}

                </div>

                {/* User Avatar */}
                {!isBot && (
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-slate-700 to-slate-800 flex items-center justify-center flex-shrink-0 shadow-md">
                    <User className="w-4 h-4 text-cyan-300" />
                  </div>
                )}

              </div>
            );
          })
        )}
      </div>

    </div>
  );
}

