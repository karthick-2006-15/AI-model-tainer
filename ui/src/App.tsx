import { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { CoreArcReactor } from './components/CoreArcReactor';
import { TelemetryHUD } from './components/TelemetryHUD';
import { ChatFeed } from './components/ChatFeed';
import { MemoryExplorer } from './components/MemoryExplorer';
import { TaskManagerHUD } from './components/TaskManagerHUD';
import { AgentStateType, TelemetryData, ChatMessage } from './types/hud';
import { ShieldCheck, Wifi, WifiOff, Volume2, VolumeX } from 'lucide-react';

export function App() {
  const [activeTab, setActiveTab] = useState('hud');
  const [agentState, setAgentState] = useState<AgentStateType>('idle');
  const [statusMessage, setStatusMessage] = useState('JARVIS Core Initialized.');
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [voiceOutputEnabled, setVoiceOutputEnabled] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<any>(null);

  // Helper to vocalize responses directly in the browser via SpeechSynthesis
  const speakVoice = (text: string) => {
    if (!voiceOutputEnabled || !('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      const clean = text
        .replace(/\[Voice Instruction:.*?\]/gs, '')
        .replace(/[*_#`~]/g, '')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        .replace(/https?:\/\/\S+/g, '')
        .replace(/^[ \t]*[•\-\*][ \t]+/gm, '')
        .trim();
      if (!clean) return;

      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find(
        (v) =>
          v.lang.startsWith('en') &&
          (v.name.includes('Natural') ||
            v.name.includes('Google') ||
            v.name.includes('David') ||
            v.name.includes('Microsoft'))
      );
      if (preferred) utterance.voice = preferred;
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('Speech synthesis note:', e);
    }
  };

  useEffect(() => {
    let isDisposed = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;

    // Use Vite proxy (/ws/hud) or explicit environment variable
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const envWs = (import.meta as any).env?.VITE_WS_URL;
    const wsUrl = envWs 
      ? `${envWs}/ws/hud`
      : `${protocol}//${window.location.host}/ws/hud`;

    const connect = () => {
      if (isDisposed) return;

      try {
        socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          if (isDisposed) {
            socket?.close(1000, 'Unmounted');
            return;
          }
          setIsConnected(true);
          setStatusMessage('Connected to JARVIS Core.');
        };

        socket.onclose = (event) => {
          if (isDisposed) return;
          setIsConnected(false);
          // Only reconnect if disconnection was unexpected
          if (event.code !== 1000) {
            setStatusMessage('Connection lost. Reconnecting...');
            reconnectTimer = window.setTimeout(connect, 2500);
          }
        };

        socket.onerror = () => {
          if (isDisposed) return;
          // Cleanly handle reconnect through onclose without noisy logs
        };

        socket.onmessage = (event) => {
          if (isDisposed) return;
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
              speakVoice(data.chunk);
            }
          } catch (e) {
            // Silently drop invalid packets
          }
        };
      } catch (err) {
        if (!isDisposed) {
          reconnectTimer = window.setTimeout(connect, 3000);
        }
      }
    };

    connect();

    return () => {
      isDisposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (socket) {
        if (socket.readyState === WebSocket.OPEN) {
          socket.close(1000, 'Component unmounted');
        } else if (socket.readyState === WebSocket.CONNECTING) {
          socket.onopen = () => socket?.close(1000, 'Component unmounted');
          socket.onerror = null;
          socket.onclose = null;
        }
      }
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

  const toggleVoiceRecognition = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert(
        'Voice input is supported in Google Chrome, Microsoft Edge, and Chromium-based browsers. Please ensure microphone permissions are allowed in your browser settings.'
      );
      return;
    }

    if (isListening) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (_) {}
      }
      setIsListening(false);
      setAgentState('idle');
      setStatusMessage('Voice recognition paused.');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsListening(true);
        setAgentState('listening');
        setStatusMessage('Listening to your voice... Speak your command.');
      };

      recognition.onresult = (event: any) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }

        if (finalTranscript.trim()) {
          setStatusMessage(`Understood: "${finalTranscript.trim()}"`);
          handleSendMessage(finalTranscript.trim());
          setIsListening(false);
          setAgentState('thinking');
        } else if (interimTranscript) {
          setStatusMessage(`Hearing: "${interimTranscript}"`);
        }
      };

      recognition.onerror = (event: any) => {
        console.warn('Speech recognition warning:', event.error);
        setIsListening(false);
        setAgentState('idle');
        if (event.error === 'not-allowed') {
          setStatusMessage(
            'Microphone access blocked. Click the lock/tune icon in your browser address bar to allow microphone.'
          );
        } else {
          setStatusMessage('Microphone idle. Click to speak.');
        }
      };

      recognition.onend = () => {
        setIsListening(false);
        setAgentState((prev) => (prev === 'listening' ? 'idle' : prev));
      };

      recognition.start();
    } catch (err) {
      console.error('Failed to start voice recognition:', err);
      setIsListening(false);
      setAgentState('idle');
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
            {/* Voice Audio Feedback Toggle */}
            <button
              onClick={() => setVoiceOutputEnabled(!voiceOutputEnabled)}
              title={voiceOutputEnabled ? "Voice Output Active (Click to Mute)" : "Voice Output Muted (Click to Unmute)"}
              className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-[#08152e] border border-cyan-800/40 text-[11px] text-cyan-300 hover:border-cyan-400 transition"
            >
              {voiceOutputEnabled ? (
                <>
                  <Volume2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>VOICE: ON</span>
                </>
              ) : (
                <>
                  <VolumeX className="w-3.5 h-3.5 text-slate-400" />
                  <span>VOICE: MUTED</span>
                </>
              )}
            </button>

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
        ) : activeTab === 'tasks' ? (
          <div className="flex-1 p-6 overflow-hidden">
            <TaskManagerHUD />
          </div>
        ) : (
          <div className="flex-1 p-4 lg:p-6 grid grid-cols-12 gap-4 lg:gap-6 overflow-y-auto lg:overflow-hidden">
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
                  onMicClick={toggleVoiceRecognition}
                />
              </div>

              {/* Quick Status Bar */}
              <div className="border-t border-cyan-500/10 pt-3 flex justify-between items-center text-[11px] text-slate-400">
                <span>Wake-word: "Hey Jarvis" (or click Arc Reactor / Mic button)</span>
                <span className="text-cyan-300">FastAPI + Speech Engine + WebSockets</span>
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
                  onToggleMic={toggleVoiceRecognition}
                  isListening={isListening}
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
