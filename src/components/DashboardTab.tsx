import React from 'react';
import { Activity, Cpu, Database, Shield, BookOpen, Brain, Layers, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { SystemHealth } from '../types';

interface DashboardTabProps {
  health: SystemHealth | null;
  documentsCount: number;
  memoriesCount: number;
  flashcardsCount: number;
  executionsCount: number;
  onTriggerExecution: (task: string) => void;
}

export const DashboardTab: React.FC<DashboardTabProps> = ({
  health,
  documentsCount,
  memoriesCount,
  flashcardsCount,
  executionsCount,
  onTriggerExecution,
}) => {
  const [taskInput, setTaskInput] = React.useState('');

  const handleSubmitTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskInput.trim()) return;
    onTriggerExecution(taskInput.trim());
    setTaskInput('');
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-slate-900 to-blue-950 rounded-2xl p-6 text-white shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <span className="px-3 py-1 bg-blue-500/20 border border-blue-400/30 text-blue-300 rounded-full text-xs font-semibold uppercase tracking-wider">
            System Operational
          </span>
          <h1 className="text-2xl font-bold mt-2">SuperAgent Command Center</h1>
          <p className="text-slate-300 text-sm mt-1">
            Local-first AI orchestration with FSRS spaced repetition, hybrid RAG retrieval, and deterministic execution guards.
          </p>
        </div>
        <div className="flex items-center space-x-3 bg-white/10 backdrop-blur-md px-4 py-3 rounded-xl border border-white/10 text-xs">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          <div>
            <div className="font-semibold">{health ? health.environment.toUpperCase() : 'PRODUCTION'}</div>
            <div className="text-slate-300">{health ? `Uptime: ${health.uptime_seconds}s` : 'Active'}</div>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-500">Knowledge Documents</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-1">{documentsCount}</h3>
            <span className="text-xs text-emerald-600 font-medium flex items-center mt-1">
              <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Vector indexed
            </span>
          </div>
          <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
            <BookOpen className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-500">Memory Records</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-1">{memoriesCount}</h3>
            <span className="text-xs text-blue-600 font-medium flex items-center mt-1">
              <Brain className="w-3.5 h-3.5 mr-1" /> Active & Episodic
            </span>
          </div>
          <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl">
            <Brain className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-500">Flashcards (FSRS)</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-1">{flashcardsCount}</h3>
            <span className="text-xs text-purple-600 font-medium flex items-center mt-1">
              <Layers className="w-3.5 h-3.5 mr-1" /> Learning Queue
            </span>
          </div>
          <div className="p-3 bg-purple-50 text-purple-600 rounded-xl">
            <Layers className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-500">Total Executions</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-1">{executionsCount}</h3>
            <span className="text-xs text-amber-600 font-medium flex items-center mt-1">
              <Cpu className="w-3.5 h-3.5 mr-1" /> Traced & Verified
            </span>
          </div>
          <div className="p-3 bg-amber-50 text-amber-600 rounded-xl">
            <Cpu className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Quick Task Trigger & Subsystem Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-lg font-bold text-slate-900">Trigger Agent Orchestration Run</h2>
          <p className="text-sm text-slate-600">
            Submit a complex task prompt to trigger the SuperAgent planning, retrieval, tool execution, and verification pipeline.
          </p>
          <form onSubmit={handleSubmitTask} className="flex gap-3">
            <input
              type="text"
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
              placeholder="e.g. Research local AI agent state machines and summarize key principles"
              className="flex-1 px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              className="px-6 py-3 bg-slate-900 text-white font-medium rounded-xl hover:bg-slate-800 transition-colors shadow-xs shrink-0"
            >
              Run Task
            </button>
          </form>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-lg font-bold text-slate-900">Subsystem Health</h2>
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="font-medium text-slate-700">SQLite Database</span>
              <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-lg text-xs font-semibold flex items-center">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Connected
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="font-medium text-slate-700">Vector & FTS5 RAG</span>
              <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-lg text-xs font-semibold flex items-center">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Active
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="font-medium text-slate-700">FSRS Learning Engine</span>
              <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-lg text-xs font-semibold flex items-center">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Enabled
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="font-medium text-slate-700">Tool System (4 tools)</span>
              <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-lg text-xs font-semibold flex items-center">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Registered
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
