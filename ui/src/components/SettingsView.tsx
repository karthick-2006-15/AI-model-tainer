import React, { useState } from 'react';
import { Settings, Palette, Eye, Sliders, Monitor, CheckCircle2, RotateCcw, Shield, Sparkles } from 'lucide-react';
import { AvatarThemeType, AvatarSizeType } from '../types/hud';

interface Props {
  currentTheme: AvatarThemeType;
  onChangeTheme: (theme: AvatarThemeType) => void;
  currentSize: AvatarSizeType;
  onChangeSize: (size: AvatarSizeType) => void;
  glowIntensity: number;
  onChangeGlow: (val: number) => void;
  scanlinesEnabled: boolean;
  onToggleScanlines: () => void;
  onToggleFloatingMode: () => void;
  isFloatingMode: boolean;
}

export const SettingsView: React.FC<Props> = ({
  currentTheme,
  onChangeTheme,
  currentSize,
  onChangeSize,
  glowIntensity,
  onChangeGlow,
  scanlinesEnabled,
  onToggleScanlines,
  onToggleFloatingMode,
  isFloatingMode,
}) => {
  const [autostartEnabled, setAutostartEnabled] = useState(true);
  const [clickThrough, setClickThrough] = useState(false);
  const [saveNote, setSaveNote] = useState('');

  const themes: { id: AvatarThemeType; label: string; desc: string; color: string; border: string }[] = [
    { id: 'classic_cyan', label: 'Classic Cyan', desc: 'Futuristic Mark VII holographic signature', color: 'bg-cyan-400', border: 'border-cyan-400' },
    { id: 'arc_gold', label: 'Arc Gold', desc: 'Warm vibranium reactor aesthetic', color: 'bg-amber-400', border: 'border-amber-400' },
    { id: 'quantum_violet', label: 'Quantum Violet', desc: 'Deep cosmic intelligence neural aura', color: 'bg-purple-400', border: 'border-purple-400' },
    { id: 'matrix_emerald', label: 'Matrix Emerald', desc: 'Cybernetic tactical listening matrix', color: 'bg-emerald-400', border: 'border-emerald-400' },
  ];

  const sizes: { id: AvatarSizeType; label: string; px: string }[] = [
    { id: 'small', label: 'Compact Widget', px: '180px' },
    { id: 'medium', label: 'Standard Desktop', px: '240px' },
    { id: 'large', label: 'Command HUD', px: '320px' },
  ];

  const handleResetCoordinates = () => {
    localStorage.removeItem('jarvis_avatar_coords');
    setSaveNote('Widget screen coordinates reset to default bottom-right position.');
    setTimeout(() => setSaveNote(''), 3000);
  };

  return (
    <div className="h-full flex flex-col space-y-6 overflow-y-auto pr-1">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-cyan-500/20 pb-4">
        <div>
          <h2 className="font-hud font-bold text-lg text-cyan-300 tracking-wider flex items-center gap-2">
            <Settings className="w-5 h-5 text-cyan-400" />
            AVATAR & SYSTEM CONFIGURATION
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Configure animated AI face visual identity, floating widget behavior, and system parameters
          </p>
        </div>

        <button
          onClick={onToggleFloatingMode}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-xs font-hud font-bold tracking-wider transition ${
            isFloatingMode
              ? 'bg-cyan-500 text-black border-cyan-300'
              : 'bg-[#08152e] text-cyan-300 border-cyan-700/50 hover:border-cyan-400'
          }`}
        >
          <Monitor className="w-4 h-4" />
          <span>{isFloatingMode ? 'EXIT FLOATING WIDGET' : 'LAUNCH FLOATING WIDGET'}</span>
        </button>
      </div>

      {saveNote && (
        <div className="p-3 rounded-lg bg-cyan-950/70 border border-cyan-500/40 text-xs text-cyan-300 font-mono">
          {saveNote}
        </div>
      )}

      {/* Grid: Visual Appearance & System Settings */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Column: Visual Theme & Avatar Face Customization */}
        <div className="col-span-12 lg:col-span-7 space-y-6 bg-[#040e21]/70 border border-cyan-500/20 rounded-xl p-5 backdrop-blur-sm">
          <div>
            <div className="flex items-center space-x-2 text-xs font-hud text-cyan-300 mb-3">
              <Palette className="w-4 h-4 text-cyan-400" />
              <span>HOLOGRAPHIC COLOR THEME MATRIX</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {themes.map((t) => (
                <button
                  key={t.id}
                  onClick={() => onChangeTheme(t.id)}
                  className={`p-3 rounded-lg text-left border transition ${
                    currentTheme === t.id
                      ? `bg-cyan-950/80 ${t.border} text-white shadow-[0_0_12px_rgba(6,182,212,0.25)]`
                      : 'bg-[#030816] border-cyan-900/30 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center space-x-2 font-hud text-xs font-bold text-slate-200">
                      <span className={`w-3 h-3 rounded-full ${t.color}`}></span>
                      <span>{t.label}</span>
                    </div>
                    {currentTheme === t.id && <CheckCircle2 className="w-4 h-4 text-cyan-400" />}
                  </div>
                  <p className="text-[11px] text-slate-400">{t.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Size Scaling */}
          <div className="pt-4 border-t border-cyan-500/10">
            <div className="flex items-center space-x-2 text-xs font-hud text-cyan-300 mb-3">
              <Eye className="w-4 h-4 text-cyan-400" />
              <span>AVATAR SCALING & PROPORTIONS</span>
            </div>

            <div className="grid grid-cols-3 gap-3">
              {sizes.map((s) => (
                <button
                  key={s.id}
                  onClick={() => onChangeSize(s.id)}
                  className={`p-3 rounded-lg text-center border transition ${
                    currentSize === s.id
                      ? 'bg-cyan-950/80 border-cyan-400 text-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                      : 'bg-[#030816] border-cyan-900/30 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span className="text-xs font-hud font-bold block">{s.label}</span>
                  <span className="text-[10px] font-mono text-slate-500">{s.px}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Glow & Hologram Toggles */}
          <div className="pt-4 border-t border-cyan-500/10 space-y-4">
            <div>
              <div className="flex justify-between text-xs text-slate-300 mb-1">
                <span className="flex items-center gap-1.5 font-hud">
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                  Hologram Glow Intensity
                </span>
                <span className="font-mono text-cyan-300">{Math.round(glowIntensity * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.2"
                max="1.0"
                step="0.05"
                value={glowIntensity}
                onChange={(e) => onChangeGlow(parseFloat(e.target.value))}
                className="w-full accent-cyan-400 cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-[#030816] border border-cyan-900/30">
              <div>
                <span className="text-xs font-semibold text-slate-200 block">Holographic Laser Scanline</span>
                <span className="text-[11px] text-slate-400">Renders animated top-down cybernetic scanning beam</span>
              </div>
              <button
                onClick={onToggleScanlines}
                className={`w-11 h-6 rounded-full transition-colors p-1 ${
                  scanlinesEnabled ? 'bg-cyan-500' : 'bg-slate-700'
                }`}
              >
                <div
                  className={`w-4 h-4 rounded-full bg-white transition-transform ${
                    scanlinesEnabled ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Floating Window Behavior & Windows Boot */}
        <div className="col-span-12 lg:col-span-5 space-y-6 bg-[#040e21]/70 border border-cyan-500/20 rounded-xl p-5 backdrop-blur-sm">
          <div>
            <div className="flex items-center space-x-2 text-xs font-hud text-cyan-300 mb-3">
              <Sliders className="w-4 h-4 text-cyan-400" />
              <span>DESKTOP FLOATING WIDGET BEHAVIOR</span>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-[#030816] border border-cyan-900/30">
                <div>
                  <span className="text-xs font-semibold text-slate-200 block">Always-On-Top Window</span>
                  <span className="text-[11px] text-slate-400">Floats on top of Chrome, WhatsApp, VS Code</span>
                </div>
                <span className="text-emerald-400 text-xs font-mono">HWND_TOPMOST</span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-[#030816] border border-cyan-900/30">
                <div>
                  <span className="text-xs font-semibold text-slate-200 block">Click-Through Transparency</span>
                  <span className="text-[11px] text-slate-400">Pass clicks through to underlying apps</span>
                </div>
                <button
                  onClick={() => setClickThrough(!clickThrough)}
                  className={`w-11 h-6 rounded-full transition-colors p-1 ${
                    clickThrough ? 'bg-cyan-500' : 'bg-slate-700'
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded-full bg-white transition-transform ${
                      clickThrough ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              <button
                onClick={handleResetCoordinates}
                className="w-full flex items-center justify-center space-x-2 py-2 rounded-lg bg-[#08152e] hover:bg-cyan-950 border border-cyan-700/40 text-cyan-300 text-xs font-semibold transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset Widget Screen Position</span>
              </button>
            </div>
          </div>

          {/* Windows Boot & Autostart */}
          <div className="pt-4 border-t border-cyan-500/10 space-y-3">
            <div className="flex items-center space-x-2 text-xs font-hud text-cyan-300 mb-1">
              <Shield className="w-4 h-4 text-emerald-400" />
              <span>WINDOWS 11 INTEGRATION</span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-[#030816] border border-cyan-900/30">
              <div>
                <span className="text-xs font-semibold text-slate-200 block">Start with Windows Boot</span>
                <span className="text-[11px] text-slate-400">Silent VBS background startup runner</span>
              </div>
              <button
                onClick={() => setAutostartEnabled(!autostartEnabled)}
                className={`w-11 h-6 rounded-full transition-colors p-1 ${
                  autostartEnabled ? 'bg-emerald-500' : 'bg-slate-700'
                }`}
              >
                <div
                  className={`w-4 h-4 rounded-full bg-white transition-transform ${
                    autostartEnabled ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            <div className="p-3 rounded-lg bg-[#030816] border border-cyan-900/30 text-[11px] space-y-1 text-slate-400 font-mono">
              <div className="text-cyan-300 font-bold">Autostart Configuration:</div>
              <div>• Runner: scripts/run_jarvis_silent.vbs</div>
              <div>• Setup: scripts/setup_windows_autostart.ps1</div>
              <div>• Desktop Widget: scripts/run_floating_avatar.py</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
