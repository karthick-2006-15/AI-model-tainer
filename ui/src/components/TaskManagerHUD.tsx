import React, { useState } from 'react';
import { 
  Play, 
  Pause, 
  Square, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  Layers, 
  Check, 
  X, 
  Terminal,
  RefreshCw
} from 'lucide-react';

interface Task {
  id: string;
  title: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'blocked';
  progress: number;
  application?: string;
  current_step?: string;
}

interface ApprovalChallenge {
  challenge_id: string;
  action_name: string;
  target_resource: string;
  message: string;
}

export const TaskManagerHUD: React.FC = () => {
  const [activeWorkflow] = useState<string>('Autonomous Research & Presentation');
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<string>('Synthesizing research report and PowerPoint slides');
  const [currentApp] = useState<string>('Microsoft PowerPoint // Win32 Desktop');

  const [tasks, setTasks] = useState<Task[]>([
    { id: '1', title: 'Web Research: Autonomous Warehouse Robots', status: 'success', progress: 100, application: 'Browser Engine', current_step: 'Completed 4 source queries' },
    { id: '2', title: 'Source Comparison & Factual Synthesis', status: 'success', progress: 100, application: 'Research Synthesizer', current_step: 'Cross-verified SLAM benchmarks' },
    { id: '3', title: 'Generate Word Document Report (.docx)', status: 'success', progress: 100, application: 'Microsoft Word', current_step: 'Formatted 3 sections & citations' },
    { id: '4', title: 'Generate PowerPoint Presentation (.pptx)', status: 'running', progress: 75, application: 'Microsoft PowerPoint', current_step: 'Building 16:9 slides' },
    { id: '5', title: 'File Integrity & Binary Verification', status: 'pending', progress: 0, application: 'File Manager', current_step: 'Awaiting completion' },
    { id: '6', title: 'Launch Desktop Viewer & Memory Sync', status: 'pending', progress: 0, application: 'Universal App Manager', current_step: 'Scheduled' },
  ]);

  const [pendingApproval, setPendingApproval] = useState<ApprovalChallenge | null>(null);
  const [toolLogs, setToolLogs] = useState<string[]>([
    '[21:42:10] [Browser] Scraped 3 reliable robotics sources.',
    '[21:42:15] [Research] Synthesized executive summary with zero hallucinations.',
    '[21:42:19] [Word] Written Report_Autonomous_Warehouse_Robots.docx (18.4 KB).',
    '[21:42:22] [PowerPoint] Creating 4 slides: Market, SLAM, Fleet, and ROI.',
  ]);

  const handlePauseResume = () => {
    setIsPaused(!isPaused);
    setToolLogs((prev) => [
      `[${new Date().toLocaleTimeString()}] Workflow ${isPaused ? 'Resumed' : 'Paused by user'}.`,
      ...prev
    ]);
  };

  const handleCancel = () => {
    setTasks((prev) => prev.map((t) => t.status === 'running' ? { ...t, status: 'failed' } : t));
    setCurrentStep('Workflow cancelled by user.');
    setToolLogs((prev) => [`[${new Date().toLocaleTimeString()}] Workflow cancelled.`, ...prev]);
  };

  const handleApprove = () => {
    setPendingApproval(null);
    setToolLogs((prev) => [`[${new Date().toLocaleTimeString()}] User approved action.`, ...prev]);
  };

  const handleDeny = () => {
    setPendingApproval(null);
    setToolLogs((prev) => [`[${new Date().toLocaleTimeString()}] User denied action.`, ...prev]);
  };

  return (
    <div className="h-full flex flex-col space-y-6 overflow-y-auto pr-2">
      {/* Top Banner / Current Execution Matrix */}
      <div className="bg-[#040e21]/70 border border-cyan-500/30 rounded-2xl p-6 backdrop-blur-md shadow-xl shadow-cyan-950/20">
        <div className="flex flex-wrap justify-between items-center gap-4 border-b border-cyan-500/10 pb-4">
          <div>
            <div className="flex items-center space-x-3">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse"></span>
              <h2 className="font-hud font-bold text-lg text-cyan-300 tracking-wider">
                ACTIVE WORKFLOW: {activeWorkflow}
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1 flex items-center space-x-2">
              <span>Current Step:</span>
              <span className="text-cyan-200 font-medium">{currentStep}</span>
              <span className="text-slate-600">•</span>
              <span className="text-emerald-400">App: {currentApp}</span>
            </p>
          </div>

          {/* Workflow Action Controls */}
          <div className="flex items-center space-x-3">
            <button
              onClick={handlePauseResume}
              className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold tracking-wide transition-all ${
                isPaused 
                  ? 'bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/30' 
                  : 'bg-amber-500/20 border border-amber-500/40 text-amber-300 hover:bg-amber-500/30'
              }`}
            >
              {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
              <span>{isPaused ? 'Resume Workflow' : 'Pause Workflow'}</span>
            </button>

            <button
              onClick={handleCancel}
              className="flex items-center space-x-2 px-4 py-2 bg-rose-500/20 border border-rose-500/40 text-rose-300 hover:bg-rose-500/30 rounded-xl text-xs font-semibold tracking-wide transition-all"
            >
              <Square className="w-3.5 h-3.5" />
              <span>Cancel Workflow</span>
            </button>
          </div>
        </div>

        {/* Pending Approval Challenge Alert */}
        {pendingApproval && (
          <div className="mt-4 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
              <div>
                <span className="text-xs font-bold text-amber-300 block">
                  PENDING LEVEL 3 AUTHORIZATION CHALLENGE
                </span>
                <span className="text-xs text-slate-300">{pendingApproval.message}</span>
              </div>
            </div>
            <div className="flex items-center space-x-2 shrink-0">
              <button
                onClick={handleApprove}
                className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-emerald-500 text-slate-950 font-bold text-xs hover:bg-emerald-400"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Approve</span>
              </button>
              <button
                onClick={handleDeny}
                className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs hover:bg-slate-700"
              >
                <X className="w-3.5 h-3.5" />
                <span>Deny</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Main Grid: DAG Steps & Live Tool Output Feed */}
      <div className="grid grid-cols-12 gap-6 flex-1 min-h-[380px]">
        {/* Left Column: DAG Subtask Execution Waves */}
        <div className="col-span-12 lg:col-span-7 bg-[#040e21]/40 border border-cyan-500/20 rounded-2xl p-6 backdrop-blur-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs font-hud text-slate-400 mb-4">
              <span className="flex items-center space-x-2">
                <Layers className="w-4 h-4 text-cyan-400" />
                <span>DAG SUBTASK PIPELINE</span>
              </span>
              <span className="text-cyan-400 font-mono">6 DECOMPOSED STEPS</span>
            </div>

            <div className="space-y-3">
              {tasks.map((task) => (
                <div
                  key={task.id}
                  className={`p-3.5 rounded-xl border transition-all ${
                    task.status === 'running'
                      ? 'bg-cyan-500/10 border-cyan-500/40 shadow-md shadow-cyan-500/10'
                      : task.status === 'success'
                      ? 'bg-slate-900/60 border-emerald-500/20'
                      : 'bg-slate-900/30 border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-2.5">
                      {task.status === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
                      {task.status === 'running' && <RefreshCw className="w-4 h-4 text-cyan-400 animate-spin shrink-0" />}
                      {task.status === 'pending' && <Clock className="w-4 h-4 text-slate-500 shrink-0" />}
                      <span className={`font-medium ${task.status === 'running' ? 'text-cyan-200' : 'text-slate-300'}`}>
                        {task.title}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                      {task.application}
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full bg-slate-800 h-1 rounded-full mt-2.5 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        task.status === 'success' ? 'bg-emerald-400' : 'bg-cyan-400'
                      }`}
                      style={{ width: `${task.progress}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="border-t border-cyan-500/10 pt-4 mt-4 flex items-center justify-between text-xs text-slate-400">
            <span>Execution Policy: Topological Waves with Async Parallel Dispatch</span>
            <span className="text-emerald-400 font-mono">Max Retries: 3</span>
          </div>
        </div>

        {/* Right Column: Real-Time Tool Activity & Resource Feed */}
        <div className="col-span-12 lg:col-span-5 flex flex-col space-y-6">
          {/* Tool Log Console */}
          <div className="flex-1 bg-[#040e21]/40 border border-cyan-500/20 rounded-2xl p-6 backdrop-blur-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs font-hud text-slate-400 mb-3">
                <span className="flex items-center space-x-2">
                  <Terminal className="w-4 h-4 text-cyan-400" />
                  <span>TOOL ACTIVITY STREAM</span>
                </span>
                <span className="text-emerald-400 font-mono text-[11px]">LIVE</span>
              </div>

              <div className="bg-slate-950/80 rounded-xl p-3 border border-slate-800 font-mono text-[11px] text-slate-300 space-y-2 max-h-[220px] overflow-y-auto">
                {toolLogs.map((log, idx) => (
                  <div key={idx} className="leading-relaxed">
                    <span className="text-cyan-400">&gt;</span> {log}
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Metrics Strip */}
            <div className="border-t border-cyan-500/10 pt-4 mt-4 grid grid-cols-2 gap-3 text-xs">
              <div className="bg-slate-900/40 p-2 rounded-lg border border-slate-800">
                <span className="text-slate-400 text-[10px] block">CPU IMPACT</span>
                <span className="text-cyan-300 font-mono font-bold">8.4% (Nominal)</span>
              </div>
              <div className="bg-slate-900/40 p-2 rounded-lg border border-slate-800">
                <span className="text-slate-400 text-[10px] block">MEMORY FOOTPRINT</span>
                <span className="text-cyan-300 font-mono font-bold">48 MB Allocated</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
