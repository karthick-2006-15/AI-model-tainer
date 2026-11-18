import { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { JarvisAvatar } from './components/JarvisAvatar';
import { FloatingAvatarWidget } from './components/FloatingAvatarWidget';
import { CoreArcReactor } from './components/CoreArcReactor';
import { TelemetryHUD } from './components/TelemetryHUD';
import { ChatFeed } from './components/ChatFeed';
import { MemoryExplorer } from './components/MemoryExplorer';
import { TaskManagerHUD } from './components/TaskManagerHUD';
import { VoiceHub } from './components/VoiceHub';
import { ComputerIntelView } from './components/ComputerIntelView';
import { SettingsView } from './components/SettingsView';
import { MusicCard } from './components/MusicCard';
import { AgentStateType, TelemetryData, ChatMessage, AvatarThemeType, AvatarSizeType, SpotifyPlaybackState } from './types/hud';
import { ShieldCheck, Wifi, WifiOff, Volume2, VolumeX, Sparkles, Disc, PictureInPicture2 } from 'lucide-react';

export function App() {
  const [activeTab, setActiveTab] = useState('hud');
  const [agentState, setAgentState] = useState<AgentStateType>('idle');
  const [statusMessage, setStatusMessage] = useState('JARVIS Core Initialized.');
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [voiceOutputEnabled, setVoiceOutputEnabled] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [audioAmplitude, setAudioAmplitude] = useState(0.0);
  const [avatarTheme, setAvatarTheme] = useState<AvatarThemeType>('classic_cyan');
  const [avatarSize, setAvatarSize] = useState<AvatarSizeType>('medium');
  const [glowIntensity, setGlowIntensity] = useState(0.85);
  const [scanlinesEnabled, setScanlinesEnabled] = useState(true);
  const [centerMode, setCenterMode] = useState<'avatar' | 'reactor'>('avatar');

  // Check URL query parameter ?mode=widget for frameless desktop launcher
  const isWidgetParam = new URLSearchParams(window.location.search).get('mode') === 'widget';
  const [isFloatingWidget, setIsFloatingWidget] = useState(isWidgetParam);

  // Live Spotify Desktop Playback Telemetry
  const [spotifyState, setSpotifyState] = useState<SpotifyPlaybackState | null>(null);

  // Poll Spotify playback telemetry every 3 seconds
  useEffect(() => {
    let isDisposed = false;
    const fetchSpotify = async () => {
      try {
        const res = await fetch('/api/spotify/state');
        if (res.ok && !isDisposed) {
          const data = await res.json();
          setSpotifyState(data);
        }
      } catch (_) {}
    };

    fetchSpotify();
    const interval = setInterval(fetchSpotify, 2800);
    return () => {
      isDisposed = true;
      clearInterval(interval);
    };
  }, []);

  const handleMusicPlayPause = async () => {
    try {
      if (spotifyState?.is_playing) {
        await fetch('/api/spotify/pause', { method: 'POST' });
        setSpotifyState((prev) => prev ? { ...prev, is_playing: false, is_paused: true } : null);
      } else {
        await fetch('/api/spotify/resume', { method: 'POST' });
        setSpotifyState((prev) => prev ? { ...prev, is_playing: true, is_paused: false } : null);
      }
    } catch (e) {
      console.warn('Music control error:', e);
    }
  };

  const handleMusicNext = async () => {
    try {
      const res = await fetch('/api/spotify/next', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.current_track) {
          setSpotifyState((prev) => prev ? { ...prev, track: data.current_track, is_playing: true } : null);
        }
      }
    } catch (e) {
      console.warn('Music next error:', e);
    }
  };

  const handleMusicPrevious = async () => {
    try {
      const res = await fetch('/api/spotify/previous', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.current_track) {
          setSpotifyState((prev) => prev ? { ...prev, track: data.current_track, is_playing: true } : null);
        }
      }
    } catch (e) {
      console.warn('Music previous error:', e);
    }
  };

  const handleMusicVolumeChange = async (vol: number) => {
    setSpotifyState((prev) => prev ? { ...prev, volume: vol } : null);
    try {
      await fetch('/api/spotify/volume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ level: vol })
      });
    } catch (e) {
      console.warn('Volume set error:', e);
    }
  };

  const handleOpenSpotify = async () => {
    try {
      await fetch('/api/spotify/open', { method: 'POST' });
    } catch (e) {
      console.warn('Open Spotify error:', e);
    }
  };

  const wsRef = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<any>(null);

  // Vocalize responses via SpeechSynthesis with synchronized lip-sync and audio amplitude
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

      // Real-time lip-sync hooks
      utterance.onstart = () => {
        setAgentState('speaking');
        setAudioAmplitude(0.7);
      };

      utterance.onboundary = () => {
        // Dynamic syllable cadence
        setAudioAmplitude(0.45 + Math.random() * 0.5);
      };

      utterance.onend = () => {
        setAudioAmplitude(0.0);
        setAgentState('idle');
      };

      utterance.onerror = () => {
        setAudioAmplitude(0.0);
        setAgentState('idle');
      };

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('Speech synthesis note:', e);
    }
  };

  useEffect(() => {
    let isDisposed = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const envWs = (import.meta as any).env?.VITE_WS_URL;
    const wsUrl = envWs 
      ? `${envWs}/ws/hud`
      : (window.location.port === '5173' 
          ? 'ws://127.0.0.1:8000/ws/hud' 
          : `${protocol}//${window.location.host}/ws/hud`);

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
          if (event.code !== 1000) {
            setStatusMessage('Connection lost. Reconnecting...');
            reconnectTimer = window.setTimeout(connect, 2500);
          }
        };

        socket.onerror = () => {
          if (isDisposed) return;
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
            } else if (data.type === 'avatar_state' && data.avatar) {
              if (data.avatar.state) setAgentState(data.avatar.state);
              if (data.avatar.theme) setAvatarTheme(data.avatar.theme);
            } else if (data.type === 'token_chunk') {
              const botMsg: ChatMessage = {
                id: `${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
                sender: 'jarvis',
                content: data.chunk,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
              };
              setMessages((prev) => [...prev, botMsg]);
              speakVoice(data.chunk);
            } else if (data.type === 'chat_message') {
              const chatMsg: ChatMessage = {
                id: `${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
                sender: data.sender || 'user',
                content: data.content,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
              };
              setMessages((prev) => [...prev, chatMsg]);
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

  // Immediate barge-in: cancels any ongoing speech and prepares for user voice
  const toggleVoiceRecognition = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setAudioAmplitude(0.0);
    }

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
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setAudioAmplitude(0.0);
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'abort_task',
        reason: 'User manual emergency abort triggered from HUD.'
      }));
    }
    setAgentState('error');
    setStatusMessage('EMERGENCY ABORT ACTIVE: All subtasks halted.');
  };

  // If in pure floating widget mode (e.g. desktop app or popup window)
  if (isFloatingWidget) {
    return (
      <div className="w-screen h-screen bg-transparent flex items-center justify-center overflow-hidden">
        <FloatingAvatarWidget
          state={agentState}
          statusMessage={statusMessage}
          theme={avatarTheme}
          size={avatarSize}
          audioAmplitude={audioAmplitude}
          voiceOutputEnabled={voiceOutputEnabled}
          isListening={isListening}
          onExpandDashboard={() => setIsFloatingWidget(false)}
          onToggleMic={toggleVoiceRecognition}
          onToggleMute={() => setVoiceOutputEnabled(!voiceOutputEnabled)}
          onChangeTheme={setAvatarTheme}
          onChangeSize={setAvatarSize}
          onClose={() => setIsFloatingWidget(false)}
        />
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen bg-[#030712] text-slate-100 overflow-hidden scanline">
      {/* Sidebar Navigation (7 Tabs) */}
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
              MARK VII // AI VISUAL IDENTITY & OPERATING ENVIRONMENT
            </span>
            <span className="h-3 w-px bg-cyan-700/50"></span>
            <div className="flex items-center space-x-1.5 text-xs text-slate-400">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Permission Guard: Level 1 (Read-Safe)</span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {/* Toggle Floating Desktop Widget Mode */}
            <button
              onClick={() => setIsFloatingWidget(true)}
              title="Switch to Floating Desktop Avatar Widget"
              className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-[#08152e] border border-cyan-800/40 text-[11px] text-cyan-300 hover:border-cyan-400 transition"
            >
              <PictureInPicture2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>FLOATING WIDGET</span>
            </button>

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

            {/* Core Connection Status */}
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

        {/* 7 Tab Dashboard Views */}
        {activeTab === 'voice' ? (
          <div className="flex-1 p-6 overflow-hidden">
            <VoiceHub 
              isListening={isListening}
              onToggleMic={toggleVoiceRecognition}
              voiceOutputEnabled={voiceOutputEnabled}
              onToggleVoiceOutput={() => setVoiceOutputEnabled(!voiceOutputEnabled)}
            />
          </div>
        ) : activeTab === 'tasks' ? (
          <div className="flex-1 p-6 overflow-hidden">
            <TaskManagerHUD />
          </div>
        ) : activeTab === 'computer' ? (
          <div className="flex-1 p-6 overflow-hidden">
            <ComputerIntelView />
          </div>
        ) : activeTab === 'memory' ? (
          <div className="flex-1 p-6 overflow-hidden">
            <MemoryExplorer />
          </div>
        ) : activeTab === 'telemetry' ? (
          <div className="flex-1 p-6 overflow-y-auto">
            <div className="max-w-4xl mx-auto space-y-6">
              <h2 className="font-hud font-bold text-lg text-cyan-300 tracking-wider">
                LIVE SYSTEM MONITORING & TELEMETRY
              </h2>
              <TelemetryHUD telemetry={telemetry} />
            </div>
          </div>
        ) : activeTab === 'settings' ? (
          <div className="flex-1 p-6 overflow-hidden">
            <SettingsView 
              currentTheme={avatarTheme}
              onChangeTheme={setAvatarTheme}
              currentSize={avatarSize}
              onChangeSize={setAvatarSize}
              glowIntensity={glowIntensity}
              onChangeGlow={setGlowIntensity}
              scanlinesEnabled={scanlinesEnabled}
              onToggleScanlines={() => setScanlinesEnabled(!scanlinesEnabled)}
              onToggleFloatingMode={() => setIsFloatingWidget(true)}
              isFloatingMode={isFloatingWidget}
            />
          </div>
        ) : (
          /* Main Avatar & Core Holographic HUD Tab ('hud') */
          <div className="flex-1 p-4 lg:p-6 grid grid-cols-12 gap-4 lg:gap-6 overflow-y-auto lg:overflow-hidden">
            {/* Left Column: Central Animated Avatar / Core Reactor */}
            <div className="col-span-12 lg:col-span-7 flex flex-col justify-between bg-[#040e21]/40 border border-cyan-500/20 rounded-2xl p-6 backdrop-blur-sm hud-glow">
              <div className="flex justify-between items-center text-xs text-slate-400 font-hud">
                <div className="flex items-center space-x-2">
                  <span>HOLOGRAPHIC AVATAR MATRIX</span>
                  <span className="text-cyan-400 font-mono">NODE_ID: WIN11_HOST</span>
                </div>

                {/* Switch between Avatar Face and Arc Reactor */}
                <div className="flex items-center space-x-1 p-1 rounded-lg bg-[#020612] border border-cyan-500/30">
                  <button
                    onClick={() => setCenterMode('avatar')}
                    className={`flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-hud transition ${
                      centerMode === 'avatar'
                        ? 'bg-cyan-950 border border-cyan-400 text-cyan-300'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Sparkles className="w-3 h-3" />
                    <span>AVATAR FACE</span>
                  </button>
                  <button
                    onClick={() => setCenterMode('reactor')}
                    className={`flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-hud transition ${
                      centerMode === 'reactor'
                        ? 'bg-cyan-950 border border-cyan-400 text-cyan-300'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Disc className="w-3 h-3" />
                    <span>ARC REACTOR</span>
                  </button>
                </div>
              </div>

              {/* Centerpiece: Dynamic Animated Virtual AI Face or Arc Reactor */}
              <div className="my-auto py-4 flex flex-col items-center justify-center">
                {centerMode === 'avatar' ? (
                  <div className="flex flex-col items-center">
                    <JarvisAvatar 
                      state={agentState}
                      theme={avatarTheme}
                      size={avatarSize}
                      statusMessage={statusMessage}
                      audioAmplitude={audioAmplitude}
                      showScanlines={scanlinesEnabled}
                      interactive={true}
                      isMusicPlaying={spotifyState?.is_playing}
                      onClick={toggleVoiceRecognition}
                    />
                    <div className="mt-6 text-center max-w-sm">
                      <p className="font-hud text-xs text-cyan-300 tracking-wider">
                        {statusMessage}
                      </p>
                      <span className="text-[10px] text-slate-500 font-mono mt-1 block">
                        Click face or press Push-to-Talk to speak
                      </span>
                    </div>
                  </div>
                ) : (
                  <CoreArcReactor 
                    state={agentState} 
                    statusMessage={statusMessage}
                    onMicClick={toggleVoiceRecognition}
                  />
                )}
              </div>

              {/* Quick Status Bar */}
              <div className="border-t border-cyan-500/10 pt-3 flex justify-between items-center text-[11px] text-slate-400">
                <span>Wake-word: "Hey Jarvis" (or click Avatar / Mic button)</span>
                <span className="text-cyan-300">FastAPI + Lip-Sync Speech + WebSockets</span>
              </div>
            </div>

            {/* Right Column: Real-Time Telemetry & Chat Command Feed & Music Card */}
            <div className="col-span-12 lg:col-span-5 flex flex-col space-y-4 overflow-y-auto pr-1">
              {/* Top Right: System Telemetry HUD */}
              <div className="shrink-0">
                <TelemetryHUD telemetry={telemetry} />
              </div>

              {/* Middle Right: Spotify Music Controller Card */}
              <div className="shrink-0">
                <MusicCard 
                  playbackState={spotifyState}
                  onPlayPause={handleMusicPlayPause}
                  onNext={handleMusicNext}
                  onPrevious={handleMusicPrevious}
                  onVolumeChange={handleMusicVolumeChange}
                  onOpenSpotify={handleOpenSpotify}
                />
              </div>

              {/* Bottom Right: Real-time Command & Interaction Feed */}
              <div className="flex-1 min-h-[340px] flex flex-col">
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
