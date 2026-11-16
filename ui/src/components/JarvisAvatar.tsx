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
  statusMessage,
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
      target = 0.38 + Math.sin(Date.now() / 85) * 0.32 + Math.sin(Date.now() / 160) * 0.22;
      target = Math.max(0.1, Math.min(0.95, target));
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
      const nextDelay = 2600 + Math.random() * 3400;
      blinkTimeout = window.setTimeout(triggerBlink, nextDelay);
    };
    blinkTimeout = window.setTimeout(triggerBlink, 3000);
    return () => clearTimeout(blinkTimeout);
  }, [state]);

  // Head tilt based on cognitive state
  useEffect(() => {
    switch (state) {
      case 'listening':
        setHeadTilt({ x: -4, y: 0, z: 0 });
        break;
      case 'thinking':
        setHeadTilt({ x: 2, y: 5, z: -4 });
        break;
      case 'confused':
        setHeadTilt({ x: -2, y: -4, z: 5.5 });
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
      x: Math.max(-1, Math.min(1, deltaX)) * 6.0,
      y: Math.max(-1, Math.min(1, deltaY)) * 4.5,
    });
  };

  const handleMouseLeave = () => {
    setGaze({ x: 0, y: 0 });
  };

  // Color theme definitions with high-tech sci-fi glows
  const getThemePalette = () => {
    if (state === 'error') {
      return {
        primary: '#ef4444',
        secondary: '#991b1b',
        glow: 'rgba(239, 68, 68, 0.75)',
        text: 'text-rose-400',
        border: 'border-rose-500/50',
      };
    }
    if (state === 'warning' || state === 'executing') {
      return {
        primary: '#f59e0b',
        secondary: '#b45309',
        glow: 'rgba(245, 158, 11, 0.7)',
        text: 'text-amber-400',
        border: 'border-amber-500/50',
      };
    }
    if (state === 'listening' || state === 'happy' || state === 'success') {
      return {
        primary: '#10b981',
        secondary: '#047857',
        glow: 'rgba(16, 185, 129, 0.75)',
        text: 'text-emerald-400',
        border: 'border-emerald-500/50',
      };
    }

    switch (theme) {
      case 'arc_gold':
        return {
          primary: '#fbbf24',
          secondary: '#b45309',
          glow: 'rgba(251, 191, 36, 0.7)',
          text: 'text-amber-300',
          border: 'border-amber-500/40',
        };
      case 'quantum_violet':
        return {
          primary: '#c084fc',
          secondary: '#7e22ce',
          glow: 'rgba(192, 132, 252, 0.7)',
          text: 'text-purple-300',
          border: 'border-purple-500/40',
        };
      case 'matrix_emerald':
        return {
          primary: '#34d399',
          secondary: '#047857',
          glow: 'rgba(52, 211, 153, 0.7)',
          text: 'text-emerald-300',
          border: 'border-emerald-500/40',
        };
      case 'classic_cyan':
      default:
        return {
          primary: '#00f3ff',
          secondary: '#0284c7',
          glow: 'rgba(0, 243, 255, 0.7)',
          text: 'text-cyan-300',
          border: 'border-cyan-500/40',
        };
    }
  };

  const palette = getThemePalette();

  // Pixel scaling
  const dim = size === 'small' ? 220 : size === 'large' ? 340 : 275;

  // Eyebrow and eyelid angles calculated per state
  let eyebrowLeftY1 = 98;
  let eyebrowLeftY2 = 101;
  let eyebrowRightY1 = 101;
  let eyebrowRightY2 = 98;

  if (state === 'thinking') {
    eyebrowLeftY1 = 105;
    eyebrowRightY2 = 105;
  } else if (state === 'confused') {
    eyebrowLeftY1 = 89; // raised left eyebrow
    eyebrowLeftY2 = 93;
    eyebrowRightY1 = 106; // furrowed right
    eyebrowRightY2 = 103;
  } else if (state === 'happy' || state === 'success') {
    eyebrowLeftY1 = 93;
    eyebrowLeftY2 = 96;
    eyebrowRightY1 = 96;
    eyebrowRightY2 = 93;
  } else if (state === 'error') {
    eyebrowLeftY1 = 108;
    eyebrowRightY2 = 108;
  }

  // Eyelid heights (blinking vs open vs sleeping)
  const isSleeping = state === 'sleeping';
  const eyelidCoverHeight = isSleeping ? 24 : isBlinking ? 28 : 0;
  const mouthOpenAmount = (state === 'speaking' ? smoothAmp : 0.05) * 24;

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
      {/* Outer Holographic Reticles & Dynamic Orbit Ring */}
      <div
        className="absolute inset-0 rounded-full pointer-events-none transition-all duration-700"
        style={{
          boxShadow: `0 0 38px ${palette.glow}`,
          border: `1px dashed ${palette.primary}30`,
        }}
      >
        {/* Outer Tachymeter Dial */}
        <div
          className={`w-full h-full rounded-full border border-t-2 border-dashed ${
            state === 'thinking' ? 'animate-spin' : 'animate-spin-slow'
          }`}
          style={{ borderColor: `${palette.primary}35`, borderTopColor: palette.primary }}
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
          viewBox="0 0 300 300"
          className="w-full h-full overflow-visible drop-shadow-[0_0_15px_rgba(0,0,0,0.9)]"
        >
          <defs>
            {/* Holographic Glow Filter */}
            <filter id="avatarGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="2.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Holographic Linear Gradient */}
            <linearGradient id="cyberGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={palette.primary} stopOpacity="0.95" />
              <stop offset="50%" stopColor={palette.secondary} stopOpacity="0.75" />
              <stop offset="100%" stopColor="#0284c7" stopOpacity="0.3" />
            </linearGradient>

            {/* Eye Iris Radial Glow */}
            <radialGradient id="irisCoreGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
              <stop offset="35%" stopColor={palette.primary} stopOpacity="0.9" />
              <stop offset="75%" stopColor={palette.secondary} stopOpacity="0.4" />
              <stop offset="100%" stopColor="#000000" stopOpacity="0" />
            </radialGradient>

            {/* Microscopic Cyber Circuit Grid */}
            <pattern id="avatarGrid" width="12" height="12" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="12" y2="0" stroke={palette.primary} strokeOpacity="0.08" strokeWidth="0.6" />
              <line x1="0" y1="0" x2="0" y2="12" stroke={palette.primary} strokeOpacity="0.08" strokeWidth="0.6" />
            </pattern>
          </defs>

          {/* ========================================================= */}
          {/* 1. HUD TARGETING BRACKETS & CARDINAL COMPASS READOUTS */}
          {/* ========================================================= */}
          <g className="pointer-events-none" opacity="0.65">
            {/* 4 Corner Framing Brackets [ + ] */}
            <path d="M 18,36 L 18,18 L 36,18" fill="none" stroke={palette.primary} strokeWidth="1.5" />
            <path d="M 282,36 L 282,18 L 264,18" fill="none" stroke={palette.primary} strokeWidth="1.5" />
            <path d="M 18,264 L 18,282 L 36,282" fill="none" stroke={palette.primary} strokeWidth="1.5" />
            <path d="M 282,264 L 282,282 L 264,282" fill="none" stroke={palette.primary} strokeWidth="1.5" />

            {/* Coordinate Axis Rings */}
            <circle cx="150" cy="150" r="140" fill="none" stroke={palette.primary} strokeWidth="0.8" strokeDasharray="4 6" opacity="0.4" />
            <circle cx="150" cy="150" r="132" fill="none" stroke={palette.primary} strokeWidth="1" strokeDasharray="80 20 40 10" opacity="0.6" />

            {/* Degree Markings */}
            <text x="150" y="14" fill={palette.primary} fontSize="7" fontFamily="monospace" textAnchor="middle" opacity="0.8">000°</text>
            <text x="294" y="152" fill={palette.primary} fontSize="7" fontFamily="monospace" textAnchor="middle" opacity="0.8">090°</text>
            <text x="150" y="295" fill={palette.primary} fontSize="7" fontFamily="monospace" textAnchor="middle" opacity="0.8">180°</text>
            <text x="6" y="152" fill={palette.primary} fontSize="7" fontFamily="monospace" textAnchor="middle" opacity="0.8">270°</text>

            {/* Telemetry Labels */}
            <text x="24" y="32" fill={palette.primary} fontSize="7" fontFamily="monospace" letterSpacing="1">SYS.AI // MARK_VII</text>
            <text x="276" y="32" fill={palette.primary} fontSize="7" fontFamily="monospace" letterSpacing="1" textAnchor="end">BIOMETRIC_MATRIX</text>
          </g>

          {/* ========================================================= */}
          {/* 2. CRANIAL BASE PLATE & POLYGONAL FACET MESH */}
          {/* ========================================================= */}
          {/* Dark Glass Cranial Silhouette */}
          <path
            d="M 75,85 Q 150,30 225,85 L 232,175 Q 220,250 150,268 Q 80,250 68,175 Z"
            fill="#030816"
            fillOpacity="0.88"
            stroke={palette.primary}
            strokeWidth="1.4"
            strokeOpacity="0.7"
            filter="url(#avatarGlow)"
          />
          {/* Circuit Texture Fill */}
          <path
            d="M 75,85 Q 150,30 225,85 L 232,175 Q 220,250 150,268 Q 80,250 68,175 Z"
            fill="url(#avatarGrid)"
          />

          {/* Wireframe Polygonal Facial Contours (Cheekbones, Jaw, Brow) */}
          <g stroke={palette.primary} strokeWidth="0.8" strokeOpacity="0.45" fill="none">
            {/* Cranial Forehead Triangles */}
            <polygon points="150,45 110,75 150,85" />
            <polygon points="150,45 190,75 150,85" />
            <line x1="110" y1="75" x2="68" y2="105" />
            <line x1="190" y1="75" x2="232" y2="105" />

            {/* Temple Circuit Traces */}
            <path d="M 60,135 L 68,125 L 68,165 L 60,155 Z" fill={palette.secondary} fillOpacity="0.3" strokeWidth="1" />
            <path d="M 240,135 L 232,125 L 232,165 L 240,155 Z" fill={palette.secondary} fillOpacity="0.3" strokeWidth="1" />

            {/* Zygomatic Cheekbone Facets */}
            <polygon points="105,150 78,185 125,205 150,175" />
            <polygon points="195,150 222,185 175,205 150,175" />

            {/* Jawline & Mandible Connectors */}
            <line x1="125" y1="205" x2="115" y2="238" />
            <line x1="175" y1="205" x2="185" y2="238" />
            <line x1="115" y1="238" x2="150" y2="262" />
            <line x1="185" y1="238" x2="150" y2="262" />
          </g>

          {/* Wireframe Nodes / Vertices */}
          <g fill={palette.primary} filter="url(#avatarGlow)">
            <circle cx="150" cy="45" r="2.5" />
            <circle cx="110" cy="75" r="2" />
            <circle cx="190" cy="75" r="2" />
            <circle cx="150" cy="85" r="2" />
            <circle cx="78" cy="185" r="2" />
            <circle cx="222" cy="185" r="2" />
            <circle cx="125" cy="205" r="2" />
            <circle cx="175" cy="205" r="2" />
            <circle cx="150" cy="262" r="2.5" />
          </g>

          {/* Forehead Central Matrix Data Trace */}
          <line x1="150" y1="52" x2="150" y2="78" stroke={palette.primary} strokeWidth="1.2" strokeDasharray="3 2" />
          <circle cx="150" cy="65" r="1.5" fill="#ffffff" className="animate-ping" />

          {/* ========================================================= */}
          {/* 3. HIGH-PRECISION CYBERNETIC LEFT EYE COMPLEX */}
          {/* ========================================================= */}
          <g transform={`translate(${gaze.x * 0.4}, ${gaze.y * 0.4})`}>
            {/* Left Eyebrow Vector */}
            <path
              d={`M 82,${eyebrowLeftY1} Q 106,${eyebrowLeftY1 - 6} 130,${eyebrowLeftY2}`}
              fill="none"
              stroke={palette.primary}
              strokeWidth="2.8"
              strokeLinecap="round"
              filter="url(#avatarGlow)"
              className="transition-all duration-300"
            />

            {/* Left Eye Hexagonal Outer Socket */}
            <polygon
              points="84,124 94,110 118,110 128,124 118,138 94,138"
              fill="#020612"
              stroke={palette.primary}
              strokeWidth="1.4"
              strokeOpacity="0.8"
            />

            {/* Left Rotating Iris Tech Reticle */}
            <circle
              cx="106"
              cy="124"
              r="15"
              fill="none"
              stroke={palette.primary}
              strokeWidth="0.8"
              strokeDasharray="4 2"
              className={state === 'thinking' ? 'animate-spin' : 'animate-spin-slow'}
              style={{ transformOrigin: '106px 124px' }}
            />

            {/* Left Iris Glow Core (Tracks Gaze) */}
            <circle
              cx={106 + gaze.x}
              cy={124 + gaze.y}
              r={state === 'listening' ? 11 : 9.5}
              fill="url(#irisCoreGlow)"
              className="transition-all duration-150"
            />

            {/* Left Pupil Optic Center */}
            <circle
              cx={106 + gaze.x}
              cy={124 + gaze.y}
              r={state === 'listening' ? 5.0 : state === 'thinking' ? 3.0 : 3.8}
              fill="#ffffff"
            />

            {/* Left Crosshair Reticle Lines */}
            <line
              x1={106 + gaze.x - 14}
              y1={124 + gaze.y}
              x2={106 + gaze.x + 14}
              y2={124 + gaze.y}
              stroke={palette.primary}
              strokeWidth="0.6"
              strokeOpacity="0.6"
            />
            <line
              x1={106 + gaze.x}
              y1={124 + gaze.y - 14}
              x2={106 + gaze.x}
              y2={124 + gaze.y + 14}
              stroke={palette.primary}
              strokeWidth="0.6"
              strokeOpacity="0.6"
            />

            {/* Left Eyelid Shutter Mask (Blinking & Sleeping) */}
            <rect
              x="80"
              y="108"
              width="52"
              height={eyelidCoverHeight}
              fill="#030816"
              stroke={palette.primary}
              strokeWidth="1"
              className="transition-all duration-100 ease-out"
            />
          </g>

          {/* ========================================================= */}
          {/* 4. HIGH-PRECISION CYBERNETIC RIGHT EYE COMPLEX */}
          {/* ========================================================= */}
          <g transform={`translate(${gaze.x * 0.4}, ${gaze.y * 0.4})`}>
            {/* Right Eyebrow Vector */}
            <path
              d={`M 170,${eyebrowRightY1} Q 194,${eyebrowRightY1 - 6} 218,${eyebrowRightY2}`}
              fill="none"
              stroke={palette.primary}
              strokeWidth="2.8"
              strokeLinecap="round"
              filter="url(#avatarGlow)"
              className="transition-all duration-300"
            />

            {/* Right Eye Hexagonal Outer Socket */}
            <polygon
              points="172,124 182,110 206,110 216,124 206,138 182,138"
              fill="#020612"
              stroke={palette.primary}
              strokeWidth="1.4"
              strokeOpacity="0.8"
            />

            {/* Right Rotating Iris Tech Reticle */}
            <circle
              cx="194"
              cy="124"
              r="15"
              fill="none"
              stroke={palette.primary}
              strokeWidth="0.8"
              strokeDasharray="4 2"
              className={state === 'thinking' ? 'animate-spin' : 'animate-spin-slow'}
              style={{ transformOrigin: '194px 124px' }}
            />

            {/* Right Iris Glow Core (Tracks Gaze) */}
            <circle
              cx={194 + gaze.x}
              cy={124 + gaze.y}
              r={state === 'listening' ? 11 : 9.5}
              fill="url(#irisCoreGlow)"
              className="transition-all duration-150"
            />

            {/* Right Pupil Optic Center */}
            <circle
              cx={194 + gaze.x}
              cy={124 + gaze.y}
              r={state === 'listening' ? 5.0 : state === 'thinking' ? 3.0 : 3.8}
              fill="#ffffff"
            />

            {/* Right Crosshair Reticle Lines */}
            <line
              x1={194 + gaze.x - 14}
              y1={124 + gaze.y}
              x2={194 + gaze.x + 14}
              y2={124 + gaze.y}
              stroke={palette.primary}
              strokeWidth="0.6"
              strokeOpacity="0.6"
            />
            <line
              x1={194 + gaze.x}
              y1={124 + gaze.y - 14}
              x2={194 + gaze.x}
              y2={124 + gaze.y + 14}
              stroke={palette.primary}
              strokeWidth="0.6"
              strokeOpacity="0.6"
            />

            {/* Right Eyelid Shutter Mask (Blinking & Sleeping) */}
            <rect
              x="168"
              y="108"
              width="52"
              height={eyelidCoverHeight}
              fill="#030816"
              stroke={palette.primary}
              strokeWidth="1"
              className="transition-all duration-100 ease-out"
            />
          </g>

          {/* Central Nose Bridge Tech Traces */}
          <line x1="150" y1="130" x2="150" y2="155" stroke={palette.primary} strokeWidth="1.2" strokeOpacity="0.5" />
          <polygon points="150,140 144,152 156,152" fill="none" stroke={palette.primary} strokeWidth="0.8" strokeOpacity="0.6" />

          {/* ========================================================= */}
          {/* 5. DYNAMIC VOCALIZER & MULTI-BAR EQUALIZER MOUTH */}
          {/* ========================================================= */}
          <g transform="translate(0, 8)">
            {/* Upper Cybernetic Lip Arch */}
            <path
              d={`M 118,188 Q 150,${188 - (state === 'happy' ? 5 : 1)} 182,188`}
              fill="none"
              stroke={palette.primary}
              strokeWidth="2.4"
              strokeLinecap="round"
              filter="url(#avatarGlow)"
            />

            {/* 9-Bar Harmonic Frequency Equalizer Ribbon (Active During Speech) */}
            {state === 'speaking' && mouthOpenAmount > 2.5 ? (
              <g>
                {[-24, -18, -12, -6, 0, 6, 12, 18, 24].map((offset, i) => {
                  const barH = Math.max(
                    3.5,
                    (mouthOpenAmount * 0.75) * (0.55 + Math.sin(i * 1.35 + Date.now() / 90) * 0.45)
                  );
                  return (
                    <line
                      key={i}
                      x1={150 + offset}
                      y1={190 - barH / 2}
                      x2={150 + offset}
                      y2={190 + barH / 2}
                      stroke={palette.primary}
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      filter="url(#avatarGlow)"
                    />
                  );
                })}
              </g>
            ) : null}

            {/* Lower Cybernetic Lip Arch with Dynamic Drop */}
            <path
              d={`M 122,${192 + mouthOpenAmount} Q 150,${194 + mouthOpenAmount * 1.25 + (state === 'happy' ? -2.5 : 0)} 178,${192 + mouthOpenAmount}`}
              fill="none"
              stroke={palette.primary}
              strokeWidth="2.4"
              strokeLinecap="round"
              filter="url(#avatarGlow)"
              className="transition-all duration-75"
            />

            {/* Mandible Vent & Power Coupling */}
            <line x1="140" y1="228" x2="160" y2="228" stroke={palette.primary} strokeWidth="1.5" strokeOpacity="0.6" />
            <line x1="144" y1="233" x2="156" y2="233" stroke={palette.primary} strokeWidth="1.2" strokeOpacity="0.4" />
          </g>

          {/* ========================================================= */}
          {/* 6. HOLOGRAPHIC LASER SCANLINE */}
          {/* ========================================================= */}
          {showScanlines && (
            <line
              x1="65"
              y1="40"
              x2="235"
              y2="40"
              stroke={palette.primary}
              strokeWidth="2"
              strokeOpacity="0.8"
              filter="url(#avatarGlow)"
              className="animate-scanline pointer-events-none"
            />
          )}
        </svg>
      </div>

      {/* Floating State Badge Under Avatar */}
      <div
        title={statusMessage || state}
        className="absolute -bottom-2 flex items-center space-x-1.5 px-3 py-0.5 rounded-full bg-[#040e21]/95 border border-cyan-500/40 backdrop-blur-md shadow-xl pointer-events-none"
      >
        <span
          className="w-2 h-2 rounded-full animate-ping"
          style={{ backgroundColor: palette.primary }}
        />
        <span className={`font-hud font-bold text-[10px] tracking-widest uppercase ${palette.text}`}>
          {statusMessage && statusMessage !== 'STANDING BY' ? (statusMessage.length > 24 ? statusMessage.slice(0, 24) + '...' : statusMessage) : state}
        </span>
      </div>
    </div>
  );
};
