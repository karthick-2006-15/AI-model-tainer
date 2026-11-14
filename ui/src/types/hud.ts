export type AgentStateType = 'idle' | 'listening' | 'thinking' | 'executing' | 'verifying' | 'error';

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
