/**
 * JARVIS Mobile Bridge Client for Android Companion
 * Handles authenticated WebSocket communication, remote voice/text dispatch, and biometric approval.
 */

export interface Telemetry {
  cpu: { percent: number; cores: number };
  ram: { percent: number; used_gb: number; total_gb: number };
  disk: { percent: number };
  battery?: { percent: number | null };
}

export type OnTelemetryCallback = (data: Telemetry) => void;
export type OnCommandResultCallback = (command: string, response: string, verified: boolean) => void;
export type OnApprovalRequestCallback = (challengeId: string, tool: string, target: string) => void;

export class JarvisMobileBridge {
  private socket: WebSocket | null = null;
  private url: string;
  private token: string;
  private reconnectInterval: any = null;

  private onTelemetry: OnTelemetryCallback | null = null;
  private onCommandResult: OnCommandResultCallback | null = null;
  private onApprovalRequest: OnApprovalRequestCallback | null = null;

  constructor(serverHost: string, port: number = 8000, token: string = '') {
    this.url = `ws://${serverHost}:${port}/ws/mobile`;
    this.token = token;
  }

  public connect(
    onTelemetry: OnTelemetryCallback,
    onCommandResult: OnCommandResultCallback,
    onApprovalRequest: OnApprovalRequestCallback
  ) {
    this.onTelemetry = onTelemetry;
    this.onCommandResult = onCommandResult;
    this.onApprovalRequest = onApprovalRequest;

    this.socket = new WebSocket(this.url);

    this.socket.onopen = () => {
      console.log('[MobileBridge] Connected to JARVIS Core.');
      clearInterval(this.reconnectInterval);
    };

    this.socket.onclose = () => {
      console.log('[MobileBridge] Disconnected. Reconnecting in 3s...');
      this.reconnectInterval = setTimeout(() => {
        this.connect(this.onTelemetry!, this.onCommandResult!, this.onApprovalRequest!);
      }, 3000);
    };

    this.socket.onerror = (e) => {
      console.error('[MobileBridge] Socket Error:', e);
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'laptop_telemetry' && this.onTelemetry) {
          this.onTelemetry(data.data);
        } else if (data.type === 'command_result' && this.onCommandResult) {
          this.onCommandResult(data.command, data.response, data.verified);
        } else if (data.type === 'permission_request' && this.onApprovalRequest) {
          this.onApprovalRequest(data.challenge_id, data.tool_name, data.target_resource);
        }
      } catch (err) {
        console.error('[MobileBridge] Parse error:', err);
      }
    };
  }

  public sendCommand(command: string) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        type: 'mobile_command',
        command: command,
        token: this.token
      }));
    }
  }

  public sendBiometricApproval(challengeId: string, approved: boolean, biometricType: string = 'fingerprint') {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        type: 'biometric_approval',
        challenge_id: challengeId,
        approved: approved,
        biometric_type: biometricType
      }));
    }
  }

  public disconnect() {
    clearTimeout(this.reconnectInterval);
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}
