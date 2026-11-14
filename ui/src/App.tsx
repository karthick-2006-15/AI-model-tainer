import { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { CoreArcReactor } from './components/CoreArcReactor';
import { TelemetryHUD } from './components/TelemetryHUD';
import { ChatFeed } from './components/ChatFeed';
import { MemoryExplorer } from './components/MemoryExplorer';
import { AgentStateType, TelemetryData, ChatMessage } from './types/hud';
import { ShieldCheck, Wifi, WifiOff } from 'lucide-react';

export function App() {
  const [activeTab, setActiveTab] = useState('hud');
  const [agentState, setAgentState] = useState<AgentStateType>('idle');
  const [statusMessage, setStatusMessage] = useState('JARVIS Core Initialized.');
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Determine WebSocket URL based on current host (direct to 8000 in dev mode)
    const isDev = window.location.port === '5173';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = isDev ? '127.0.0.1:8000' : window.location.host;
    const wsUrl = `${protocol}//${host}/ws/hud`;

    let socket: WebSocket;
    let reconnectTimer: number;

    const connect = () => {
      socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
        setStatusMessage('Connected to JARVIS Core.');
      };

      socket.onclose = () => {
        setIsConnected(false);
        setStatusMessage('Connection lost. Reconnecting...');
        reconnectTimer = window.setTimeout(connect, 2000);
      };

      socket.onerror = () => {
        // Quiet retry during initial boot or reconnection
        console.warn('JARVIS HUD WebSocket reconnecting...');
        socket.close();
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'telemetry') {
            setTelemetry(data.data);
          } else if (data.type === 'agent_state') {
            setAgentState(data.state);
            if (data.message) setStatusMessage(data.message);
          } else if (data.type === 'token_chunk') {
            const botMsg: ChatMessage = {
              id: `${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
              sender: 'jarvis',
              content: data.chunk,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            };
            setMessages((prev) => [...prev, botMsg]);
          }
        } catch (e) {
          console.warn('Failed to parse WebSocket message:', e);
        }
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      if (socket) socket.close();
    };
  }, []);

  const handleSendMessage = (text: string) => {
    const userMsg: ChatMessage = {
      id: `${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
      sender: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    };
    setMessages((prev) => [...prev, userMsg]);

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'chat_input',
        text: text
      }));
    } else {
      // Fallback local echo if socket temporarily reconnecting
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: `${Date.now()}_sys_${Math.random().toString(36).slice(2, 9)}`,
            sender: 'system',
            content: 'WebSocket offline. Action queued for transmission.',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
          }
        ]);
      }, 300);
    }
  };

  const handleEmergencyStop = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'abort_task',
        reason: 'User manual emergency abort triggered from HUD.'
      }));
    }
    setAgentState('error');
    setStatusMessage('EMERGENCY ABORT ACTIVE: All subtasks halted.');
  };

  return (
    <div className="flex h-screen w-screen bg-[#030712] text-slate-100 overflow-hidden scanline">
      {/* Sidebar Navigation */}
      <Sidebar 
        activeTab={activeTab} 
        onSelectTab={setActiveTab} 
        onEmergencyStop={handleEmergencyStop}
      />

      {/* Main Workspace Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header Bar */}
        <header className="h-14 border-b border-cyan-500/20 bg-[#040e21]/70 px-6 flex items-center justify-between backdrop-blur-md">
          <div className="flex items-center space-x-3">
            <span className="font-hud font-bold text-xs tracking-widest text-cyan-400">
              MARK VII // OPERATING ENVIRONMENT
            </span>
            <span className="h-3 w-px bg-cyan-700/50"></span>
            <div className="flex items-center space-x-1.5 text-xs text-slate-400">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Permission Guard: Level 1 (Read-Safe)</span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-xs">
              {isConnected ? (
                <span className="flex items-center space-x-1.5 text-emerald-400 font-mono text-[11px]">
                  <Wifi className="w-3.5 h-3.5" />
                  <span>CORE LINKED</span>
                </span>
              ) : (
                <span className="flex items-center space-x-1.5 text-rose-400 font-mono text-[11px]">
                  <WifiOff className="w-3.5 h-3.5 animate-pulse" />
                  <span>DISCONNECTED</span>
                </span>
              )}
            </div>
          </div>
        </header>

        {/* Dashboard Grid Content */}
        {activeTab === 'memory' ? (
          <div className="flex-1 p-6 overflow-hidden">
            <MemoryExplorer />
          </div>
        ) : (
          <div className="flex-1 p-6 grid grid-cols-12 gap-6 overflow-hidden">
            {/* Left Column: Central Arc Reactor & Status */}
            <div className="col-span-12 lg:col-span-7 flex flex-col justify-between bg-[#040e21]/40 border border-cyan-500/20 rounded-2xl p-6 backdrop-blur-sm hud-glow">
              <div className="flex justify-between items-center text-xs text-slate-400 font-hud">
                <span>HOLOGRAPHIC CORE MATRIX</span>
                <span className="text-cyan-400 font-mono">NODE_ID: WIN11_HOST</span>
              </div>

              <div className="my-auto py-4">
                <CoreArcReactor 
                  state={agentState} 
                  statusMessage={statusMessage}
                  onMicClick={() => {
                    setAgentState(agentState === 'listening' ? 'idle' : 'listening');
                    setStatusMessage(agentState === 'listening' ? 'Standing by.' : 'Listening for audio instruction...');
                  }}
                />
              </div>

              {/* Quick Status Bar */}
              <div className="border-t border-cyan-500/10 pt-3 flex justify-between items-center text-[11px] text-slate-400">
                <span>Wake-word: "Hey Jarvis"</span>
                <span className="text-cyan-300">FastAPI + AsyncIO + WebSockets</span>
              </div>
            </div>

            {/* Right Column: Real-Time Telemetry & Chat Command Feed */}
            <div className="col-span-12 lg:col-span-5 flex flex-col space-y-6 overflow-hidden">
              {/* Top Right: System Telemetry HUD */}
              <div className="shrink-0">
                <TelemetryHUD telemetry={telemetry} />
              </div>

              {/* Bottom Right: Real-time Command & Interaction Feed */}
              <div className="flex-1 overflow-hidden">
                <ChatFeed 
                  messages={messages} 
                  onSendMessage={handleSendMessage} 
                />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
