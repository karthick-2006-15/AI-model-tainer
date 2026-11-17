import React, { useState, useEffect, useRef } from 'react';
import { AgentStateType, AvatarThemeType, AvatarSizeType } from '../types/hud';

interface Props {
  state: AgentStateType;
  theme?: AvatarThemeType;
  size?: AvatarSizeType;
  statusMessage?: string;
  audioAmplitude?: number;
  showScanlines?: boolean;
  interactive?: boolean;
  isMusicPlaying?: boolean;
  onClick?: () => void;
}

export const JarvisAvatar: React.FC<Props> = ({
  state,
  theme = 'classic_cyan',
  size = 'medium',
  statusMessage = 'STANDING BY',
  audioAmplitude = 0.0,
  showScanlines = true,
  interactive = true,
  isMusicPlaying = false,
  onClick,
}) => {
  // Eye gaze direction tracking with damped lerping
  const [gaze, setGaze] = useState({ x: 0, y: 0 });
  const [headTilt, setHeadTilt] = useState({ x: 0, y: 0, z: 0 });
  const [isBlinking, setIsBlinking] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Filtered audio amplitude
  const [smoothAmp, setSmoothAmp] = useState(0.0);

  // Smooth audio amplitude decay
  useEffect(() => {
    let animId: number;
    const updateAmp = () => {
      setSmoothAmp((prev) => {
        const target = audioAmplitude || 0;
        const diff = target - prev;
        return prev + diff * 0.35;
      });
      animId = requestAnimationFrame(updateAmp);
    };
    animId = requestAnimationFrame(updateAmp);
    return () => cancelAnimationFrame(animId);
  }, [audioAmplitude]);

  // Autonomous Natural Blinking cycle (every 3.5 - 6 seconds)
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const triggerBlink = () => {
      setIsBlinking(true);
      setTimeout(() => {
        setIsBlinking(false);
        const nextInterval = 3200 + Math.random() * 3000;
        timer = setTimeout(triggerBlink, nextInterval);
      }, 160);
    };

    const initialInterval = 2500 + Math.random() * 2000;
    timer = setTimeout(triggerBlink, initialInterval);
    return () => clearTimeout(timer);
  }, []);

  // Idle Micro-Saccade eye movements (slight autonomous ocular scanning)
  useEffect(() => {
    const saccadeInterval = setInterval(() => {
      if (state === 'idle' || state === 'listening') {
        const randomX = (Math.random() - 0.5) * 4.5;
        const randomY = (Math.random() - 0.5) * 3.0;
        setGaze((prev) => ({
          x: prev.x * 0.7 + randomX * 0.3,
          y: prev.y * 0.7 + randomY * 0.3,
        }));
      }
    }, 1800);
    return () => clearInterval(saccadeInterval);
  }, [state]);

  // Interactive mouse gaze & 3D head parallax
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const normX = Math.max(-1, Math.min(1, (e.clientX - centerX) / (rect.width / 2)));
    const normY = Math.max(-1, Math.min(1, (e.clientY - centerY) / (rect.height / 2)));

    setGaze({
      x: normX * 8.5,
      y: normY * 6.5,
    });

    setHeadTilt({
      x: -normY * 9.0,
      y: normX * 11.0,
      z: normX * normY * 3.0,
    });
  };

  const handleMouseLeave = () => {
    setGaze({ x: 0, y: 0 });
    setHeadTilt({ x: 0, y: 0, z: 0 });
  };

  // Color schemes for futuristic Hologram HUD
  const getThemePalette = () => {
    switch (theme) {
      case 'arc_gold':
        return {
          primary: '#fbbf24',
          secondary: '#b45309',
          tertiary: '#78350f',
          glow: 'rgba(251, 191, 36, 0.75)',
          text: 'text-amber-300',
          border: 'border-amber-500/40',
          bgTint: 'rgba(251, 191, 36, 0.04)',
        };
      case 'quantum_violet':
        return {
          primary: '#c084fc',
          secondary: '#7e22ce',
          tertiary: '#4c1d95',
          glow: 'rgba(192, 132, 252, 0.75)',
          text: 'text-purple-300',
          border: 'border-purple-500/40',
          bgTint: 'rgba(192, 132, 252, 0.04)',
        };
      case 'matrix_emerald':
        return {
          primary: '#34d399',
          secondary: '#059669',
          tertiary: '#064e3b',
          glow: 'rgba(52, 211, 153, 0.75)',
          text: 'text-emerald-300',
          border: 'border-emerald-500/40',
          bgTint: 'rgba(52, 211, 153, 0.04)',
        };
      case 'classic_cyan':
      default:
        return {
          primary: '#00f3ff',
          secondary: '#0284c7',
          tertiary: '#0369a1',
          glow: 'rgba(0, 243, 255, 0.75)',
          text: 'text-cyan-300',
          border: 'border-cyan-500/40',
          bgTint: 'rgba(0, 243, 255, 0.04)',
        };
    }
  };

  const palette = getThemePalette();

  // Pixel scaling
  const dim = size === 'small' ? 210 : size === 'large' ? 320 : 255;

  // Eyebrow and eyelid angles calculated per state
  let eyebrowLeftY1 = 98;
  let eyebrowLeftY2 = 101;
  let eyebrowRightY1 = 101;
  let eyebrowRightY2 = 98;

  if (state === 'thinking') {
    eyebrowLeftY1 = 104;
    eyebrowRightY2 = 104;
  } else if (state === 'confused') {
    eyebrowLeftY1 = 90;
    eyebrowLeftY2 = 94;
    eyebrowRightY1 = 106;
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
      {/* Outer Holographic Reticles & Dynamic Orbit Ring */}
      <div
        className="absolute inset-0 rounded-full pointer-events-none transition-all duration-700"
        style={{
          boxShadow: `0 0 32px ${palette.glow}`,
          border: `1px dashed ${palette.primary}25`,
        }}
      >
        {/* Outer Tachymeter Dial */}
        <div
          className={`w-full h-full rounded-full border border-t-2 border-dashed ${
            state === 'thinking' ? 'animate-spin' : 'animate-spin-slow'
          }`}
          style={{ borderColor: `${palette.primary}30`, borderTopColor: palette.primary }}
        />
      </div>

      {/* 3D Perspective Head Shell */}
      <div
        className={`w-full h-full flex items-center justify-center transition-transform duration-300 ease-out ${
          isMusicPlaying ? 'animate-music-groove' : ''
        }`}
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
            <filter id="avatarGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="2.2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Subtle Node Bloom Filter */}
            <filter id="nodeBloom" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3.0" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Holographic Linear Gradient */}
            <linearGradient id="cyberGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={palette.primary} stopOpacity="0.95" />
              <stop offset="50%" stopColor={palette.secondary} stopOpacity="0.75" />
              <stop offset="100%" stopColor={palette.tertiary} stopOpacity="0.3" />
            </linearGradient>

            {/* Cranial Face Fill Gradient */}
            <radialGradient id="cranialGradient" cx="50%" cy="45%" r="60%">
              <stop offset="0%" stopColor="#040f26" stopOpacity="0.95" />
              <stop offset="70%" stopColor="#020713" stopOpacity="0.98" />
              <stop offset="100%" stopColor="#000206" stopOpacity="1" />
            </radialGradient>

            {/* Eye Iris Radial Glow */}
            <radialGradient id="irisCoreGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
              <stop offset="35%" stopColor={palette.primary} stopOpacity="0.95" />
              <stop offset="70%" stopColor={palette.secondary} stopOpacity="0.5" />
              <stop offset="100%" stopColor="#000000" stopOpacity="0" />
            </radialGradient>

            {/* Microscopic Cyber Circuit Grid */}
            <pattern id="avatarGrid" width="10" height="10" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="10" y2="0" stroke={palette.primary} strokeOpacity="0.07" strokeWidth="0.5" />
              <line x1="0" y1="0" x2="0" y2="10" stroke={palette.primary} strokeOpacity="0.07" strokeWidth="0.5" />
            </pattern>
          </defs>

          {/* ========================================================= */}
          {/* 1. HUD TARGETING BRACKETS & CARDINAL COMPASS READOUTS */}
          {/* ========================================================= */}
          <g className="pointer-events-none" opacity="0.75">
            {/* 4 Precision Corner Framing Brackets */}
            <path d="M 22,38 L 22,22 L 38,22" fill="none" stroke={palette.primary} strokeWidth="1.6" />
            <path d="M 278,38 L 278,22 L 262,22" fill="none" stroke={palette.primary} strokeWidth="1.6" />
            <path d="M 22,262 L 22,278 L 38,278" fill="none" stroke={palette.primary} strokeWidth="1.6" />
            <path d="M 278,262 L 278,278 L 262,278" fill="none" stroke={palette.primary} strokeWidth="1.6" />

            {/* Concentric Telemetry Rings */}
            <circle cx="150" cy="150" r="138" fill="none" stroke={palette.primary} strokeWidth="0.75" strokeDasharray="3 5" opacity="0.35" />
            <circle cx="150" cy="150" r="130" fill="none" stroke={palette.primary} strokeWidth="1.0" strokeDasharray="60 15 20 15" opacity="0.55" />
            <circle cx="150" cy="150" r="124" fill="none" stroke={palette.secondary} strokeWidth="0.6" strokeDasharray="2 8" opacity="0.4" />

            {/* Cardinal Degree Readouts */}
            <text x="150" y="16" fill={palette.primary} fontSize="6.5" fontFamily="monospace" textAnchor="middle" opacity="0.85">000° // NORTH</text>
            <text x="290" y="152" fill={palette.primary} fontSize="6.5" fontFamily="monospace" textAnchor="middle" opacity="0.85">090°</text>
            <text x="150" y="294" fill={palette.primary} fontSize="6.5" fontFamily="monospace" textAnchor="middle" opacity="0.85">180° // SOUTH</text>
            <text x="10" y="152" fill={palette.primary} fontSize="6.5" fontFamily="monospace" textAnchor="middle" opacity="0.85">270°</text>

            {/* Futuristic Top HUD Telemetry Tags */}
            <text x="26" y="34" fill={palette.primary} fontSize="6.5" fontFamily="monospace" letterSpacing="0.8">JARVIS // MK.VII</text>
            <text x="274" y="34" fill={palette.primary} fontSize="6.5" fontFamily="monospace" letterSpacing="0.8" textAnchor="end">BIOMETRIC_MATRIX</text>
          </g>

          {/* ========================================================= */}
          {/* 2. CRANIAL SCULPT & BIOMETRIC WIREFRAME MESH */}
          {/* ========================================================= */}
          {/* Dark Glass Cranial Silhouette */}
          <path
            d="M 75,82 Q 150,28 225,82 L 234,175 Q 222,250 150,268 Q 78,250 66,175 Z"
            fill="url(#cranialGradient)"
            stroke={palette.primary}
            strokeWidth="1.5"
            strokeOpacity="0.8"
            filter="url(#avatarGlow)"
          />

          {/* Micro-Circuit Texture Layer */}
          <path
            d="M 75,82 Q 150,28 225,82 L 234,175 Q 222,250 150,268 Q 78,250 66,175 Z"
            fill="url(#avatarGrid)"
          />

          {/* Wireframe Polygonal Facets (Sleek Geometric Planes) */}
          <g stroke={palette.primary} strokeWidth="0.75" strokeOpacity="0.45" fill="none">
            {/* Forehead Frontal Plate Facets */}
            <polygon points="150,42 112,74 150,84" fill={palette.primary} fillOpacity="0.04" />
            <polygon points="150,42 188,74 150,84" fill={palette.primary} fillOpacity="0.04" />
            <line x1="112" y1="74" x2="66" y2="102" />
            <line x1="188" y1="74" x2="234" y2="102" />
            <line x1="66" y1="102" x2="90" y2="106" />
            <line x1="234" y1="102" x2="210" y2="106" />

            {/* Temple Acoustic Couplings */}
            <path d="M 58,136 L 66,124 L 66,166 L 58,154 Z" fill={palette.secondary} fillOpacity="0.25" strokeWidth="0.9" />
            <path d="M 242,136 L 234,124 L 234,166 L 242,154 Z" fill={palette.secondary} fillOpacity="0.25" strokeWidth="0.9" />

            {/* Zygomatic Cheekbone Polygon Facets */}
            <polygon points="106,148 76,184 124,204 150,174" fill={palette.primary} fillOpacity="0.03" />
            <polygon points="194,148 224,184 176,204 150,174" fill={palette.primary} fillOpacity="0.03" />

            {/* Mandible & Chin Vector Struts */}
            <line x1="124" y1="204" x2="114" y2="236" />
            <line x1="176" y1="204" x2="186" y2="236" />
            <line x1="114" y1="236" x2="150" y2="262" />
            <line x1="186" y1="236" x2="150" y2="262" />
            <polygon points="135,246 165,246 150,262" fill={palette.primary} fillOpacity="0.08" />
          </g>

          {/* Luminous Neon Vertex Points */}
          <g fill={palette.primary} filter="url(#nodeBloom)">
            <circle cx="150" cy="42" r="2.2" />
            <circle cx="112" cy="74" r="1.8" />
            <circle cx="188" cy="74" r="1.8" />
            <circle cx="150" cy="84" r="2.0" />
            <circle cx="76" cy="184" r="1.8" />
            <circle cx="224" cy="184" r="1.8" />
            <circle cx="124" cy="204" r="1.8" />
            <circle cx="176" cy="204" r="1.8" />
            <circle cx="150" cy="262" r="2.2" />
          </g>

          {/* Forehead Central Core Uplink Line */}
          <line x1="150" y1="48" x2="150" y2="76" stroke={palette.primary} strokeWidth="1.2" strokeDasharray="3 2" />
          <circle cx="150" cy="62" r="1.5" fill="#ffffff" className="animate-ping" />

          {/* ========================================================= */}
          {/* 3. HIGH-PRECISION CYBERNETIC LEFT EYE COMPLEX */}
          {/* ========================================================= */}
          <g transform={`translate(${gaze.x * 0.4}, ${gaze.y * 0.4})`}>
            {/* Sleek Biometric Left Eyebrow Arc */}
            <path
              d={`M 84,${eyebrowLeftY1} Q 106,${eyebrowLeftY1 - 7} 128,${eyebrowLeftY2}`}
              fill="none"
              stroke={palette.primary}
              strokeWidth="2.4"
              strokeLinecap="round"
              filter="url(#avatarGlow)"
              className="transition-all duration-300"
            />
            {/* Subtle Eyebrow Accent Dash */}
            <line
              x1="92"
              y1={eyebrowLeftY1 - 4}
              x2="104"
              y2={eyebrowLeftY1 - 6}
              stroke={palette.primary}
              strokeWidth="1.0"
              strokeOpacity="0.6"
            />

            {/* Left Eye Hexagonal Socket Plate */}
            <polygon
              points="84,124 94,110 118,110 128,124 118,138 94,138"
              fill="#020612"
              stroke={palette.primary}
              strokeWidth="1.4"
              strokeOpacity="0.85"
            />

            {/* Left Rotating Iris Optical Reticle */}
            <circle
              cx="106"
              cy="124"
              r="14.5"
              fill="none"
              stroke={palette.primary}
              strokeWidth="0.8"
              strokeDasharray="4 2 2 2"
              className={state === 'thinking' ? 'animate-spin' : 'animate-spin-slow'}
              style={{ transformOrigin: '106px 124px' }}
            />

            {/* Left Iris Glow Core (Tracks Gaze) */}
            <circle
              cx={106 + gaze.x}
              cy={124 + gaze.y}
              r={state === 'listening' ? 10.5 : 9.0}
              fill="url(#irisCoreGlow)"
              className="transition-all duration-150"
            />

            {/* Left High-Intensity Optical Pupil */}
            <circle
              cx={106 + gaze.x}
              cy={124 + gaze.y}
              r={state === 'listening' ? 4.8 : state === 'thinking' ? 2.8 : 3.6}
              fill="#ffffff"
            />

            {/* Left Crosshair Reticle Lines */}
            <line
              x1={106 + gaze.x - 13}
              y1={124 + gaze.y}
              x2={106 + gaze.x + 13}
              y2={124 + gaze.y}
              stroke={palette.primary}
              strokeWidth="0.6"
              strokeOpacity="0.55"
            />
            <line
              x1={106 + gaze.x}
              y1={124 + gaze.y - 13}
              x2={106 + gaze.x}
              y2={124 + gaze.y + 13}
              stroke={palette.primary}
              strokeWidth="0.6"
              strokeOpacity="0.55"
            />

            {/* Left Eyelid Shutter Mask (Blinking & Sleeping) */}
            <rect
              x="82"
              y="108"
              width="48"
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
            {/* Sleek Biometric Right Eyebrow Arc */}
            <path
              d={`M 172,${eyebrowRightY1} Q 194,${eyebrowRightY1 - 7} 216,${eyebrowRightY2}`}
              fill="none"
              stroke={palette.primary}
              strokeWidth="2.4"
              strokeLinecap="round"
              filter="url(#avatarGlow)"
              className="transition-all duration-300"
            />
            {/* Subtle Eyebrow Accent Dash */}
            <line
              x1="196"
              y1={eyebrowRightY1 - 6}
              x2="208"
              y2={eyebrowRightY1 - 4}
              stroke={palette.primary}
              strokeWidth="1.0"
              strokeOpacity="0.6"
            />

            {/* Right Eye Hexagonal Socket Plate */}
            <polygon
              points="172,124 182,110 206,110 216,124 206,138 182,138"
              fill="#020612"
              stroke={palette.primary}
              strokeWidth="1.4"
              strokeOpacity="0.85"
            />

            {/* Right Rotating Iris Optical Reticle */}
            <circle
              cx="194"
              cy="124"
              r="14.5"
              fill="none"
              stroke={palette.primary}
              strokeWidth="0.8"
              strokeDasharray="4 2 2 2"
              className={state === 'thinking' ? 'animate-spin' : 'animate-spin-slow'}
              style={{ transformOrigin: '194px 124px' }}
            />

            {/* Right Iris Glow Core (Tracks Gaze) */}
            <circle
              cx={194 + gaze.x}
              cy={124 + gaze.y}
              r={state === 'listening' ? 10.5 : 9.0}
              fill="url(#irisCoreGlow)"
              className="transition-all duration-150"
            />

            {/* Right High-Intensity Optical Pupil */}
            <circle
              cx={194 + gaze.x}
              cy={124 + gaze.y}
              r={state === 'listening' ? 4.8 : state === 'thinking' ? 2.8 : 3.6}
              fill="#ffffff"
            />

            {/* Right Crosshair Reticle Lines */}
            <line
              x1={194 + gaze.x - 13}
              y1={124 + gaze.y}
              x2={194 + gaze.x + 13}
              y2={124 + gaze.y}
              stroke={palette.primary}
              strokeWidth="0.6"
              strokeOpacity="0.55"
            />
            <line
              x1={194 + gaze.x}
              y1={124 + gaze.y - 13}
              x2={194 + gaze.x}
              y2={124 + gaze.y + 13}
              stroke={palette.primary}
              strokeWidth="0.6"
              strokeOpacity="0.55"
            />

            {/* Right Eyelid Shutter Mask (Blinking & Sleeping) */}
            <rect
              x="170"
              y="108"
              width="48"
              height={eyelidCoverHeight}
              fill="#030816"
              stroke={palette.primary}
              strokeWidth="1"
              className="transition-all duration-100 ease-out"
            />
          </g>

          {/* Central Nose Bridge Tech Traces (Sleek Geometric Lines) */}
          <line x1="150" y1="126" x2="150" y2="154" stroke={palette.primary} strokeWidth="1.2" strokeOpacity="0.55" />
          <polygon points="150,138 143,152 157,152" fill="none" stroke={palette.primary} strokeWidth="0.9" strokeOpacity="0.65" />

          {/* ========================================================= */}
          {/* 5. DYNAMIC VOCALIZER & HARMONIC FREQUENCY EQUALIZER MOUTH */}
          {/* ========================================================= */}
          <g transform="translate(0, 8)">
            {/* Upper Cybernetic Lip Arch */}
            <path
              d={`M 118,188 Q 150,${188 - (state === 'happy' ? 5 : 1)} 182,188`}
              fill="none"
              stroke={palette.primary}
              strokeWidth="2.2"
              strokeLinecap="round"
              filter="url(#avatarGlow)"
            />

            {/* 9-Bar Harmonic Frequency Equalizer Ribbon (Active During Speech) */}
            {state === 'speaking' && mouthOpenAmount > 2.0 ? (
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
                      strokeWidth="2.0"
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
              strokeWidth="2.2"
              strokeLinecap="round"
              filter="url(#avatarGlow)"
              className="transition-all duration-75"
            />

            {/* Mandible Vent & Power Coupling Ports */}
            <line x1="140" y1="228" x2="160" y2="228" stroke={palette.primary} strokeWidth="1.5" strokeOpacity="0.6" />
            <line x1="144" y1="233" x2="156" y2="233" stroke={palette.primary} strokeWidth="1.1" strokeOpacity="0.4" />
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
              strokeWidth="1.8"
              strokeOpacity="0.85"
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
        <span className={`font-hud font-bold text-[9.5px] tracking-widest uppercase ${palette.text}`}>
          {statusMessage && statusMessage !== 'STANDING BY' ? (statusMessage.length > 24 ? statusMessage.slice(0, 24) + '...' : statusMessage) : state}
        </span>
      </div>
    </div>
  );
};
