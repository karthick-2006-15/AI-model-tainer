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
  size = 'medium',
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
  const isCompactWindow = window.innerWidth <= 480;

  // Draggable coordinate state with localStorage persistence
  const [pos, setPos] = useState(() => {
    if (window.innerWidth <= 480) return { x: 0, y: 0 };
    try {
      const saved = localStorage.getItem('jarvis_avatar_coords');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.x < window.innerWidth && parsed.y < window.innerHeight) {
          return parsed;
        }
      }
    } catch (_) {}
    return { x: Math.max(10, window.innerWidth - 300), y: Math.max(10, window.innerHeight - 340) };
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
    if (isCompactWindow) return; // In standalone popup window, OS handles window dragging
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
    if (isCompactWindow) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const dx = e.clientX - dragStartRef.current.startX;
      const dy = e.clientY - dragStartRef.current.startY;
      const newX = Math.max(10, Math.min(window.innerWidth - 260, dragStartRef.current.origX + dx));
      const newY = Math.max(10, Math.min(window.innerHeight - 260, dragStartRef.current.origY + dy));
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
  }, [isDragging, pos, isCompactWindow]);

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

  const controlsVisible = isCompactWindow || showControls;

  const containerStyle: React.CSSProperties = isCompactWindow
    ? {
        position: 'relative',
        width: '100vw',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '8px',
        background: 'transparent',
      }
    : {
        position: 'fixed',
        left: `${pos.x}px`,
        top: `${pos.y}px`,
        zIndex: 99999,
      };

  return (
    <div
      style={containerStyle}
      onMouseEnter={() => setShowControls(true)}
      onMouseLeave={() => setShowControls(false)}
      className="group relative select-none flex flex-col items-center"
    >
      {/* Draggable Header Handle & Quick Actions */}
      <div
        onMouseDown={handleMouseDown}
        className={`flex items-center justify-between w-full max-w-[280px] px-3 py-1.5 mb-1 rounded-xl bg-[#040e21]/95 border border-cyan-500/40 backdrop-blur-md shadow-lg transition-opacity duration-200 ${
          isCompactWindow ? 'cursor-default' : 'cursor-grab active:cursor-grabbing'
        } ${controlsVisible ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
      >
        <div className="flex items-center space-x-1.5 text-cyan-400">
          <Move className="w-3 h-3" />
          <span className="text-[10px] font-hud font-bold tracking-wider">JARVIS // AVATAR</span>
        </div>

        <div className="flex items-center space-x-1.5">
          {/* Theme Switcher */}
          <button
            onClick={cycleTheme}
            title="Cycle Theme (Cyan, Gold, Violet, Emerald)"
            className="p-1 text-slate-400 hover:text-cyan-300 transition"
          >
            <Palette className="w-3.5 h-3.5" />
          </button>

          {/* Size Switcher */}
          <button
            onClick={cycleSize}
            title={`Scale: ${size.toUpperCase()}`}
            className="px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-700/50 text-cyan-300 hover:text-white transition text-[9px] font-mono font-bold"
          >
            {size[0].toUpperCase()}
          </button>

          {/* Voice Output Toggle */}
          <button
            onClick={onToggleMute}
            title={voiceOutputEnabled ? 'Mute Speech' : 'Unmute Speech'}
            className="p-1 text-slate-400 hover:text-cyan-300 transition"
          >
            {voiceOutputEnabled ? <Volume2 className="w-3.5 h-3.5 text-emerald-400" /> : <VolumeX className="w-3.5 h-3.5 text-rose-400" />}
          </button>

          {/* Expand to Full Dashboard Button */}
          <button
            onClick={onExpandDashboard}
            title="Expand Full Dashboard"
            className="p-1 text-slate-400 hover:text-cyan-300 transition"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>

          {/* Close/Minimize */}
          {onClose && (
            <button
              onClick={onClose}
              title="Hide Widget"
              className="p-1 text-slate-400 hover:text-rose-400 transition"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Main Animated AI Face (Clicking opens dashboard) */}
      <div className="relative flex items-center justify-center my-auto">
        <JarvisAvatar
          state={state}
          theme={theme}
          size={isCompactWindow ? 'small' : size}
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
          className={`absolute -bottom-1 -right-2 p-2 rounded-full border shadow-xl backdrop-blur-md transition-all duration-200 ${
            isListening
              ? 'bg-emerald-500 text-white border-emerald-300 animate-pulse'
              : 'bg-[#040e21]/95 text-cyan-400 border-cyan-500/50 hover:scale-110 hover:border-cyan-300 hover:shadow-cyan-500/50'
          }`}
        >
          {isListening ? <Mic className="w-3.5 h-3.5" /> : <MicOff className="w-3.5 h-3.5 text-slate-400" />}
        </button>
      </div>
    </div>
  );
};
