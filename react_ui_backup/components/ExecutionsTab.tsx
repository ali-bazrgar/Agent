import React, { useState } from 'react';
import { ExecutionState } from '../types';
import { Cpu, Terminal, Play, RefreshCw, CheckCircle2, Clock, AlertCircle } from 'lucide-react';

interface ExecutionsTabProps {
  executions: ExecutionState[];
  onTriggerExecution: (description: string) => void;
}

export const ExecutionsTab: React.FC<ExecutionsTabProps> = ({
  executions,
  onTriggerExecution,
}) => {
  const [task, setTask] = useState('');
  const [selectedExec, setSelectedExec] = useState<ExecutionState | null>(executions[0] || null);

  const handleRun = (e: React.FormEvent) => {
    e.preventDefault();
    if (!task.trim()) return;
    onTriggerExecution(task);
    setTask('');
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center space-x-2">
            <Cpu className="w-5 h-5 text-purple-600" />
            <h2 className="text-lg font-bold text-slate-900">Agent Execution Engine</h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Tracks request lifecycle, status, model calls, tool calls, and retries deterministically.
          </p>
        </div>

        <form onSubmit={handleRun} className="flex gap-2">
          <input
            type="text"
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="Trigger new execution task..."
            className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
          <button
            type="submit"
            disabled={!task.trim()}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl transition-colors flex items-center space-x-1 shadow-xs"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Dispatch</span>
          </button>
        </form>
      </div>

      {/* Main Grid: Executions List + Log Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Executions List */}
        <div className="space-y-3">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Execution History</h3>

          {executions.map((exec) => {
            const isSelected = selectedExec?.execution_id === exec.execution_id;
            return (
              <div
                key={exec.execution_id}
                onClick={() => setSelectedExec(exec)}
                className={`p-4 rounded-xl border cursor-pointer transition-all space-y-2 ${
                  isSelected
                    ? 'bg-purple-50/50 border-purple-300 ring-1 ring-purple-400'
                    : 'bg-white border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-slate-900">{exec.execution_id}</span>
                  <span className={`px-2 py-0.5 rounded-md text-[10px] font-mono font-bold uppercase ${
                    exec.status === 'completed'
                      ? 'bg-emerald-100 text-emerald-800'
                      : exec.status === 'running'
                      ? 'bg-amber-100 text-amber-800 animate-pulse'
                      : 'bg-slate-100 text-slate-700'
                  }`}>
                    {exec.status}
                  </span>
                </div>

                <p className="text-xs text-slate-600 font-mono truncate">
                  {exec.metadata?.task || exec.request_id}
                </p>

                <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono pt-1 border-t border-slate-100">
                  <span>Models: {exec.model_calls} · Tools: {exec.tool_calls}</span>
                  <span>{new Date(exec.created_at).toLocaleTimeString()}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Execution Log Inspector */}
        <div className="lg:col-span-2 bg-slate-950 rounded-2xl p-6 text-slate-200 border border-slate-800 space-y-4 shadow-md font-mono">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <Terminal className="w-4 h-4 text-purple-400" />
              <span className="text-sm font-bold text-white">
                {selectedExec ? selectedExec.execution_id : 'Select an Execution'}
              </span>
            </div>

            {selectedExec && (
              <div className="flex items-center space-x-3 text-xs text-slate-400">
                <span>Model Calls: {selectedExec.model_calls}</span>
                <span>Tool Calls: {selectedExec.tool_calls}</span>
                <span>Retries: {selectedExec.retries}</span>
              </div>
            )}
          </div>

          {selectedExec ? (
            <div className="space-y-3">
              <div className="text-xs text-slate-400">
                Task: <span className="text-purple-300">{selectedExec.metadata?.task || selectedExec.request_id}</span>
              </div>

              <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 space-y-2 text-xs text-slate-300 max-h-80 overflow-y-auto">
                <div className="text-slate-500 pb-1 border-b border-slate-800 text-[11px]">=== EXECUTION LOG STREAM ===</div>
                {selectedExec.logs?.map((log, idx) => (
                  <div key={idx} className="flex space-x-2 leading-relaxed">
                    <span className="text-slate-600 select-none">&gt;</span>
                    <span className="text-slate-200">{log}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-slate-500 text-xs">
              Select an execution run from the history to view telemetry logs.
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
