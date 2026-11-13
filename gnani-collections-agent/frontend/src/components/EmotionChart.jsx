import React from 'react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  ReferenceLine,
  CartesianGrid
} from 'recharts';
import { Activity, ShieldAlert, Zap, AlertCircle } from 'lucide-react';

export default function EmotionChart({ history = [] }) {
  // Map emotion names to numerical arousal/stress scale (0 to 100)
  // neutral: 30, cooperative: 20, confused: 55, stressed: 75, frustrated: 90
  const emotionScoreMap = {
    cooperative: 20,
    neutral: 35,
    confused: 55,
    stressed: 75,
    frustrated: 90
  };

  const chartData = history.map((item, index) => {
    const emotion = item.emotion || 'neutral';
    const baseScore = emotionScoreMap[emotion] || 35;
    const confidence = item.confidence || 0.8;
    const intensity = Math.round(baseScore * confidence);

    return {
      turn: `Turn ${item.turn_id || index + 1}`,
      intensity: intensity,
      emotion: emotion,
      confidence: Math.round(confidence * 100),
      interrupted: item.interrupted || false,
      sarcasm: item.sarcasm_detected || false,
      bargeInMs: item.barge_in_latency_ms || 0
    };
  });

  // Default initial point if empty
  if (chartData.length === 0) {
    chartData.push({
      turn: 'Turn 1',
      intensity: 35,
      emotion: 'neutral',
      confidence: 70,
      interrupted: false,
      sarcasm: false,
      bargeInMs: 0
    });
  }

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-[#0B0F19] border border-cyan-800/80 p-3 rounded-xl shadow-2xl text-xs space-y-1">
          <div className="font-bold text-white flex items-center justify-between gap-4">
            <span>{data.turn}</span>
            <span className="capitalize text-cyan-400 font-mono">{data.emotion}</span>
          </div>
          <div className="text-slate-400">
            Arousal / Tension: <span className="text-white font-mono">{data.intensity}/100</span>
          </div>
          <div className="text-slate-400">
            Model Confidence: <span className="text-white font-mono">{data.confidence}%</span>
          </div>
          {data.sarcasm && (
            <div className="text-rose-400 font-bold flex items-center gap-1">
              <ShieldAlert className="w-3 h-3" /> Sarcasm Overridden
            </div>
          )}
          {data.interrupted && (
            <div className="text-amber-400 font-bold flex items-center gap-1">
              <Zap className="w-3 h-3" /> Barge-In: {data.bargeInMs} ms
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-[#0D1322] border border-slate-800 rounded-2xl p-4 shadow-xl flex flex-col h-full">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-slate-100">
            Real-Time Emotion & Barge-In Trajectory
          </h2>
        </div>
        <div className="flex items-center gap-4 text-[11px] font-semibold text-slate-400">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
            <span>Emotional Stress Index</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
            <span>Barge-In Marker</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <span>Sarcasm Trigger</span>
          </div>
        </div>
      </div>

      <div className="flex-1 w-full min-h-[160px] pt-3">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 20, left: -25, bottom: 0 }}>
            <defs>
              <linearGradient id="emotionGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#06B6D4" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
            <XAxis dataKey="turn" stroke="#64748B" fontSize={11} tickLine={false} />
            <YAxis stroke="#64748B" fontSize={11} domain={[0, 100]} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            
            {/* Vertical reference markers for Barge-In and Sarcasm */}
            {chartData.map((d, i) => {
              if (d.interrupted) {
                return (
                  <ReferenceLine
                    key={`bargein-${i}`}
                    x={d.turn}
                    stroke="#EF4444"
                    strokeWidth={2}
                    strokeDasharray="4 2"
                    label={{
                      value: `⚡ Interrupted (${d.bargeInMs}ms)`,
                      position: 'top',
                      fill: '#EF4444',
                      fontSize: 10,
                      fontWeight: 700
                    }}
                  />
                );
              }
              if (d.sarcasm) {
                return (
                  <ReferenceLine
                    key={`sarcasm-${i}`}
                    x={d.turn}
                    stroke="#F59E0B"
                    strokeWidth={2}
                    strokeDasharray="3 3"
                    label={{
                      value: '🎭 Sarcasm',
                      position: 'insideTopRight',
                      fill: '#F59E0B',
                      fontSize: 10,
                      fontWeight: 700
                    }}
                  />
                );
              }
              return null;
            })}

            <Area
              type="monotone"
              dataKey="intensity"
              stroke="#06B6D4"
              strokeWidth={3}
              fillOpacity={1}
              fill="url(#emotionGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
