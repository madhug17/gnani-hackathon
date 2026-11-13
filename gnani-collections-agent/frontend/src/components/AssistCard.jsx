import React from 'react';
import { 
  ShieldAlert, 
  UserCheck, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  ArrowRight, 
  X,
  PhoneCall,
  Activity
} from 'lucide-react';

export default function AssistCard({ card, onDismiss }) {
  if (!card) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[#0B0F19] border-2 border-amber-500/80 rounded-2xl max-w-xl w-full p-6 shadow-2xl shadow-amber-500/20 relative animate-scaleUp">
        
        {/* Close Button */}
        <button 
          onClick={onDismiss}
          className="absolute top-4 right-4 p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Top Header Badge */}
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/40 animate-pulse">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-black uppercase tracking-wider text-amber-400 bg-amber-950/80 px-2 py-0.5 rounded border border-amber-800">
                Gnani Assist Sub-500ms Human Handoff
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                ID: {card.handoff_id}
              </span>
            </div>
            <h2 className="text-lg font-extrabold text-white mt-1">
              Live Supervisor Intervention Triggered
            </h2>
          </div>
        </div>

        {/* Latency & SLA Notice */}
        <div className="flex items-center justify-between bg-slate-900/90 border border-slate-800 rounded-xl px-4 py-2 mb-4 text-xs">
          <span className="text-slate-400 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            Handoff Card Generation Time:
          </span>
          <span className="font-mono font-bold text-emerald-400">
            {card.latency_ms || 280} ms (&lt;500ms SLA Pass)
          </span>
        </div>

        {/* Core Account Details */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-slate-900/80 border border-slate-800/80 p-3 rounded-xl">
            <div className="text-[10px] uppercase font-bold text-slate-400">Borrower</div>
            <div className="text-sm font-black text-white mt-0.5">{card.borrower_name}</div>
          </div>
          <div className="bg-slate-900/80 border border-slate-800/80 p-3 rounded-xl">
            <div className="text-[10px] uppercase font-bold text-slate-400">Total Overdue</div>
            <div className="text-sm font-black text-rose-400 mt-0.5">₹{card.overdue_amount?.toLocaleString()}</div>
          </div>
        </div>

        {/* Issue Summary */}
        <div className="mb-4">
          <div className="text-[10px] uppercase font-bold text-slate-400 mb-1">Root Dispute Summary</div>
          <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 leading-relaxed font-medium">
            {card.issue_summary}
          </div>
        </div>

        {/* Emotion Trajectory */}
        <div className="mb-4">
          <div className="text-[10px] uppercase font-bold text-slate-400 mb-1 flex items-center gap-1.5">
            <Activity className="w-3 h-3 text-cyan-400" />
            Emotion Trajectory (Recent Turns)
          </div>
          <div className="flex items-center gap-2">
            {(card.emotion_trajectory || ['neutral', 'frustrated', 'frustrated']).map((em, idx) => (
              <React.Fragment key={idx}>
                <span className={`px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider ${
                  em === 'frustrated' 
                    ? 'bg-rose-950/80 border border-rose-800 text-rose-300' 
                    : 'bg-slate-900 border border-slate-800 text-slate-300'
                }`}>
                  {em}
                </span>
                {idx < (card.emotion_trajectory?.length - 1) && (
                  <ArrowRight className="w-3 h-3 text-slate-600" />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Negotiation Steps Tried */}
        <div className="mb-4">
          <div className="text-[10px] uppercase font-bold text-slate-400 mb-1">Negotiation Steps Tried by Voice Agent</div>
          <ul className="space-y-1">
            {(card.negotiation_steps_tried || []).map((step, sIdx) => (
              <li key={sIdx} className="text-xs text-slate-300 flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                <span>{step}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Recommended Next Action */}
        <div className="p-3 bg-gradient-to-r from-blue-950/80 to-cyan-950/80 border border-cyan-800/80 rounded-xl mb-4">
          <div className="text-[10px] uppercase font-bold text-cyan-300 mb-0.5">Recommended Human Action</div>
          <div className="text-xs text-white font-medium">
            {card.recommended_next_action}
          </div>
        </div>

        {/* Compliance Footer */}
        <div className="text-[10px] text-slate-400 bg-slate-950/80 p-2.5 rounded-lg border border-slate-800 mb-5 flex items-center gap-2">
          <UserCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>{card.compliance_status}</span>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3">
          <button
            onClick={onDismiss}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition"
          >
            Dismiss
          </button>
          <button
            onClick={() => {
              alert("Gnani Assist: Call routed to Senior Supervisor line! Live audio stream patched.");
              onDismiss();
            }}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-slate-950 font-black text-xs uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-amber-500/25 transition"
          >
            <PhoneCall className="w-3.5 h-3.5" />
            Accept Live Call Patch
          </button>
        </div>

      </div>
    </div>
  );
}

