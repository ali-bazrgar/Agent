import React from 'react';
import { Activity, Cpu, ShieldCheck, Database } from 'lucide-react';
import { SystemHealth } from '../types';

interface DashboardTabProps { health: SystemHealth | null; documentsCount: number; memoriesCount: number; flashcardsCount: number; executionsCount: number; onTriggerExecution: (task: string) => void; }

export const DashboardTab: React.FC<DashboardTabProps> = ({ health, documentsCount, memoriesCount, flashcardsCount, executionsCount, onTriggerExecution }) => {
  const [taskInput, setTaskInput] = React.useState('');
  const providers = health?.providers || {};
  const providerHealthy = (name: string) => providers[name]?.status === 'healthy';
  const overallHealthy = health?.status === 'ok' || health?.status === 'healthy';
  const handleSubmitTask = (e: React.FormEvent) => { e.preventDefault(); if (!taskInput.trim()) return; onTriggerExecution(taskInput.trim()); setTaskInput(''); };
  const healthRow = (label: string, ok: boolean, detail: string) => <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100 dark:bg-slate-900/40"><span className="font-medium text-slate-700 dark:text-slate-300">{label}</span><span className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center ${ok ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}><span className={`status-dot ${ok ? 'online' : 'offline'} mr-1.5`} />{detail}</span></div>;
  return <div className="space-y-6">
    <div className="page-header"><div><div className="eyebrow"><Activity className="w-4 h-4" /> SYSTEM OVERVIEW</div><h1>SuperAgent command center</h1><p>One view of persistent knowledge, memory, learning, execution telemetry, and provider health. Status labels are derived from runtime responses.</p></div><div className="status-chip"><span className={`status-dot ${overallHealthy ? 'online' : 'offline'}`} />{overallHealthy ? 'Operational' : 'Degraded'}</div></div>
    <div className="stats-strip"><div><span>Knowledge documents</span><strong>{documentsCount}</strong></div><div><span>Memory records</span><strong>{memoriesCount}</strong></div><div><span>Flashcards</span><strong>{flashcardsCount}</strong></div><div><span>Executions</span><strong>{executionsCount}</strong></div></div>
    <div className="settings-grid"><section className="settings-card"><div className="settings-card-title"><Cpu className="w-4 h-4" /><h2>Quick orchestration</h2></div><p className="muted text-sm mt-2">Dispatch a task through the same orchestrator used by chat and inspect it in Execution Center.</p><form onSubmit={handleSubmitTask} className="flex gap-2 mt-4"><input value={taskInput} onChange={(e) => setTaskInput(e.target.value)} placeholder="Research, analyze, calculate…" className="composer-input" /><button className="primary-button" type="submit" disabled={!taskInput.trim()}>Run</button></form></section><section className="settings-card"><div className="settings-card-title"><ShieldCheck className="w-4 h-4" /><h2>Provider health</h2></div><div className="space-y-2 mt-4">{healthRow('LLM', providerHealthy('llm'), providers.llm?.status || 'unknown')}{healthRow('Embeddings', providerHealthy('embedding'), providers.embedding?.status || 'unknown')}{healthRow('Reranker', providerHealthy('reranker'), providers.reranker?.status || 'unknown')}</div></section></div>
    <section className="settings-card"><div className="settings-card-title"><Database className="w-4 h-4" /><h2>Subsystems</h2></div><div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-4">{healthRow('SQLite', health?.database_status === 'healthy', health?.database_status || 'unknown')}{healthRow('Storage', health?.storage_status === 'healthy', health?.storage_status || 'unknown')}{healthRow('Learning', flashcardsCount >= 0, 'available')}</div><p className="muted text-xs mt-4">Database: {health?.database || 'not reported'} · Storage: {health?.storage || 'not reported'}</p></section>
  </div>;
};
