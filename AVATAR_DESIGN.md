# JARVIS Animated Virtual AI Face: Design Specification

## 1. Design Philosophy & Aesthetic Identity

The **JARVIS Virtual AI Face** serves as the primary visual identity of the JARVIS Personal AI Operating System. Designed with a premium science-fiction cybernetic aesthetic inspired by Tony Stark's iconic digital interfaces and advanced holographic intelligences, the avatar embodies high intelligence, alertness, and digital precision—deliberately avoiding cartoon or emoji tropes in favor of a sleek, holographic cybernetic entity.

```
                  ┌────────────────────────────────────────┐
                  │      JARVIS HOLOGRAPHIC CRANIAL MATRIX │
                  │                                        │
                  │              [ TEMPLE CREST ]          │
                  │          ┌───────────────────────┐     │
                  │          │     DATA MATRIX TRACE │     │
                  │          └───────────────────────┘     │
                  │       [LEFT BROW]         [RIGHT BROW] │
                  │       ╭─────────╮         ╭─────────╮  │
                  │       │ ( (●) ) │         │ ( (●) ) │  │
                  │       ╰─────────╯         ╰─────────╯  │
                  │       [CYBER EYE]         [CYBER EYE]  │
                  │                                        │
                  │               | NOSE BRIDGE |          │
                  │                                        │
                  │             ╭────────────────╮         │
                  │             │  ||||||||||||  │         │
                  │             ╰────────────────╯         │
                  │             [DYNAMIC LIP-SYNC]         │
                  │                                        │
                  │            \____ JAWLINE ____/         │
                  └────────────────────────────────────────┘
```

---

## 2. Anatomical & Visual Subsystem Breakdown

### 2.1 Cranial Contour, Polygonal Facet Mesh & Compass Ring
- **Geometry & Faceting:** High-density cybernetic wireframe polygonal mesh with forehead triangulation, cheekbone facet planes (`polygon points="105,150 78,185 125,205 150,175"`), and jawline facet connectors meeting at the chin anchor with cybernetic air/power vents.
- **Surface Texture & Glow:** Dark translucent glass base (`fill="#030816"`, `opacity=0.88`) with microscopic circuit grid and volumetric holographic SVG glow filter (`#avatarGlow` via `feGaussianBlur stdDeviation=2.5`).
- **360° Cardinal Compass Reticles:** Outer compass orbital dial with degree marks (`000°`, `090°`, `180°`, `270°`), 4 corner framing brackets (`[ + ]`), and telemetry watermarks (`SYS.AI // MARK_VII`, `BIOMETRIC_MATRIX`).
- **Temporal Sensors:** Angular cybernetic temple plates with luminous edge chamfers and vertex nodes.

### 2.2 Expressive Cybernetic Digital Eyes
The eyes serve as the focal point of emotional expression, attention, and cognitive state communication:
- **Outer Socket:** Hexagonal tech reticles with precision corner chamfers.
- **Iris Architecture:** Concentric circular reticles with counter-rotating tick marks (`animate-spin-slow` and `animate-spin`) and radial gradient falloff (`#ffffff` core -> `palette.primary` -> `palette.secondary` edge).
- **Gaze & Saccades:** Smooth mouse cursor tracking across 2D screen coordinates (`gaze.x`, `gaze.y`) with dynamic pupil dilation:
  - *Normal:* 3.8px radius
  - *Listening:* 5.0px radius (dilated attention)
  - *Thinking:* 3.0px radius with orbital tech crosshairs and micro-saccadic scanning shifts
- **Dynamic Eyelids:** Dual parametric clipping masks simulating organic blinking:
  - Natural blinking interval: randomly scheduled between 2.6s and 6.0s (160ms duration)
  - *Sleeping:* Lowered to 90% closure with subtle standby respiration
  - *Happy / Success:* Lower eyelids lift into upward smiling crescent curves
- **Eyebrow Posture:** Dynamic quadratic curves reflecting cognitive state:
  - *Neutral:* Horizontal level curve
  - *Listening:* Arched upwards (+0.1 rad)
  - *Thinking:* Furrowed analytical posture (-0.15 rad)
  - *Confused:* Asymmetric cocked left eyebrow (-0.3 rad) + furrowed right
  - *Error:* Sharply angled downward alert posture (-0.4 rad)

### 2.3 Dynamic Lip-Sync Mouth & Equalizer Jaw
- **Segmented Digital Lips:** Upper and lower bezier paths that dynamically expand vertically based on real-time speech amplitude (`mouthOpenAmount: 0.0 to 22.0px`).
- **Real-Time Vocal Frequency Visualizer:** Between the lips during speech, 7 vertical audio frequency equalizer bars oscillate synchronously with the vocal phonemes and audio volume.
- **Emotional Modulation:**
  - *Happy / Success:* Lips bend upward into a subtle cybernetic smile.
  - *Idle:* Crisp horizontal cyber-vent line with slow breathing pulse.

### 2.4 Orbital HUD Rings & Holographic Scanline
- **Orbital Ring:** Outer dashed holographic boundary ring rotating counter-clockwise (`animate-spin-slow` in idle, accelerated `animate-spin` in thinking).
- **Laser Scanline:** Vertical cybernetic scanning beam traversing top-to-bottom every 3.6 seconds, simulating holographic refresh sweeps.

---

## 3. Theme Color Palettes

The avatar engine supports 4 distinct holographic themes with state-driven color overrides:

| Theme Name | Primary Accent | Secondary Accent | Volumetric Glow | Design Inspiration |
| :--- | :--- | :--- | :--- | :--- |
| **Classic Cyan** | `#22d3ee` (Cyan-400) | `#0284c7` (Sky-600) | `rgba(34, 211, 238, 0.6)` | Mark VII Holographic HUD |
| **Arc Gold** | `#fbbf24` (Amber-400) | `#b45309` (Amber-700) | `rgba(251, 191, 36, 0.6)` | Vibranium Arc Reactor |
| **Quantum Violet** | `#c084fc` (Purple-400) | `#7e22ce` (Purple-700) | `rgba(192, 132, 252, 0.6)` | Deep Neural Core |
| **Matrix Emerald** | `#34d399` (Emerald-400) | `#047857` (Emerald-700) | `rgba(52, 211, 153, 0.6)` | Tactical Bio-Link |

### State Overrides:
- **`listening` / `happy` / `success`:** Shifts to bright Emerald Green (`#10b981`) for affirmative feedback.
- **`warning` / `executing`:** Shifts to Golden Amber (`#f59e0b`) indicating active background execution.
- **`error`:** Shifts to Crimson Red (`#ef4444`) with subtle glitch pulses.
- **`sleeping`:** Dimmed navy glow with lowered eyelids and slow standby respiration.

---

## 4. Floating Desktop Widget Specification

- **Window Characteristics:** Frameless, transparent background, always-on-top (`HWND_TOPMOST` / -1).
- **Draggability:** Smooth mouse drag via header handle or avatar perimeter; stores last screen position in `localStorage.jarvis_avatar_coords`.
- **Quick Controls (Hover Bar):**
  - Theme Cycle button (cycles 4 holographic themes)
  - Size Scale button (Small: 180px, Medium: 240px, Large: 320px)
  - Audio Output Mute / Unmute
  - Push-to-Talk Mic button
  - Expand to Full HUD Dashboard button
- **Desktop Launcher Script:** `scripts/run_floating_avatar.py` launches Microsoft Edge / Chromium in standalone `--app` mode, pinned to `HWND_TOPMOST` via Windows User32 API.
