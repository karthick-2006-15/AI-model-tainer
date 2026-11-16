import React, { useState, useEffect, useRef } from 'react';
import { AgentStateType, AvatarThemeType, AvatarSizeType } from '../types/hud';

interface Props {
  state?: AgentStateType;
  theme?: AvatarThemeType;
  size?: AvatarSizeType;
  statusMessage?: string;
  audioAmplitude?: number; // 0.0 - 1.0 for lip-sync
  interactive?: boolean;
  onClick?: () => void;
  showScanlines?: boolean;
}

export const JarvisAvatar: React.FC<Props> = ({
  state = 'idle',
  theme = 'classic_cyan',
  size = 'medium',
  audioAmplitude = 0.0,
  interactive = true,
  onClick,
  showScanlines = true,
}) => {
  // Gaze tracking
  const [gaze, setGaze] = useState({ x: 0, y: 0 });
  const [isBlinking, setIsBlinking] = useState(false);
  const [headTilt, setHeadTilt] = useState({ x: 0, y: 0, z: 0 });
  const [smoothAmp, setSmoothAmp] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const animFrameRef = useRef<number | null>(null);

  // Smooth audio amplitude lerp for organic lip-sync
  useEffect(() => {
    let target = audioAmplitude;
    // If speaking but amplitude is not passed, simulate subtle speech rhythm
    if (state === 'speaking' && audioAmplitude <= 0.05) {
      target = 0.35 + Math.sin(Date.now() / 90) * 0.3 + Math.sin(Date.now() / 170) * 0.2;
      target = Math.max(0.1, Math.min(0.9, target));
    }

    const lerpSpeed = 0.35;
    const update = () => {
      setSmoothAmp((prev) => {
        const next = prev + (target - prev) * lerpSpeed;
        return Math.abs(next - target) < 0.01 ? target : next;
      });
      animFrameRef.current = requestAnimationFrame(update);
    };
    animFrameRef.current = requestAnimationFrame(update);
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [audioAmplitude, state]);

  // Natural organic blinking loop
  useEffect(() => {
    let blinkTimeout: number;
    const triggerBlink = () => {
      if (state !== 'sleeping') {
        setIsBlinking(true);
        setTimeout(() => setIsBlinking(false), 160);
      }
      const nextDelay = 2800 + Math.random() * 3200;
      blinkTimeout = window.setTimeout(triggerBlink, nextDelay);
    };
    blinkTimeout = window.setTimeout(triggerBlink, 3000);
    return () => clearTimeout(blinkTimeout);
  }, [state]);

  // Head tilt based on state
  useEffect(() => {
    switch (state) {
      case 'listening':
        setHeadTilt({ x: -4, y: 0, z: 0 });
        break;
      case 'thinking':
        setHeadTilt({ x: 2, y: 4, z: -3.5 });
        break;
      case 'confused':
        setHeadTilt({ x: -2, y: -4, z: 5 });
        break;
      case 'speaking':
        setHeadTilt({ x: -1, y: 0, z: 0 });
        break;
      case 'happy':
      case 'success':
        setHeadTilt({ x: -3, y: 0, z: 1.5 });
        break;
      case 'sleeping':
        setHeadTilt({ x: 6, y: 0, z: 0 });
        break;
      case 'error':
        setHeadTilt({ x: 3, y: 0, z: -2 });
        break;
      default:
        setHeadTilt({ x: 0, y: 0, z: 0 });
    }
  }, [state]);

  // Mouse cursor gaze tracking
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current || state === 'sleeping') return;
    const rect = containerRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const deltaX = (e.clientX - centerX) / (rect.width / 2);
    const deltaY = (e.clientY - centerY) / (rect.height / 2);
    setGaze({
      x: Math.max(-1, Math.min(1, deltaX)) * 5,
      y: Math.max(-1, Math.min(1, deltaY)) * 4,
    });
  };

  const handleMouseLeave = () => {
    setGaze({ x: 0, y: 0 });
  };

  // Color theme definitions
  const getThemePalette = () => {
    // State overrides for critical signals
    if (state === 'error') {
      return {
        primary: '#ef4444',
        secondary: '#dc2626',
        glow: 'rgba(239, 68, 68, 0.65)',
        text: 'text-rose-400',
        border: 'border-rose-500/50',
      };
    }
    if (state === 'warning' || state === 'executing') {
      return {
        primary: '#f59e0b',
        secondary: '#d97706',
        glow: 'rgba(245, 158, 11, 0.65)',
        text: 'text-amber-400',
        border: 'border-amber-500/50',
      };
    }
    if (state === 'listening' || state === 'happy' || state === 'success') {
      return {
        primary: '#10b981',
        secondary: '#059669',
        glow: 'rgba(16, 185, 129, 0.65)',
        text: 'text-emerald-400',
        border: 'border-emerald-500/50',
      };
    }

    switch (theme) {
      case 'arc_gold':
        return {
          primary: '#fbbf24',
          secondary: '#b45309',
          glow: 'rgba(251, 191, 36, 0.6)',
          text: 'text-amber-300',
          border: 'border-amber-500/40',
        };
      case 'quantum_violet':
        return {
          primary: '#c084fc',
          secondary: '#7e22ce',
          glow: 'rgba(192, 132, 252, 0.6)',
          text: 'text-purple-300',
          border: 'border-purple-500/40',
        };
      case 'matrix_emerald':
        return {
          primary: '#34d399',
          secondary: '#047857',
          glow: 'rgba(52, 211, 153, 0.6)',
          text: 'text-emerald-300',
          border: 'border-emerald-500/40',
        };
      case 'classic_cyan':
      default:
        return {
          primary: '#22d3ee',
          secondary: '#0284c7',
          glow: 'rgba(34, 211, 238, 0.6)',
          text: 'text-cyan-300',
          border: 'border-cyan-500/40',
        };
    }
  };

  const palette = getThemePalette();

  // Pixel scaling
  const dim = size === 'small' ? 180 : size === 'large' ? 320 : 250;

  // Eyebrow and eyelid angles calculated per state
  let eyebrowLeftY1 = 80;
  let eyebrowLeftY2 = 82;
  let eyebrowRightY1 = 82;
  let eyebrowRightY2 = 80;

  if (state === 'thinking') {
    eyebrowLeftY1 = 86;
    eyebrowRightY2 = 86;
  } else if (state === 'confused') {
    eyebrowLeftY1 = 73; // raised left eyebrow
    eyebrowLeftY2 = 76;
    eyebrowRightY1 = 86; // furrowed right
    eyebrowRightY2 = 84;
  } else if (state === 'happy' || state === 'success') {
    eyebrowLeftY1 = 76;
    eyebrowLeftY2 = 78;
    eyebrowRightY1 = 78;
    eyebrowRightY2 = 76;
  } else if (state === 'error') {
    eyebrowLeftY1 = 88;
    eyebrowRightY2 = 88;
  }

  // Eyelid heights (blinking vs open vs sleeping)
  const isSleeping = state === 'sleeping';
  const eyelidCoverHeight = isSleeping ? 18 : isBlinking ? 22 : 0;
  const mouthOpenAmount = (state === 'speaking' ? smoothAmp : 0.05) * 22;

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={interactive ? onClick : undefined}
      style={{
        width: dim,
        height: dim,
        perspective: '900px',
      }}
      className={`relative select-none flex flex-col items-center justify-center ${
        interactive ? 'cursor-pointer group' : ''
      }`}
    >
      {/* Outer Holographic Reticles & Orbit Ring */}
      <div
        className="absolute inset-0 rounded-full pointer-events-none transition-all duration-700"
        style={{
          boxShadow: `0 0 35px ${palette.glow}`,
          border: `1px dashed ${palette.primary}40`,
        }}
      >
        {/* Orbital HUD Rotation Ring */}
        <div
          className={`w-full h-full rounded-full border border-t-2 border-dashed ${
            state === 'thinking' ? 'animate-spin' : 'animate-spin-slow'
          }`}
          style={{ borderColor: `${palette.primary}40`, borderTopColor: palette.primary }}
        />
      </div>

      {/* 3D Perspective Head Shell */}
      <div
        className="w-full h-full flex items-center justify-center transition-transform duration-300 ease-out"
        style={{
          transform: `rotateX(${headTilt.x}deg) rotateY(${headTilt.y}deg) rotateZ(${headTilt.z}deg)`,
        }}
      >
        <svg
          viewBox="0 0 250 250"
          className="w-full h-full overflow-visible drop-shadow-[0_0_12px_rgba(0,0,0,0.8)]"
        >
          <defs>
            {/* Holographic linear gradient */}
            <linearGradient id="holoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={palette.primary} stopOpacity="0.9" />
              <stop offset="100%" stopColor={palette.secondary} stopOpacity="0.4" />
            </linearGradient>

            {/* Eye iris radial glow */}
            <radialGradient id="irisGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
              <stop offset="40%" stopColor={palette.primary} stopOpacity="0.8" />
              <stop offset="100%" stopColor={palette.secondary} stopOpacity="0.1" />
            </radialGradient>

            {/* Cranial grid pattern */}
            <pattern id="circuitGrid" width="10" height="10" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="10" y2="0" stroke={palette.primary} strokeOpacity="0.08" strokeWidth="0.5" />
              <line x1="0" y1="0" x2="0" y2="10" stroke={palette.primary} strokeOpacity="0.08" strokeWidth="0.5" />
            </pattern>
          </defs>

          {/* Cranial Background Plate with Grid */}
          <path
            d="M 60,70 Q 125,25 190,70 L 195,145 Q 185,210 125,225 Q 65,210 55,145 Z"
            fill="#030816"
            fillOpacity="0.85"
            stroke={palette.primary}
            strokeWidth="1.2"
            strokeOpacity="0.5"
          />
          <path
            d="M 60,70 Q 125,25 190,70 L 195,145 Q 185,210 125,225 Q 65,210 55,145 Z"
            fill="url(#circuitGrid)"
          />

          {/* Cybernetic Forehead Crest & Matrix Data Trace */}
          <path
            d="M 95,48 L 125,38 L 155,48"
            fill="none"
            stroke={palette.primary}
            strokeWidth="2"
            strokeLinecap="round"
          />
          <circle cx="125" cy="50" r="2.5" fill={palette.primary} className="animate-pulse" />
          <line x1="125" y1="52" x2="125" y2="65" stroke={palette.primary} strokeWidth="1" strokeDasharray="2 2" />

          {/* Temporal Cyber Ear Accents */}
          <path
            d="M 48,110 L 54,105 L 54,135 L 48,130 Z"
            fill={palette.secondary}
            fillOpacity="0.4"
            stroke={palette.primary}
            strokeWidth="1"
          />
          <path
            d="M 202,110 L 196,105 L 196,135 L 202,130 Z"
            fill={palette.secondary}
            fillOpacity="0.4"
            stroke={palette.primary}
            strokeWidth="1"
          />

          {/* Cheek Contour Lines & Nodes */}
          <path
            d="M 65,145 Q 75,175 105,190"
            fill="none"
            stroke={palette.primary}
            strokeWidth="1"
            strokeOpacity="0.4"
          />
          <circle cx="105" cy="190" r="1.5" fill={palette.primary} />

          <path
            d="M 185,145 Q 175,175 145,190"
            fill="none"
            stroke={palette.primary}
            strokeWidth="1"
            strokeOpacity="0.4"
          />
          <circle cx="145" cy="190" r="1.5" fill={palette.primary} />

          {/* ========================================================= */}
          {/* LEFT EYE COMPLEX */}
          {/* ========================================================= */}
          <g transform={`translate(${gaze.x * 0.4}, ${gaze.y * 0.4})`}>
            {/* Left Eyebrow */}
            <path
              d={`M 72,${eyebrowLeftY1} Q 92,${eyebrowLeftY1 - 5} 112,${eyebrowLeftY2}`}
              fill="none"
              stroke={palette.primary}
              strokeWidth="2.5"
              strokeLinecap="round"
              className="transition-all duration-300"
            />

            {/* Left Eye Socket Outer Tech Reticle */}
            <ellipse
              cx="92"
              cy="108"
              rx="20"
              ry="12"
              fill="#020612"
              stroke={palette.primary}
              strokeWidth="1.2"
              strokeOpacity="0.7"
            />

            {/* Left Iris Glow Core (Tracks Gaze) */}
            <circle
              cx={92 + gaze.x}
              cy={108 + gaze.y}
              r={state === 'thinking' ? 7.5 : 9}
              fill="url(#irisGlow)"
              className="transition-all duration-150"
            />

            {/* Left Pupil Center */}
            <circle
              cx={92 + gaze.x}
              cy={108 + gaze.y}
              r={state === 'listening' ? 4.5 : 3.2}
              fill="#ffffff"
            />

            {/* Left Eye Tech Reticle / Crosshair */}
            <line
              x1={92 + gaze.x - 11}
              y1={108 + gaze.y}
              x2={92 + gaze.x + 11}
              y2={108 + gaze.y}
              stroke={palette.primary}
              strokeWidth="0.6"
              strokeOpacity="0.5"
            />

            {/* Left Eyelid Mask (Blinking & Sleeping) */}
            <rect
              x="70"
              y="94"
              width="44"
              height={eyelidCoverHeight}
              fill="#030816"
              stroke={palette.primary}
              strokeWidth="0.8"
              className="transition-all duration-100 ease-out"
            />
          </g>

          {/* ========================================================= */}
          {/* RIGHT EYE COMPLEX */}
          {/* ========================================================= */}
          <g transform={`translate(${gaze.x * 0.4}, ${gaze.y * 0.4})`}>
            {/* Right Eyebrow */}
            <path
              d={`M 138,${eyebrowRightY1} Q 158,${eyebrowRightY1 - 5} 178,${eyebrowRightY2}`}
              fill="none"
              stroke={palette.primary}
              strokeWidth="2.5"
              strokeLinecap="round"
              className="transition-all duration-300"
            />

            {/* Right Eye Socket Outer Tech Reticle */}
            <ellipse
              cx="158"
              cy="108"
              rx="20"
              ry="12"
              fill="#020612"
              stroke={palette.primary}
              strokeWidth="1.2"
              strokeOpacity="0.7"
            />

            {/* Right Iris Glow Core (Tracks Gaze) */}
            <circle
              cx={158 + gaze.x}
              cy={108 + gaze.y}
              r={state === 'thinking' ? 7.5 : 9}
              fill="url(#irisGlow)"
              className="transition-all duration-150"
            />

            {/* Right Pupil Center */}
            <circle
              cx={158 + gaze.x}
              cy={108 + gaze.y}
              r={state === 'listening' ? 4.5 : 3.2}
              fill="#ffffff"
            />

            {/* Right Eye Tech Reticle / Crosshair */}
            <line
              x1={158 + gaze.x - 11}
              y1={108 + gaze.y}
              x2={158 + gaze.x + 11}
              y2={108 + gaze.y}
              stroke={palette.primary}
              strokeWidth="0.6"
              strokeOpacity="0.5"
            />

            {/* Right Eyelid Mask (Blinking & Sleeping) */}
            <rect
              x="136"
              y="94"
              width="44"
              height={eyelidCoverHeight}
              fill="#030816"
              stroke={palette.primary}
              strokeWidth="0.8"
              className="transition-all duration-100 ease-out"
            />
          </g>

          {/* Nose Bridge Tech Node */}
          <line x1="125" y1="115" x2="125" y2="135" stroke={palette.primary} strokeWidth="1" strokeOpacity="0.3" />
          <circle cx="125" cy="135" r="1.5" fill={palette.primary} strokeOpacity="0.5" />

          {/* ========================================================= */}
          {/* DYNAMIC LIP-SYNC MOUTH & EQUALIZER JAW */}
          {/* ========================================================= */}
          <g transform="translate(0, 5)">
            {/* Upper Lip Curve */}
            <path
              d={`M 98,162 Q 125,${162 - (state === 'happy' ? 4 : 1)} 152,162`}
              fill="none"
              stroke={palette.primary}
              strokeWidth="2"
              strokeLinecap="round"
            />

            {/* Audio Waveform Equalizer in Mouth Gap when Speaking */}
            {state === 'speaking' && mouthOpenAmount > 2 ? (
              <g>
                {/* Visualizer audio bars dancing between lips */}
                {[-18, -12, -6, 0, 6, 12, 18].map((offset, i) => {
                  const h = Math.max(3, (mouthOpenAmount * 0.7) * (0.6 + Math.sin(i * 1.5 + Date.now() / 100) * 0.4));
                  return (
                    <line
                      key={i}
                      x1={125 + offset}
                      y1={164 - h / 2}
                      x2={125 + offset}
                      y2={164 + h / 2}
                      stroke={palette.primary}
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  );
                })}
              </g>
            ) : null}

            {/* Lower Lip Curve with Dynamic Drop */}
            <path
              d={`M 102,${166 + mouthOpenAmount} Q 125,${168 + mouthOpenAmount * 1.2 + (state === 'happy' ? -2 : 0)} 148,${166 + mouthOpenAmount}`}
              fill="none"
              stroke={palette.primary}
              strokeWidth="2"
              strokeLinecap="round"
              className="transition-all duration-75"
            />

            {/* Chin Anchor Node & Vent */}
            <line x1="118" y1="195" x2="132" y2="195" stroke={palette.primary} strokeWidth="1.2" strokeOpacity="0.5" />
          </g>

          {/* Holographic Laser Scanline */}
          {showScanlines && (
            <line
              x1="55"
              y1="40"
              x2="195"
              y2="40"
              stroke={palette.primary}
              strokeWidth="1.5"
              strokeOpacity="0.7"
              className="animate-scanline pointer-events-none"
            />
          )}
        </svg>
      </div>

      {/* Floating State Badge Under Avatar */}
      <div className="absolute -bottom-2 flex items-center space-x-1.5 px-3 py-0.5 rounded-full bg-[#040e21]/90 border border-cyan-500/30 backdrop-blur-md shadow-lg pointer-events-none">
        <span
          className="w-2 h-2 rounded-full animate-ping"
          style={{ backgroundColor: palette.primary }}
        />
        <span className={`font-hud font-bold text-[10px] tracking-widest uppercase ${palette.text}`}>
          {state}
        </span>
      </div>
    </div>
  );
};
