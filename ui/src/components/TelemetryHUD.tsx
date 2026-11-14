import React from 'react';
import { TelemetryData } from '../types/hud';
import { Cpu, HardDrive, Battery, Layers } from 'lucide-react';

interface Props {
  telemetry: TelemetryData | null;
}

export const TelemetryHUD: React.FC<Props> = ({ telemetry }) => {
  if (!telemetry) {
    return (
      <div className="bg-[#081226]/80 border border-cyan-500/20 rounded-xl p-4 text-center text-cyan-400 font-hud text-xs animate-pulse">
        CONNECTING TO TELEMETRY STREAM...
      </div>
    );
  }

  const { cpu, ram, disk, battery, process_count, platform, os_release } = telemetry;

  return (
    <div className="bg-[#081226]/80 border border-cyan-500/30 rounded-xl p-5 backdrop-blur-md hud-glow flex flex-col space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
        <div className="flex items-center space-x-2 text-cyan-400 font-hud text-xs tracking-wider">
          <Layers className="w-4 h-4 text-cyan-300" />
          <span>SYSTEM TELEMETRY</span>
        </div>
        <span className="text-[10px] text-slate-400 font-mono bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
          {platform} {os_release}
        </span>
      </div>

      {/* Grid of Gauges */}
      <div className="grid grid-cols-2 gap-4">
        {/* CPU Load */}
        <div className="bg-[#040e21] border border-cyan-900/50 rounded-lg p-3 flex flex-col">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="flex items-center space-x-1.5">
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              <span>CPU Load</span>
            </span>
            <span className="font-hud font-bold text-cyan-300">{cpu.percent}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden mt-1">
            <div 
              className="bg-gradient-to-r from-cyan-500 to-blue-500 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(cpu.percent, 100)}%` }}
            ></div>
          </div>
          <span className="text-[10px] text-slate-500 mt-1.5">{cpu.cores} Cores Active</span>
        </div>

        {/* RAM Usage */}
        <div className="bg-[#040e21] border border-cyan-900/50 rounded-lg p-3 flex flex-col">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="flex items-center space-x-1.5">
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              <span>Memory</span>
            </span>
            <span className="font-hud font-bold text-indigo-300">{ram.percent}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden mt-1">
            <div 
              className="bg-gradient-to-r from-indigo-500 to-cyan-400 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(ram.percent, 100)}%` }}
            ></div>
          </div>
          <span className="text-[10px] text-slate-500 mt-1.5">{ram.used_gb} / {ram.total_gb} GB</span>
        </div>

        {/* Disk Storage */}
        <div className="bg-[#040e21] border border-cyan-900/50 rounded-lg p-3 flex flex-col">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="flex items-center space-x-1.5">
              <HardDrive className="w-3.5 h-3.5 text-emerald-400" />
              <span>Storage (C:)</span>
            </span>
            <span className="font-hud font-bold text-emerald-300">{disk.percent}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden mt-1">
            <div 
              className="bg-gradient-to-r from-emerald-500 to-cyan-400 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(disk.percent, 100)}%` }}
            ></div>
          </div>
          <span className="text-[10px] text-slate-500 mt-1.5">{disk.used_gb} / {disk.total_gb} GB</span>
        </div>

        {/* Battery / Processes */}
        <div className="bg-[#040e21] border border-cyan-900/50 rounded-lg p-3 flex flex-col">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="flex items-center space-x-1.5">
              <Battery className="w-3.5 h-3.5 text-amber-400" />
              <span>Battery</span>
            </span>
            <span className="font-hud font-bold text-amber-300">
              {battery?.percent !== null && battery?.percent !== undefined ? `${battery.percent}%` : 'AC Line'}
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden mt-1">
            <div 
              className="bg-gradient-to-r from-amber-500 to-yellow-300 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${battery?.percent ?? 100}%` }}
            ></div>
          </div>
          <span className="text-[10px] text-slate-500 mt-1.5">{process_count} Active OS Tasks</span>
        </div>
      </div>
    </div>
  );
};
