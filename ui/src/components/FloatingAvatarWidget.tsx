import React, { useState, useEffect, useRef } from 'react';
import { JarvisAvatar } from './JarvisAvatar';
import { AgentStateType, AvatarThemeType, AvatarSizeType } from '../types/hud';
import { Maximize2, Mic, MicOff, Volume2, VolumeX, Palette, X, Move } from 'lucide-react';

interface Props {
  state: AgentStateType;
  statusMessage?: string;
  theme?: AvatarThemeType;
  size?: AvatarSizeType;
  audioAmplitude?: number;
  voiceOutputEnabled?: boolean;
  isListening?: boolean;
  onExpandDashboard: () => void;
  onToggleMic: () => void;
  onToggleMute: () => void;
  onChangeTheme?: (theme: AvatarThemeType) => void;
  onChangeSize?: (size: AvatarSizeType) => void;
  onClose?: () => void;
}

export const FloatingAvatarWidget: React.FC<Props> = ({
  state,
  statusMessage = 'STANDING BY',
  theme = 'classic_cyan',
  size = 'small',
  audioAmplitude = 0.0,
  voiceOutputEnabled = true,
  isListening = false,
  onExpandDashboard,
  onToggleMic,
  onToggleMute,
  onChangeTheme,
  onChangeSize,
  onClose,
}) => {
  // Draggable coordinate state with localStorage persistence
  const [pos, setPos] = useState(() => {
    try {
      const saved = localStorage.getItem('jarvis_avatar_coords');
      if (saved) return JSON.parse(saved);
    } catch (_) {}
    return { x: window.innerWidth - 240, y: window.innerHeight - 260 };
  });

  const [isDragging, setIsDragging] = useState(false);
  const [showControls, setShowControls] = useState(false);
  const dragStartRef = useRef<{ startX: number; startY: number; origX: number; origY: number }>({
    startX: 0,
    startY: 0,
    origX: 0,
    origY: 0,
  });

  // Save coordinates on drag finish
  const handleMouseDown = (e: React.MouseEvent) => {
    // Only drag when holding drag handle or primary avatar body, not inner buttons
    if ((e.target as HTMLElement).closest('button')) return;
    setIsDragging(true);
    dragStartRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      origX: pos.x,
      origY: pos.y,
    };
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const dx = e.clientX - dragStartRef.current.startX;
      const dy = e.clientY - dragStartRef.current.startY;
      const newX = Math.max(10, Math.min(window.innerWidth - 200, dragStartRef.current.origX + dx));
      const newY = Math.max(10, Math.min(window.innerHeight - 200, dragStartRef.current.origY + dy));
      setPos({ x: newX, y: newY });
    };

    const handleMouseUp = () => {
      if (isDragging) {
        setIsDragging(false);
        try {
          localStorage.setItem('jarvis_avatar_coords', JSON.stringify(pos));
        } catch (_) {}
      }
    };

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, pos]);

  const cycleTheme = () => {
    if (!onChangeTheme) return;
    const themes: AvatarThemeType[] = ['classic_cyan', 'arc_gold', 'quantum_violet', 'matrix_emerald'];
    const nextIdx = (themes.indexOf(theme) + 1) % themes.length;
    onChangeTheme(themes[nextIdx]);
  };

  const cycleSize = () => {
    if (!onChangeSize) return;
    const sizes: AvatarSizeType[] = ['small', 'medium', 'large'];
    const nextIdx = (sizes.indexOf(size) + 1) % sizes.length;
    onChangeSize(sizes[nextIdx]);
  };

  return (
    <div
      style={{
        position: 'fixed',
        left: `${pos.x}px`,
        top: `${pos.y}px`,
        zIndex: 99999,
      }}
      onMouseEnter={() => setShowControls(true)}
      onMouseLeave={() => setShowControls(false)}
      className="group relative select-none flex flex-col items-center"
    >
      {/* Draggable Header Handle & Quick Actions */}
      <div
        onMouseDown={handleMouseDown}
        className={`flex items-center justify-between w-full px-2 py-1 mb-1 rounded-t-lg bg-[#040e21]/90 border border-cyan-500/30 backdrop-blur-md transition-opacity duration-200 cursor-grab active:cursor-grabbing ${
          showControls ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
      >
        <div className="flex items-center space-x-1.5 text-cyan-400">
          <Move className="w-3 h-3" />
          <span className="text-[10px] font-hud font-bold tracking-wider">JARVIS</span>
        </div>

        <div className="flex items-center space-x-1">
          {/* Theme Switcher */}
          <button
            onClick={cycleTheme}
            title="Cycle Theme"
            className="p-1 text-slate-400 hover:text-cyan-300 transition"
          >
            <Palette className="w-3 h-3" />
          </button>

          {/* Size Switcher */}
          <button
            onClick={cycleSize}
            title={`Scale: ${size.toUpperCase()}`}
            className="p-1 text-slate-400 hover:text-cyan-300 transition text-[9px] font-mono"
          >
            {size[0].toUpperCase()}
          </button>

          {/* Voice Output Toggle */}
          <button
            onClick={onToggleMute}
            title={voiceOutputEnabled ? 'Mute Speech' : 'Unmute Speech'}
            className="p-1 text-slate-400 hover:text-cyan-300 transition"
          >
            {voiceOutputEnabled ? <Volume2 className="w-3 h-3 text-emerald-400" /> : <VolumeX className="w-3 h-3 text-rose-400" />}
          </button>

          {/* Expand to Full Dashboard Button */}
          <button
            onClick={onExpandDashboard}
            title="Expand Full Dashboard"
            className="p-1 text-slate-400 hover:text-cyan-300 transition"
          >
            <Maximize2 className="w-3 h-3" />
          </button>

          {/* Close/Minimize */}
          {onClose && (
            <button
              onClick={onClose}
              title="Hide Widget"
              className="p-1 text-slate-400 hover:text-rose-400 transition"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Main Animated AI Face (Clicking opens dashboard) */}
      <div className="relative">
        <JarvisAvatar
          state={state}
          theme={theme}
          size={size}
          statusMessage={statusMessage}
          audioAmplitude={audioAmplitude}
          interactive={true}
          onClick={onExpandDashboard}
        />

        {/* Quick Mic Action Hover Pill */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleMic();
          }}
          title={isListening ? 'Listening (Click to Stop)' : 'Click to Speak'}
          className={`absolute bottom-3 right-3 p-2 rounded-full border shadow-lg backdrop-blur-md transition-all duration-200 ${
            isListening
              ? 'bg-emerald-500 text-white border-emerald-300 animate-pulse'
              : 'bg-[#040e21]/90 text-cyan-400 border-cyan-500/40 hover:scale-110 hover:border-cyan-300'
          }`}
        >
          {isListening ? <Mic className="w-3.5 h-3.5" /> : <MicOff className="w-3.5 h-3.5 text-slate-400" />}
        </button>
      </div>
    </div>
  );
};
