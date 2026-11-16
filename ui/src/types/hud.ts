export type AgentStateType = 
  | 'idle' 
  | 'listening' 
  | 'thinking' 
  | 'speaking' 
  | 'happy' 
  | 'confused' 
  | 'error' 
  | 'warning' 
  | 'sleeping' 
  | 'success'
  | 'executing' 
  | 'verifying';

export type AvatarThemeType = 'classic_cyan' | 'arc_gold' | 'quantum_violet' | 'matrix_emerald';
export type AvatarSizeType = 'small' | 'medium' | 'large';

export interface AvatarEyeMetrics {
  left_pupil: { x: number; y: number; dilation: number };
  right_pupil: { x: number; y: number; dilation: number };
  eyelid_open: number;
  eyebrow_tilt: number;
}

export interface AvatarLipSync {
  amplitude: number;
  mouth_open: number;
  phoneme: string;
  last_updated: number;
}

export interface AvatarStateData {
  state: AgentStateType;
  expression: string;
  status_message: string;
  eye_metrics: AvatarEyeMetrics;
  lip_sync: AvatarLipSync;
  theme: AvatarThemeType;
  size: AvatarSizeType;
  glow_intensity: number;
  scanlines_enabled: boolean;
  always_on_top: boolean;
  timestamp: number;
}

export interface TelemetryData {
  platform: string;
  os_release: string;
  cpu: {
    percent: number;
    cores: number;
  };
  ram: {
    used_gb: number;
    total_gb: number;
    percent: number;
  };
  disk: {
    used_gb: number;
    total_gb: number;
    percent: number;
  };
  battery?: {
    percent: number | null;
    power_plugged: boolean | null;
  };
  process_count: number;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'jarvis' | 'system';
  content: string;
  timestamp: string;
}
