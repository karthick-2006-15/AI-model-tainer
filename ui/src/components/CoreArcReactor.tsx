import React from 'react';
import { AgentStateType } from '../types/hud';
import { Mic, Cpu, Zap, Activity } from 'lucide-react';
import { VoiceVisualizer } from './VoiceVisualizer';

interface Props {
  state: AgentStateType;
  statusMessage?: string;
  onMicClick?: () => void;
}

export const CoreArcReactor: React.FC<Props> = ({ state, statusMessage, onMicClick }) => {
  const getStateColor = () => {
    switch (state) {
      case 'listening':
        return 'border-emerald-400 text-emerald-400 shadow-emerald-500/50';
      case 'thinking':
        return 'border-cyan-400 text-cyan-400 shadow-cyan-500/60 animate-pulse';
      case 'executing':
        return 'border-amber-400 text-amber-400 shadow-amber-500/50';
      case 'verifying':
        return 'border-indigo-400 text-indigo-400 shadow-indigo-500/50';
      case 'error':
        return 'border-rose-500 text-rose-500 shadow-rose-500/50';
      case 'idle':
      default:
        return 'border-cyan-500/60 text-cyan-400 shadow-cyan-500/30';
    }
  };

  const getStateGlow = () => {
    switch (state) {
      case 'listening': return 'rgba(52, 211, 153, 0.4)';
      case 'thinking': return 'rgba(6, 182, 212, 0.6)';
      case 'executing': return 'rgba(251, 191, 36, 0.5)';
      case 'error': return 'rgba(244, 63, 94, 0.5)';
      default: return 'rgba(6, 182, 212, 0.25)';
    }
  };

  const getWaveColor = () => {
    switch (state) {
      case 'listening': return '#34d399';
      case 'thinking': return '#06b6d4';
      case 'executing': return '#fbbf24';
      case 'error': return '#f43f5e';
      default: return '#0891b2';
    }
  };

  return (
    <div className="relative flex flex-col items-center justify-center p-8 select-none">
      {/* Outer Rotating Segment Ring */}
      <div 
        className={`relative w-72 h-72 rounded-full border-2 border-dashed ${getStateColor()} flex items-center justify-center transition-all duration-700 animate-spin-slow`}
        style={{ boxShadow: `0 0 35px ${getStateGlow()}` }}
      >
        {/* Decorative Ring Nodes */}
        <div className="absolute top-0 w-3 h-3 bg-cyan-400 rounded-full shadow-[0_0_10px_#06b6d4]"></div>
        <div className="absolute bottom-0 w-3 h-3 bg-cyan-400 rounded-full shadow-[0_0_10px_#06b6d4]"></div>
        <div className="absolute left-0 w-3 h-3 bg-cyan-400 rounded-full shadow-[0_0_10px_#06b6d4]"></div>
        <div className="absolute right-0 w-3 h-3 bg-cyan-400 rounded-full shadow-[0_0_10px_#06b6d4]"></div>
      </div>

      {/* Middle Counter-Rotating Geometric Ring */}
      <div className="absolute w-56 h-56 rounded-full border border-cyan-500/40 border-t-2 border-t-cyan-300 animate-spin-reverse flex items-center justify-center">
        <div className="w-48 h-48 rounded-full border border-blue-500/30"></div>
      </div>

      {/* Inner Glowing Arc Core */}
      <div 
        onClick={onMicClick}
        className={`absolute w-36 h-36 rounded-full bg-[#040e21] border-2 ${getStateColor()} flex flex-col items-center justify-center cursor-pointer transition-transform duration-300 hover:scale-105 group`}
        style={{ boxShadow: `inset 0 0 25px ${getStateGlow()}` }}
      >
        <div className="relative flex items-center justify-center">
          {state === 'thinking' ? (
            <Zap className="w-10 h-10 text-cyan-300 animate-bounce" />
          ) : state === 'executing' ? (
            <Activity className="w-10 h-10 text-amber-300 animate-spin" />
          ) : (
            <Mic className="w-10 h-10 text-cyan-400 group-hover:text-cyan-200 transition-colors" />
          )}
        </div>

        <span className="font-hud text-xs font-bold tracking-widest mt-2 uppercase text-cyan-300">
          {state}
        </span>
      </div>

      {/* Voice Visualizer Waveform */}
      <div className="mt-6 w-full max-w-xs">
        <VoiceVisualizer 
          isActive={state === 'listening' || state === 'thinking'} 
          color={getWaveColor()} 
        />
      </div>

      {/* Core Status Message */}
      <div className="mt-4 text-center max-w-sm">
        <div className="flex items-center justify-center space-x-2 text-cyan-400 font-hud text-sm tracking-wider">
          <Cpu className="w-4 h-4 animate-pulse" />
          <span>JARVIS CORE KERNEL</span>
        </div>
        <p className="text-slate-400 text-xs mt-1 font-medium tracking-wide">
          {statusMessage || 'All autonomous subsystems active and listening.'}
        </p>
      </div>
    </div>
  );
};
