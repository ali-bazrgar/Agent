import React, { useState } from 'react';
import { SystemHealth, MemoryRecord, Document, Flashcard, ExecutionState } from '../types';
import { Activity, Brain, BookOpen, Cpu, Play, CheckCircle2, Clock, Server, HardDrive, ShieldCheck } from 'lucide-react';

interface OverviewTabProps {
  health: SystemHealth | null;
  memories: MemoryRecord[];
  documents: Document[];
  flashcards: Flashcard[];
  executions: ExecutionState[];
  onTriggerExecution: (description: string) => void;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  health,
  memories,
  documents,
  flashcards,
  executions,
  onTriggerExecution,
}) => {
  const [taskInput, setTaskInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRun = (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskInput.trim()) return;
    setIsSubmitting(true);
    onTriggerExecution(taskInput);
    setTaskInput('');
    setTimeout(() => setIsSubmitting(false), 800);
  };

  const totalChunks = documents.reduce((acc, d) => acc + (d.chunks?.length || 0), 0);
  const activeMemories = memories.filter((m) => m.status === 'active').length;
  const completedExecutions = executions.filter((e) => e.status === 'completed').length;

  return (
    <div className="space-y-6">
      {/* Quick Launch Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 rounded-2xl p-6 text-white shadow-md border border-slate-800">
        <div className="max-w-3xl space-y-3">
          <div className="inline-flex items-center space-x-2 px-2.5 py-1 bg-blue-500/10 border border-blue-400/20 text-blue-300 rounded-full text-xs font-mono">
            <Activity className="w-3.5 h-3.5" />
            <span>Agent Orchestrator Ready</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">SuperAgent Local Core Engine</h1>
          <p className="text-slate-300 text-sm leading-relaxed">
            Local-first AI orchestration runtime featuring structured 7-type memory distillation, vector/lexical knowledge chunking, spaced repetition learning, and deterministic execution logs.
          </p>
          
          <form onSubmit={handleRun} className="flex gap-2 pt-2">
            <input
              type="text"
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
              placeholder="Enter an orchestration prompt (e.g. 'Synthesize memory records for RAG context')..."
              className="flex-1 px-4 py-2.5 bg-slate-950/80 border border-slate-700 rounded-xl text-sm text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={isSubmitting || !taskInput.trim()}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors flex items-center space-x-2 shadow-sm"
            >
              <Play className="w-4 h-4" />
              <span>{isSubmitting ? 'Dispatching...' : 'Dispatch Run'}</span>
            </button>
          </form>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Memories</span>
            <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
              <Brain className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">{activeMemories}</div>
          <p className="text-xs text-slate-500">Working, session & semantic records</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Indexed Documents</span>
            <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
              <BookOpen className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">{documents.length}</div>
          <p className="text-xs text-slate-500">{totalChunks} search chunks available</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Execution Runs</span>
            <div className="p-2 bg-purple-50 text-purple-600 rounded-lg">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">{executions.length}</div>
          <p className="text-xs text-slate-500">{completedExecutions} completed runs</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Flashcards</span>
            <div className="p-2 bg-amber-50 text-amber-600 rounded-lg">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">{flashcards.length}</div>
          <p className="text-xs text-slate-500">Spaced repetition deck items</p>
        </div>
      </div>

      {/* System Diagnostics & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* System Diagnostics Box */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <h2 className="font-bold text-slate-900 text-base flex items-center space-x-2">
            <Server className="w-4 h-4 text-slate-700" />
            <span>System Diagnostics</span>
          </h2>

          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">API Status</span>
              <span className="inline-flex items-center space-x-1 font-semibold text-emerald-600">
                <CheckCircle2 className="w-4 h-4" />
                <span>Operational</span>
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Environment</span>
              <span className="font-mono text-xs px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md">
                {health?.environment || 'development'}
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Database Target</span>
              <span className="font-mono text-xs text-slate-700 flex items-center space-x-1">
                <HardDrive className="w-3.5 h-3.5 text-slate-400" />
                <span>{health?.database || 'data/superagent.db'}</span>
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">System Uptime</span>
              <span className="font-mono text-xs text-slate-700 flex items-center space-x-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>{health ? `${health.uptime_seconds}s` : '0s'}</span>
              </span>
            </div>
          </div>
        </div>

        {/* Recent Agent Executions Panel */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-slate-900 text-base flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-slate-700" />
              <span>Recent Orchestration Executions</span>
            </h2>
            <span className="text-xs text-slate-500 font-mono">/api/v1/executions</span>
          </div>

          <div className="space-y-3">
            {executions.slice(0, 4).map((exec) => (
              <div
                key={exec.execution_id}
                className="p-4 bg-slate-50 border border-slate-200/80 rounded-xl space-y-2 hover:border-slate-300 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className={`w-2 h-2 rounded-full ${
                      exec.status === 'completed' ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'
                    }`} />
                    <span className="font-mono text-xs font-semibold text-slate-800">{exec.execution_id}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded-md text-xs font-medium ${
                    exec.status === 'completed' 
                      ? 'bg-emerald-100 text-emerald-800' 
                      : 'bg-amber-100 text-amber-800'
                  }`}>
                    {exec.status.toUpperCase()}
                  </span>
                </div>

                <p className="text-xs text-slate-600 font-mono truncate">
                  {exec.metadata?.task || exec.request_id}
                </p>

                <div className="flex items-center justify-between text-xs text-slate-500 pt-1 border-t border-slate-200/60">
                  <span>Model Calls: {exec.model_calls} · Tool Calls: {exec.tool_calls}</span>
                  <span>{new Date(exec.created_at).toLocaleTimeString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};
