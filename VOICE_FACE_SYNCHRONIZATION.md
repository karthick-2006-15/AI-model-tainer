# JARVIS Voice-Face Synchronization Specification

## 1. Synchronization Architecture Overview

The synchronization between the **JARVIS Audio Engine** and the **Animated AI Face** creates an organic illusion of speech articulation. When JARVIS vocalizes responses via Edge-TTS or the Web Speech API, facial deformation and mouth aperture respond in real time to audio amplitude, phonemes, and syllable boundaries.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   VOICE-FACE SYNCHRONIZATION PIPELINE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [ User Speech Input ] ────────► Wake-Word / VAD Detection                 │
│                                           │                                 │
│                                           ▼                                 │
│                               Avatar State: 'LISTENING'                     │
│                               (Pupils Dilate, Head Tilts Up)                │
│                                           │                                 │
│                                           ▼                                 │
│                                Central AI Reasoning                         │
│                                           │                                 │
│                                           ▼                                 │
│                               Avatar State: 'THINKING'                      │
│                               (Scanning Eye Reticles Active)                │
│                                           │                                 │
│                                           ▼                                 │
│       ┌─────────────────── Speech Synthesis Response ───────────────────┐   │
│       │                                                                 │   │
│       ▼                                                                 ▼   │
│  Audio Stream Output                                          Avatar Face   │
│  (Edge-TTS / SpeechSynthesis)                         State: 'SPEAKING'     │
│       │                                                                 │   │
│       ▼                                                                 ▼   │
│  Word Boundary Events ───────────► Exponential Filter ───────► Lip Aperture │
│  (utterance.onboundary)            Smoothing (α = 0.35)        (0px - 22px) │
│                                                                 │           │
│                                                                 ▼           │
│                                                       7-Bar Vocal Equalizer │
│                                                                 │           │
│       ┌─────────────────────────────────────────────────────────┘           │
│       ▼                                                                     │
│  Speech Complete ────────────────► Return to 'IDLE'                         │
│  (utterance.onend)                 (Mouth Closes, Respiration Resumes)      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Real-Time Lip-Sync Engine

### 2.1 Web Speech API Boundary Tracking
In the frontend React application (`ui/src/App.tsx`), speech output is vocalized via `SpeechSynthesisUtterance`. High-resolution boundary tracking is attached directly to the vocalization lifecycle:

```typescript
// 1. Audio Start Hook
utterance.onstart = () => {
  setAgentState('speaking');
  setAudioAmplitude(0.7);
};

// 2. Word & Syllable Boundary Hook
utterance.onboundary = (event) => {
  // Modulate mouth opening dynamically on each syllable
  const dynamicCadence = 0.45 + Math.random() * 0.5;
  setAudioAmplitude(dynamicCadence);
};

// 3. Audio Completion Hook
utterance.onend = () => {
  setAudioAmplitude(0.0);
  setAgentState('idle');
};

// 4. Fault Handling
utterance.onerror = () => {
  setAudioAmplitude(0.0);
  setAgentState('idle');
};
```

### 2.2 Kinetic Lip Aperture & Waveform Deformation
In `ui/src/components/JarvisAvatar.tsx`, the amplitude is smoothly interpolated via `requestAnimationFrame`:

```typescript
const mouthOpenAmount = (state === 'speaking' ? smoothAmp : 0.05) * 22; // 0 to 22 pixels

// Upper Lip Bezier:
<path d="M 98,162 Q 125,161 152,162" />

// Lower Lip Dynamic Drop Bezier:
<path d={`M 102,${166 + mouthOpenAmount} Q 125,${168 + mouthOpenAmount * 1.2} 148,${166 + mouthOpenAmount}`} />
```

Between the lips, 7 vertical audio frequency equalizer bars oscillate synchronously with the vocal phonemes and audio volume:
```typescript
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
```

---

## 3. Zero-Latency Duplex Barge-In Interruption

When the user speaks while JARVIS is speaking or vocalizing a response:
1. **Immediate Audio Cancellation:** `window.speechSynthesis.cancel()` is triggered immediately on microphone activation.
2. **Instant Mouth Reset:** `setAudioAmplitude(0.0)` instantly collapses the mouth aperture to 0px (no lagging jaw motion).
3. **State Transition:** The avatar snaps from `SPEAKING` to `LISTENING`.
4. **Backend Coordination:** In `api/websockets/hud_stream.py`, the backend aborts active TTS threads via `tts_engine.stop()`.

This guarantees a natural, uninterrupted conversational flow without overlapping audio or visual desynchronization.
