import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '../types/hud';
import { Send, Terminal, Bot, User, Sparkles, Mic, MicOff } from 'lucide-react';

interface Props {
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  isStreaming?: boolean;
  onToggleMic?: () => void;
  isListening?: boolean;
}

export const ChatFeed: React.FC<Props> = ({ 
  messages, 
  onSendMessage, 
  isStreaming,
  onToggleMic,
  isListening = false
}) => {
  const [inputText, setInputText] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputText.trim()) {
      onSendMessage(inputText);
      setInputText('');
    }
  };

  const handleQuickPrompt = (prompt: string) => {
    onSendMessage(prompt);
  };

  return (
    <div className="flex flex-col h-full bg-[#081226]/80 border border-cyan-500/30 rounded-xl backdrop-blur-md hud-glow overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-cyan-500/20 px-4 py-3 bg-[#040e21]">
        <div className="flex items-center space-x-2 text-cyan-400 font-hud text-xs tracking-wider">
          <Terminal className="w-4 h-4 text-cyan-300" />
          <span>NEURAL COMMAND FEED</span>
        </div>
        <span className="text-[10px] text-emerald-400 font-hud flex items-center space-x-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
          <span>ONLINE</span>
        </span>
      </div>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500 space-y-3">
            <Bot className="w-10 h-10 text-cyan-500/40" />
            <p className="text-xs max-w-xs font-medium">
              JARVIS voice and text input ready. Speak or type instructions below to orchestrate system actions.
            </p>
            <div className="flex flex-wrap justify-center gap-2 mt-2">
              <button 
                onClick={() => handleQuickPrompt("Check laptop storage")}
                className="text-[11px] bg-cyan-950/60 hover:bg-cyan-900 border border-cyan-800/40 text-cyan-300 px-2.5 py-1 rounded transition"
              >
                "Check laptop storage"
              </button>
              <button 
                onClick={() => handleQuickPrompt("Open VS Code")}
                className="text-[11px] bg-cyan-950/60 hover:bg-cyan-900 border border-cyan-800/40 text-cyan-300 px-2.5 py-1 rounded transition"
              >
                "Open VS Code"
              </button>
              <button 
                onClick={() => handleQuickPrompt("Find all PDFs in Downloads")}
                className="text-[11px] bg-cyan-950/60 hover:bg-cyan-900 border border-cyan-800/40 text-cyan-300 px-2.5 py-1 rounded transition"
              >
                "Find PDFs in Downloads"
              </button>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div 
              key={msg.id}
              className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div className="flex items-center space-x-1.5 text-[10px] text-slate-400 mb-1 px-1">
                {msg.sender === 'user' ? (
                  <>
                    <span className="font-mono">{msg.timestamp}</span>
                    <span className="text-cyan-400 font-semibold flex items-center gap-1">
                      YOU <User className="w-3 h-3" />
                    </span>
                  </>
                ) : (
                  <>
                    <span className="text-cyan-400 font-semibold flex items-center gap-1">
                      <Sparkles className="w-3 h-3 text-cyan-300" /> JARVIS
                    </span>
                    <span className="font-mono">{msg.timestamp}</span>
                  </>
                )}
              </div>

              <div 
                className={`max-w-[85%] rounded-xl px-4 py-2.5 text-xs font-medium leading-relaxed ${
                  msg.sender === 'user'
                    ? 'bg-cyan-950/70 border border-cyan-700/60 text-cyan-100 rounded-tr-none'
                    : 'bg-[#040e21] border border-cyan-900/60 text-slate-200 rounded-tl-none shadow-md'
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="p-3 bg-[#040e21] border-t border-cyan-500/20 flex gap-2">
        <input 
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Command JARVIS (e.g. 'Open VS Code', 'Organize downloads')..."
          className="flex-1 bg-[#020617] border border-cyan-800/50 rounded-lg px-3.5 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition"
        />
        {onToggleMic && (
          <button
            type="button"
            onClick={onToggleMic}
            title={isListening ? "Listening... Click to cancel" : "Click to speak with voice"}
            className={`px-3 py-2 rounded-lg text-xs font-semibold flex items-center justify-center transition border ${
              isListening
                ? 'bg-emerald-500/20 border-emerald-400 text-emerald-300 animate-pulse shadow-[0_0_12px_#10b981]'
                : 'bg-cyan-950/60 border-cyan-700/60 text-cyan-300 hover:bg-cyan-900/60 hover:border-cyan-400'
            }`}
          >
            {isListening ? (
              <MicOff className="w-4 h-4 text-emerald-400 animate-bounce" />
            ) : (
              <Mic className="w-4 h-4 text-cyan-400" />
            )}
          </button>
        )}
        <button 
          type="submit"
          className="bg-cyan-600 hover:bg-cyan-500 text-white px-3.5 py-2 rounded-lg text-xs font-hud font-semibold flex items-center space-x-1.5 shadow-md shadow-cyan-600/30 transition"
        >
          <span>EXECUTE</span>
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};
