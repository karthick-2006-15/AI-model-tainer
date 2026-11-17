import React from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, ExternalLink, Disc } from 'lucide-react';
import { SpotifyPlaybackState } from '../types/hud';

interface Props {
  playbackState: SpotifyPlaybackState | null;
  onPlayPause: () => void;
  onNext: () => void;
  onPrevious: () => void;
  onVolumeChange: (vol: number) => void;
  onOpenSpotify?: () => void;
}

export const MusicCard: React.FC<Props> = ({
  playbackState,
  onPlayPause,
  onNext,
  onPrevious,
  onVolumeChange,
  onOpenSpotify,
}) => {
  const isPlaying = playbackState?.is_playing ?? false;
  const isRunning = playbackState?.is_running ?? false;
  const track = playbackState?.track;
  const title = track?.title && track.title !== "No track playing" ? track.title : "Ready for music";
  const artist = track?.artist && track.artist !== "Spotify" ? track.artist : isRunning ? "Spotify Desktop Ready" : "Spotify Standing By";
  const volume = playbackState?.volume ?? 50;

  // Format milliseconds to mm:ss
  const formatTime = (ms: number) => {
    if (!ms || ms <= 0) return '0:00';
    const totalSecs = Math.floor(ms / 1000);
    const mins = Math.floor(totalSecs / 60);
    const secs = totalSecs % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const durationMs = track?.duration_ms || 215000;
  const progressMs = track?.progress_ms || 0;
  const progressPercent = durationMs > 0 ? Math.min(100, Math.max(0, (progressMs / durationMs) * 100)) : 0;

  return (
    <div className="bg-[#030c1d]/85 border border-cyan-500/25 rounded-xl p-4 backdrop-blur-md hud-glow relative overflow-hidden group">
      {/* Background ambient vinyl aura */}
      <div 
        className="absolute -right-8 -bottom-8 w-32 h-32 rounded-full opacity-10 pointer-events-none transition-all duration-1000"
        style={{
          background: isPlaying ? 'radial-gradient(circle, #10b981 0%, transparent 70%)' : 'radial-gradient(circle, #06b6d4 0%, transparent 70%)'
        }}
      />

      {/* Header bar */}
      <div className="flex justify-between items-center text-[10px] text-slate-400 font-hud tracking-wider pb-2 border-b border-cyan-500/15 mb-3">
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1.5">
            <span className={`w-2 h-2 rounded-full ${isPlaying ? 'bg-emerald-400 animate-pulse' : isRunning ? 'bg-amber-400' : 'bg-slate-500'}`} />
            <span className="text-cyan-300 font-bold">SPOTIFY MEDIA CONTROLLER</span>
          </div>
          <span className="text-slate-600">//</span>
          <span className="text-slate-400 text-[9px] font-mono">{playbackState?.device || 'Windows PC'}</span>
        </div>

        {onOpenSpotify && (
          <button
            onClick={onOpenSpotify}
            title="Open Spotify Desktop Window"
            className="flex items-center space-x-1 text-slate-400 hover:text-cyan-300 transition text-[9px]"
          >
            <span>DESKTOP APP</span>
            <ExternalLink className="w-2.5 h-2.5" />
          </button>
        )}
      </div>

      {/* Main Track & Controls Row */}
      <div className="flex items-center space-x-3.5">
        {/* Animated Vinyl Album Art */}
        <div className="relative shrink-0 w-13 h-13 rounded-lg bg-gradient-to-br from-slate-900 to-black border border-cyan-500/30 flex items-center justify-center p-2.5 shadow-lg">
          <div className={`w-8 h-8 rounded-full border border-cyan-400/30 flex items-center justify-center ${isPlaying ? 'animate-spin-slow' : ''}`}>
            <Disc className={`w-5 h-5 ${isPlaying ? 'text-emerald-400' : 'text-cyan-400'}`} />
          </div>
          {isPlaying && (
            <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
          )}
        </div>

        {/* Track Title and Artist details */}
        <div className="flex-1 min-w-0 pr-1">
          <h4 className="text-xs font-semibold text-slate-100 truncate tracking-wide" title={title}>
            {title}
          </h4>
          <p className="text-[11px] text-slate-400 truncate mt-0.5" title={artist}>
            {artist}
          </p>

          {/* Playback Progress Bar */}
          <div className="mt-2 space-y-1">
            <div className="w-full bg-slate-800/80 rounded-full h-1 overflow-hidden">
              <div 
                className="bg-gradient-to-r from-cyan-500 to-emerald-400 h-full rounded-full transition-all duration-300"
                style={{ width: `${isPlaying ? (progressPercent || 35) : 0}%` }}
              />
            </div>
            <div className="flex justify-between text-[9px] font-mono text-slate-500">
              <span>{formatTime(progressMs)}</span>
              <span>{formatTime(durationMs)}</span>
            </div>
          </div>
        </div>

        {/* Transport Controls */}
        <div className="flex items-center space-x-1.5 shrink-0">
          <button
            onClick={onPrevious}
            title="Previous Track"
            className="p-1.5 rounded-lg bg-[#08152e] hover:bg-cyan-950/60 border border-cyan-900/40 text-slate-300 hover:text-cyan-300 transition"
          >
            <SkipBack className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onPlayPause}
            title={isPlaying ? "Pause Music" : "Play Music"}
            className="p-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold transition shadow-md shadow-cyan-500/20 active:scale-95"
          >
            {isPlaying ? (
              <Pause className="w-4 h-4 fill-current" />
            ) : (
              <Play className="w-4 h-4 fill-current ml-0.5" />
            )}
          </button>

          <button
            onClick={onNext}
            title="Next Track"
            className="p-1.5 rounded-lg bg-[#08152e] hover:bg-cyan-950/60 border border-cyan-900/40 text-slate-300 hover:text-cyan-300 transition"
          >
            <SkipForward className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Volume Bar footer */}
      <div className="mt-3 pt-2.5 border-t border-cyan-500/10 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center space-x-2 w-full max-w-xs">
          {volume === 0 ? (
            <VolumeX className="w-3.5 h-3.5 text-rose-400 shrink-0" />
          ) : (
            <Volume2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          )}
          <input
            type="range"
            min="0"
            max="100"
            value={volume}
            onChange={(e) => onVolumeChange(Number(e.target.value))}
            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
            title={`Volume: ${volume}%`}
          />
          <span className="text-[10px] font-mono text-slate-400 w-8 text-right shrink-0">
            {volume}%
          </span>
        </div>

        <span className="text-[10px] text-slate-500 font-hud ml-4 shrink-0">
          VOICE: "PLAY [SONG]"
        </span>
      </div>
    </div>
  );
};
