# JARVIS Avatar Animation System Specification

## 1. Animation Architecture Overview

The **JARVIS Avatar Animation System** combines parametric SVG vector deformation, Web Audio amplitude analysis, CSS 3D perspective transforms, and requestAnimationFrame linear interpolation (lerping) to deliver fluid, 60 FPS lifelike animation.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       JARVIS AVATAR ANIMATION PIPELINE                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [ Backend WebSocket / REST ]                                              │
│               │                                                             │
│               ▼                                                             │
│       Avatar State Machine                                                  │
│   (idle, listening, thinking, speaking, happy, confused, error, sleeping)   │
│               │                                                             │
│       ┌───────┴───────────────────────────────┐                             │
│       ▼                                       ▼                             │
│   Kinematic Transform Engine              Facial Morphing Engine            │
│   - Sinusoidal Respiration (3.5s)         - Eye Blinking Scheduler (3-5s)   │
│   - Head Tilt (Pitch, Yaw, Roll)          - Eyelid Parametric Masks         │
│   - Mouse Gaze Tracking                   - Eyebrow Curve Vectors           │
│       │                                   - Dynamic Lip-Sync Visemes        │
│       │                                   - Audio Equalizer Waveform Bars   │
│       │                                       │                             │
│       └───────────────────┬───────────────────┘                             │
│                           ▼                                                 │
│                Hardware Accelerated Compositor                              │
│                 (60 FPS requestAnimationFrame)                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Animation States & Visual Behaviors

### 2.1 `IDLE` (Standby & Ambient Respiration)
- **Breathing Oscillation:** Head smoothly translates vertically along the Y-axis:
  $$\Delta y = 4.0 \cdot \sin\left(\frac{2\pi t}{3.5}\right)\text{ px}$$
- **Blinking:** Natural involuntary eyelid closure scheduled randomly every $3.0 \pm 1.8$ seconds, lasting 160ms.
- **Head Posture:** Neutral level alignment (`rotateX: 0°`, `rotateY: 0°`, `rotateZ: 0°`).
- **Gaze:** Smoothly tracks user mouse coordinates across screen with damping factor ($0.4\times$).
- **Mouth:** Closed cybernetic vent line with low-intensity cyan breathing pulse.

### 2.2 `LISTENING` (Attentive Visual Perception)
- **Pupil Reaction:** Pupils dilate from 3.2px to 4.5px (+40% surface area).
- **Head Posture:** Head tilts upwards slightly (`rotateX: -4°`), indicating attentive focus.
- **Aura & Illumination:** Shifts to bright Emerald Green (`#10b981`) with active visual pulsation around the iris ring.
- **Eyebrows:** Raised slightly into alert, receptive curvature (`eyelid_open: 1.05`, `eyebrow_tilt: +0.1`).
- **Mouth:** Neutral ready posture.

### 2.3 `THINKING` (Cognitive Processing & Problem Solving)
- **Orbital Ring Acceleration:** Outer dashed HUD reticle ring spins at $3\times$ idle speed (`animate-spin`).
- **Micro-Saccades:** Eyes shift slightly upward and to the side (`x: +0.25, y: -0.15`), mimicking human cognitive retrieval.
- **Head Posture:** Thoughtful cocked head posture (`rotateX: +2°`, `rotateY: +4°`, `rotateZ: -3.5°`).
- **Eyebrows:** Inner brow dips into furrowed analytical concentration (`eyebrow_tilt: -0.15`).
- **Laser Scanline:** Active holographic sweep beam traversing cranial matrix every 3.6s.

### 2.4 `SPEAKING` (Synchronous Articulation & Vocal Waveform)
- **Lip Aperture:** Vertical separation between upper and lower lips modulates dynamically between 0px and 22px based on smoothed vocal amplitude $A_t$.
- **Equalizer Waveform:** 7 dynamic cyan frequency bars dance between the lips, oscillating at audio frequency intervals.
- **Head Nod Cadence:** Subtle organic affirmative head nods aligned with sentence rhythm (`rotateX: -1°`).
- **Eye Contact:** Eyes remain locked onto user cursor, maintaining steady visual rapport.

### 2.5 `HAPPY` / `SUCCESS` (Affirmative Goal Completion)
- **Eye Curvature:** Lower eyelids elevate into smiling crescent arches.
- **Eyebrows:** Uplifted friendly curvature (`eyebrow_tilt: +0.25`).
- **Mouth:** Upper and lower lips curve gently upwards into a subtle cybernetic smile.
- **Aura:** Brighter emerald-cyan illumination pulse.

### 2.6 `CONFUSED` / `QUESTIONING` (Ambiguity or Clarification Needed)
- **Asymmetric Eyebrows:** Left eyebrow arches upward high (`y1: 73px`), while right eyebrow furrows down (`y1: 86px`).
- **Head Posture:** Quizzical asymmetric tilt (`rotateZ: +5°`, `rotateY: -4°`).
- **Pupils:** Slight questioning glance offset.

### 2.7 `ERROR` / `WARNING` (Fault Detection or Security Alert)
- **Color Accent:** Core illumination shifts instantly to Crimson Red (`#ef4444`) or Golden Amber (`#f59e0b`).
- **Eyebrows:** Angled sharply downward into an intense alert posture (`eyebrow_tilt: -0.4`).
- **Glitch Effect:** Brief high-frequency micro-jitter in orbital reticles.

### 2.8 `SLEEPING` / `LOW-POWER` (Standby & Power Conservation)
- **Eyelids:** Lowered to 90% closure (`height: 18px`), concealing pupils.
- **Respiration:** Respiration period slows to 5.0 seconds with reduced amplitude (2px).
- **Head Posture:** Slightly bowed forward (`rotateX: +6°`).
- **Aura:** Dimmed low-intensity navy glow (`0.25x` normal intensity).

---

## 3. Mathematical Interpolation & Kinematics

### 3.1 Audio Amplitude Exponential Smoothing (Lerp)
To eliminate audio jitter during speech, real-time volume input $T$ is filtered using an exponential moving average updated on every display frame:

$$A_{t} = A_{t-1} + \alpha \cdot \left(T - A_{t-1}\right)$$

where $\alpha = 0.35$. If speech stops, $A_t$ decays exponentially to $0.0$.

### 3.2 Gaze Coordinate Clamping & Projection
Given mouse coordinates $(M_x, M_y)$ and avatar center $(C_x, C_y)$, normalized gaze vector $(G_x, G_y)$ is clamped within a circle of radius $R_{\text{max}} = 5\text{ px}$:

$$G_x = \text{clamp}\left(\frac{M_x - C_x}{W / 2}, -1, 1\right) \times 5.0$$
$$G_y = \text{clamp}\left(\frac{M_y - C_y}{H / 2}, -1, 1\right) \times 4.0$$

---

## 4. Performance & Rendering Benchmarks
- **Rendering Technology:** Vector SVG + Canvas fallback, accelerated via GPU compositing.
- **Frame Budget:** Targets < 1.2ms render time per frame on standard Windows 11 hardware.
- **CPU Overhead:** < 0.8% average CPU utilization in idle standby.
- **Memory Footprint:** < 45 MB browser runtime heap memory.
