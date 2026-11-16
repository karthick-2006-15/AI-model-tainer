import React from 'react';
import { 
  ShieldAlert, 
  Brain, 
  Monitor, 
  Settings, 
  Terminal, 
  Mic,
  Activity,
  Sparkles
} from 'lucide-react';

interface Props {
  activeTab: string;
  onSelectTab: (tab: string) => void;
  onEmergencyStop: () => void;
  mobileConnected?: boolean;
}

export const Sidebar: React.FC<Props> = ({ 
  activeTab, 
  onSelectTab, 
  onEmergencyStop,
  mobileConnected = false
}) => {
  const navItems = [
    { id: 'hud', label: 'Main Avatar & HUD', icon: Sparkles },
    { id: 'voice', label: 'Voice Interface', icon: Mic },
    { id: 'tasks', label: 'Task Management', icon: Terminal },
    { id: 'computer', label: 'Computer Intelligence', icon: Monitor },
    { id: 'memory', label: 'Personal Intelligence', icon: Brain },
    { id: 'telemetry', label: 'System Monitoring', icon: Activity },
    { id: 'settings', label: 'Settings & Config', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-[#040e21] border-r border-cyan-500/20 flex flex-col justify-between p-4 h-full">
      <div className="space-y-6">
        {/* Brand Header */}
        <div className="flex items-center space-x-3 px-2 pt-2">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/30">
            <span className="font-hud text-lg font-black text-white">J</span>
          </div>
          <div>
            <h1 className="font-hud font-extrabold text-base tracking-wider text-cyan-300">JARVIS</h1>
            <span className="text-[9px] text-slate-400 font-mono tracking-widest block -mt-1">
              AI OPERATING SYSTEM
            </span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                  isActive
                    ? 'bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Status & Emergency Abort */}
      <div className="space-y-3 pt-4 border-t border-cyan-900/40">
        {/* Device Badges */}
        <div className="space-y-1.5 px-2">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-400">Windows Host</span>
            <span className="text-emerald-400 font-mono flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Active
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-400">Android Mobile</span>
            <span className={`font-mono flex items-center gap-1 ${mobileConnected ? 'text-emerald-400' : 'text-slate-500'}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${mobileConnected ? 'bg-emerald-400' : 'bg-slate-600'}`}></span>
              {mobileConnected ? 'Paired' : 'Standby'}
            </span>
          </div>
        </div>

        {/* Emergency Stop Button */}
        <button
          onClick={onEmergencyStop}
          className="w-full bg-rose-950/60 hover:bg-rose-900 border border-rose-700/60 text-rose-300 py-2.5 px-3 rounded-lg text-xs font-hud font-bold tracking-wider flex items-center justify-center space-x-2 transition shadow-md hover:shadow-rose-900/50"
        >
          <ShieldAlert className="w-4 h-4 text-rose-400" />
          <span>EMERGENCY ABORT</span>
        </button>
      </div>
    </aside>
  );
};
