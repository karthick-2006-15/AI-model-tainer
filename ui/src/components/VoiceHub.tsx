import React, { useState } from 'react';
import { Mic, MicOff, Volume2, Globe, Radio, Play, CheckCircle2, Sliders } from 'lucide-react';
import { VoiceVisualizer } from './VoiceVisualizer';

interface Props {
  isListening: boolean;
  onToggleMic: () => void;
  voiceOutputEnabled: boolean;
  onToggleVoiceOutput: () => void;
}

export const VoiceHub: React.FC<Props> = ({
  isListening,
  onToggleMic,
  voiceOutputEnabled,
  onToggleVoiceOutput,
}) => {
  const [selectedLanguage, setSelectedLanguage] = useState('en-US');
  const [speechRate, setSpeechRate] = useState(1.0);
  const [pitch, setPitch] = useState(1.0);
  const [bargeInEnabled, setBargeInEnabled] = useState(true);
  const [continuousMode, setContinuousMode] = useState(true);
  const recentTranscripts = [
    { id: 1, text: "Hey Jarvis, search for recent AI automation developments.", lang: "en-US", time: "18:42:10", confidence: 0.98 },
    { id: 2, text: "Open WhatsApp and send message to father.", lang: "en-US", time: "18:45:22", confidence: 0.96 },
    { id: 3, text: "Innaiku weather eppadi irukku?", lang: "ta-IN", time: "18:48:05", confidence: 0.94 }
  ];

  const languages = [
    { code: 'en-US', label: 'English (US / UK)', flag: '🇺🇸' },
    { code: 'ta-IN', label: 'Tamil (தமிழ்)', flag: '🇮🇳' },
    { code: 'tanglish', label: 'Tanglish (Tamil-English)', flag: '🇮🇳' },
    { code: 'hi-IN', label: 'Hindi (हिंदी)', flag: '🇮🇳' },
    { code: 'hinglish', label: 'Hinglish (Hindi-English)', flag: '🇮🇳' },
  ];

  const testTTS = () => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const phrase = selectedLanguage.startsWith('ta') 
      ? 'வணக்கம், நான் ஜார்விஸ். உங்களுக்கு என்ன உதவி வேண்டும்?'
      : 'Hello, I am JARVIS. All voice subsystems are calibrated and operational.';
    const utterance = new SpeechSynthesisUtterance(phrase);
    utterance.rate = speechRate;
    utterance.pitch = pitch;
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div className="h-full flex flex-col space-y-6 overflow-y-auto pr-1">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-cyan-500/20 pb-4">
        <div>
          <h2 className="font-hud font-bold text-lg text-cyan-300 tracking-wider flex items-center gap-2">
            <Radio className="w-5 h-5 text-cyan-400 animate-pulse" />
            VOICE INTERACTION & DUPLEX HUB
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time speech pipeline: Wake-word Detection → VAD → Neural STT → Gemini Reasoning → Edge TTS
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={onToggleVoiceOutput}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-xs font-semibold transition ${
              voiceOutputEnabled
                ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300'
                : 'bg-rose-950/60 border-rose-500/40 text-rose-300'
            }`}
          >
            <Volume2 className="w-4 h-4" />
            <span>{voiceOutputEnabled ? 'TTS ACTIVE' : 'TTS MUTED'}</span>
          </button>

          <button
            onClick={onToggleMic}
            className={`flex items-center space-x-2 px-4 py-1.5 rounded-lg font-hud text-xs font-bold tracking-wider transition shadow-lg ${
              isListening
                ? 'bg-emerald-500 hover:bg-emerald-600 text-white shadow-emerald-500/30 animate-pulse'
                : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-cyan-600/30'
            }`}
          >
            {isListening ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
            <span>{isListening ? 'LISTENING (PUSH TO STOP)' : 'PUSH TO TALK'}</span>
          </button>
        </div>
      </div>

      {/* Grid: Left Column Waveform & Status, Right Column Settings */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left: Live Audio Feed & Waveform */}
        <div className="col-span-12 lg:col-span-7 flex flex-col space-y-4 bg-[#040e21]/70 border border-cyan-500/20 rounded-xl p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between text-xs font-hud text-cyan-300">
            <span>LIVE AUDIO STREAM // DUPLEX SPECTRUM</span>
            <span className="text-emerald-400 flex items-center gap-1 font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              48,000 Hz / 16-bit PCM
            </span>
          </div>

          <div className="h-32 bg-[#020612] border border-cyan-500/30 rounded-lg flex items-center justify-center p-4">
            <VoiceVisualizer isActive={isListening} color={isListening ? '#10b981' : '#06b6d4'} />
          </div>

          {/* Duplex State Indicators */}
          <div className="grid grid-cols-3 gap-3 pt-2">
            <div className="bg-[#030712] border border-cyan-500/20 rounded-lg p-3 text-center">
              <span className="text-[10px] text-slate-400 block font-hud">WAKE WORD</span>
              <span className="text-xs font-bold text-cyan-300">"Hey Jarvis"</span>
            </div>
            <div className="bg-[#030712] border border-cyan-500/20 rounded-lg p-3 text-center">
              <span className="text-[10px] text-slate-400 block font-hud">BARGE-IN CUTOFF</span>
              <span className="text-xs font-bold text-emerald-400">Zero-Latency Active</span>
            </div>
            <div className="bg-[#030712] border border-cyan-500/20 rounded-lg p-3 text-center">
              <span className="text-[10px] text-slate-400 block font-hud">ACTIVE LANGUAGE</span>
              <span className="text-xs font-bold text-cyan-300">{selectedLanguage}</span>
            </div>
          </div>

          {/* Recent Transcripts */}
          <div className="mt-4">
            <span className="text-xs font-hud text-slate-300 tracking-wider block mb-2">
              REAL-TIME TRANSCRIPT STREAM
            </span>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {recentTranscripts.map((t) => (
                <div key={t.id} className="p-2.5 rounded-lg bg-[#030816] border border-cyan-900/40 text-xs flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span className="text-slate-200">"{t.text}"</span>
                  </div>
                  <div className="flex items-center space-x-2 text-[10px] text-slate-400 font-mono">
                    <span className="px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-800/40 text-cyan-300">{t.lang}</span>
                    <span>{t.time}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Multilingual & Calibration Settings */}
        <div className="col-span-12 lg:col-span-5 flex flex-col space-y-4 bg-[#040e21]/70 border border-cyan-500/20 rounded-xl p-5 backdrop-blur-sm">
          <div className="flex items-center space-x-2 text-xs font-hud text-cyan-300">
            <Globe className="w-4 h-4 text-cyan-400" />
            <span>MULTILINGUAL ROUTING</span>
          </div>

          <div className="grid grid-cols-1 gap-2">
            {languages.map((l) => (
              <button
                key={l.code}
                onClick={() => setSelectedLanguage(l.code)}
                className={`flex items-center justify-between p-2.5 rounded-lg text-xs font-medium border transition ${
                  selectedLanguage === l.code
                    ? 'bg-cyan-950/80 border-cyan-400 text-cyan-200 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                    : 'bg-[#030816] border-cyan-900/30 text-slate-400 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <span className="text-base">{l.flag}</span>
                  <span>{l.label}</span>
                </div>
                {selectedLanguage === l.code && <CheckCircle2 className="w-4 h-4 text-cyan-400" />}
              </button>
            ))}
          </div>

          {/* Continuous Mode & Barge-in Controls */}
          <div className="pt-3 border-t border-cyan-500/20 space-y-2">
            <div className="flex items-center justify-between p-2 rounded-lg bg-[#030816] text-xs">
              <span className="text-slate-300">Continuous Dialogue Mode</span>
              <button
                onClick={() => setContinuousMode(!continuousMode)}
                className={`w-9 h-5 rounded-full p-0.5 transition ${continuousMode ? 'bg-cyan-500' : 'bg-slate-700'}`}
              >
                <div className={`w-4 h-4 rounded-full bg-white transition ${continuousMode ? 'translate-x-4' : ''}`} />
              </button>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-[#030816] text-xs">
              <span className="text-slate-300">Duplex Barge-in Interrupt</span>
              <button
                onClick={() => setBargeInEnabled(!bargeInEnabled)}
                className={`w-9 h-5 rounded-full p-0.5 transition ${bargeInEnabled ? 'bg-emerald-500' : 'bg-slate-700'}`}
              >
                <div className={`w-4 h-4 rounded-full bg-white transition ${bargeInEnabled ? 'translate-x-4' : ''}`} />
              </button>
            </div>
          </div>

          {/* Voice Tuning Sliders */}
          <div className="pt-3 border-t border-cyan-500/20 space-y-3">
            <div className="flex items-center space-x-2 text-xs font-hud text-cyan-300">
              <Sliders className="w-3.5 h-3.5 text-cyan-400" />
              <span>SYNTHESIS CALIBRATION</span>
            </div>

            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1">
                <span>Speech Speed Rate</span>
                <span className="font-mono text-cyan-300">{speechRate.toFixed(1)}x</span>
              </div>
              <input
                type="range"
                min="0.8"
                max="1.5"
                step="0.1"
                value={speechRate}
                onChange={(e) => setSpeechRate(parseFloat(e.target.value))}
                className="w-full accent-cyan-400 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1">
                <span>Voice Pitch</span>
                <span className="font-mono text-cyan-300">{pitch.toFixed(1)}</span>
              </div>
              <input
                type="range"
                min="0.8"
                max="1.4"
                step="0.1"
                value={pitch}
                onChange={(e) => setPitch(parseFloat(e.target.value))}
                className="w-full accent-cyan-400 cursor-pointer"
              />
            </div>

            {/* Test Voice Button */}
            <button
              onClick={testTTS}
              className="w-full flex items-center justify-center space-x-2 py-2 rounded-lg bg-cyan-950/60 hover:bg-cyan-900/80 border border-cyan-600/50 text-cyan-300 text-xs font-hud font-bold tracking-wider transition"
            >
              <Play className="w-3.5 h-3.5" />
              <span>AUDIT VOICE OUTPUT</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
