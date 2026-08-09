import React, { useEffect, useMemo, useState } from 'react';
import { Activity, BrainCircuit, CheckCircle2, Cpu, Database, Download, Gauge, Moon, Network, Save, Settings, ShieldCheck, SlidersHorizontal, Sun, Wifi, Zap } from 'lucide-react';
import { exportDiagnostics, isDiagnosticsEnabled, setDiagnosticsEnabled } from '../diagnostics';

interface Props { darkMode: boolean; setDarkMode: (value: boolean) => void; }

type Runtime = { model_id: string | null; context_window_tokens: number; max_output_tokens: number | null; temperature: number; top_p: number; timeout_seconds: number; context_allocation: { use_conversation_history: boolean; use_memory: boolean; use_knowledge: boolean; max_memory_tokens: number | null; max_knowledge_tokens: number | null; max_history_tokens: number | null; min_retrieval_score: number | null; reserve_output_tokens: number } };

const fallbackRuntime = (config: any): Runtime => ({
  model_id: config?.llm?.modelId ?? null,
  context_window_tokens: config?.llm?.runtime?.context_window_tokens ?? config?.llm?.contextWindowTokens ?? 8192,
  max_output_tokens: config?.llm?.runtime?.max_output_tokens ?? null,
  temperature: config?.llm?.runtime?.temperature ?? config?.llm?.temperature ?? 0.7,
  top_p: config?.llm?.runtime?.top_p ?? config?.llm?.topP ?? 1,
  timeout_seconds: config?.llm?.runtime?.timeout_seconds ?? 60,
  context_allocation: config?.llm?.runtime?.context_allocation ?? { use_conversation_history: true, use_memory: true, use_knowledge: true, max_memory_tokens: null, max_knowledge_tokens: null, max_history_tokens: null, min_retrieval_score: null, reserve_output_tokens: 0 },
});

export const SettingsCenterTab: React.FC<Props> = ({ darkMode, setDarkMode }) => {
  const [config, setConfig] = useState<any>(null); const [health, setHealth] = useState<any>(null); const [error, setError] = useState('');
  const [runtime, setRuntime] = useState<Runtime | null>(null); const [saving, setSaving] = useState(false); const [saved, setSaved] = useState(false);
  const [diagnosticsEnabled, setDiagEnabled] = useState(isDiagnosticsEnabled()); const [diagnosticSession, setDiagnosticSession] = useState('');

  const load = () => Promise.all([fetch('/api/v1/config').then((r) => r.json()), fetch('/api/v1/health').then((r) => r.json()), fetch('/api/v1/diagnostics/status').then((r) => r.json())]).then(([c, h, d]) => { setConfig(c); setHealth(h); setRuntime(fallbackRuntime(c)); setDiagnosticSession(d.session_id || ''); }).catch((e) => setError(e instanceof Error ? e.message : 'Failed to load runtime settings'));
  useEffect(() => { void load(); }, []);

  const modelMaximum = config?.context?.modelMaximumTokens ?? config?.llm?.capabilities?.context_window_tokens ?? null;
  const contextLabel = useMemo(() => modelMaximum ? `Model maximum: ${Number(modelMaximum).toLocaleString()} tokens` : 'Model capability not reported; manual value allowed', [modelMaximum]);
  const updateAllocation = (key: string, value: any) => setRuntime((r) => r ? ({ ...r, context_allocation: { ...r.context_allocation, [key]: value } }) : r);
  const saveRuntime = async () => {
    if (!runtime) return; setSaving(true); setSaved(false); setError('');
    try { const response = await fetch('/api/v1/config/runtime', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(runtime) }); const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'Runtime configuration was rejected'); setRuntime(data.runtime); setSaved(true); setTimeout(() => setSaved(false), 2500); } catch (e) { setError(e instanceof Error ? e.message : 'Failed to save runtime'); } finally { setSaving(false); }
  };
  const toggleDiagnostics = (value: boolean) => { setDiagEnabled(value); setDiagnosticsEnabled(value); window.location.reload(); };

  return <div className="space-y-6">
    <div className="page-header"><div><div className="eyebrow"><Settings className="w-4 h-4" /> SETTINGS</div><h1>Runtime control center</h1><p>Configure the active model profile, context allocation, memory/knowledge behavior and provider surfaces from one place.</p></div></div>
    {error && <div className="error-banner">{error}</div>}

    <div className="settings-grid">
      <section className="settings-card"><div className="settings-card-title"><Sun className="w-4 h-4" /><h2>Appearance</h2></div><div className="theme-choice-grid"><button className={`theme-choice ${!darkMode ? 'selected' : ''}`} onClick={() => setDarkMode(false)}><Sun className="w-5 h-5" /><span>Light</span><small>Clean workspace</small></button><button className={`theme-choice ${darkMode ? 'selected' : ''}`} onClick={() => setDarkMode(true)}><Moon className="w-5 h-5" /><span>Dark</span><small>Low-glare workspace</small></button></div></section>
      <section className="settings-card"><div className="settings-card-title"><Wifi className="w-4 h-4" /><h2>System health</h2></div><div className="runtime-list"><div><span>Backend</span><strong><i className={`status-dot ${health?.status === 'ok' || health?.status === 'healthy' ? 'online' : 'offline'}`} />{health?.status || 'unknown'}</strong></div><div><span>Database</span><strong>{health?.database || 'unknown'}</strong></div><div><span>Storage</span><strong>{health?.storage || 'unknown'}</strong></div></div></section>
    </div>

    {runtime && <>
      <section className="settings-card"><div className="settings-card-title"><Gauge className="w-4 h-4" /><h2>LLM runtime profile</h2></div><p className="muted text-sm">The context value is the actual runtime ceiling selected for this model. It is never capped at 128K by the application. If the provider reports a larger capability, it is available here.</p><div className="settings-form-grid">
        <label>Model ID<input value={runtime.model_id || ''} onChange={(e) => setRuntime({ ...runtime, model_id: e.target.value || null })} placeholder="provider/model" /></label>
        <label>Context window<input type="number" min={256} max={modelMaximum || undefined} step={256} value={runtime.context_window_tokens} onChange={(e) => setRuntime({ ...runtime, context_window_tokens: Number(e.target.value) })} /></label>
        <label>Max output tokens<input type="number" min={1} value={runtime.max_output_tokens ?? ''} onChange={(e) => setRuntime({ ...runtime, max_output_tokens: e.target.value ? Number(e.target.value) : null })} placeholder="Unlimited / model limit" /></label>
        <label>Temperature<input type="number" min={0} max={2} step={0.01} value={runtime.temperature} onChange={(e) => setRuntime({ ...runtime, temperature: Number(e.target.value) })} /></label>
        <label>Top P<input type="number" min={0.01} max={1} step={0.01} value={runtime.top_p} onChange={(e) => setRuntime({ ...runtime, top_p: Number(e.target.value) })} /></label>
        <label>Provider timeout (s)<input type="number" min={1} value={runtime.timeout_seconds} onChange={(e) => setRuntime({ ...runtime, timeout_seconds: Number(e.target.value) })} /></label>
      </div><div className="settings-inline-note"><Cpu className="w-4 h-4" />{contextLabel}</div></section>

      <section className="settings-card"><div className="settings-card-title"><BrainCircuit className="w-4 h-4" /><h2>Context intelligence</h2></div><p className="muted text-sm">The selected context size stays fixed. These controls decide what the agent retrieves into it, so the conversation does not simply grow until the context is full.</p><div className="toggle-grid">
        {([['use_conversation_history','Conversation history'],['use_memory','Persistent memory recall'],['use_knowledge','Knowledge retrieval']] as const).map(([key,label]) => <label className="toggle-row" key={key}><span>{label}</span><input type="checkbox" checked={Boolean(runtime.context_allocation[key])} onChange={(e) => updateAllocation(key, e.target.checked)} /></label>)}
      </div><div className="settings-form-grid mt-4">
        <label>Memory token budget<input type="number" min={0} value={runtime.context_allocation.max_memory_tokens ?? ''} placeholder="Automatic" onChange={(e) => updateAllocation('max_memory_tokens', e.target.value ? Number(e.target.value) : null)} /></label>
        <label>Knowledge token budget<input type="number" min={0} value={runtime.context_allocation.max_knowledge_tokens ?? ''} placeholder="Automatic" onChange={(e) => updateAllocation('max_knowledge_tokens', e.target.value ? Number(e.target.value) : null)} /></label>
        <label>History token budget<input type="number" min={0} value={runtime.context_allocation.max_history_tokens ?? ''} placeholder="Automatic" onChange={(e) => updateAllocation('max_history_tokens', e.target.value ? Number(e.target.value) : null)} /></label>
        <label>Minimum retrieval score<input type="number" min={0} max={1} step={0.01} value={runtime.context_allocation.min_retrieval_score ?? ''} placeholder="No threshold" onChange={(e) => updateAllocation('min_retrieval_score', e.target.value ? Number(e.target.value) : null)} /></label>
        <label>Reserved output tokens<input type="number" min={0} value={runtime.context_allocation.reserve_output_tokens} onChange={(e) => updateAllocation('reserve_output_tokens', Number(e.target.value))} /></label>
      </div></section>

      <section className="settings-card"><div className="settings-card-title"><SlidersHorizontal className="w-4 h-4" /><h2>Advanced runtime actions</h2></div><div className="flex flex-wrap gap-3"><button className="primary-button" onClick={saveRuntime} disabled={saving}><Save className="w-4 h-4" />{saving ? 'Applying…' : 'Apply runtime profile'}</button>{saved && <span className="settings-inline-note"><CheckCircle2 className="w-4 h-4" />Applied to the active process</span>}</div><p className="muted text-xs mt-3">Changes apply to subsequent executions without restarting the API. Server-level llama.cpp launch flags are intentionally kept separate from request-level controls.</p></section>
    </>}

    {config && <section className="settings-card"><div className="settings-card-title"><Network className="w-4 h-4" /><h2>Provider matrix</h2></div><div className="provider-grid">{[['LLM', config.llm, Cpu], ['Embeddings', config.embeddings, Database], ['Reranker', config.reranker, ShieldCheck]].map(([name, item, Icon]) => { const I = Icon as React.ElementType; return <div className="provider-card" key={String(name)}><I className="w-4 h-4" /><div><strong>{String(name)}</strong><span>{item?.provider} · {item?.baseUrl}</span><small>{item?.modelId || 'auto'} · {item?.path || item?.chatCompletionsPath || ''}</small></div><CheckCircle2 className="w-4 h-4 text-emerald-500" /></div>; })}</div><p className="muted text-xs mt-4">Embedding and reranker endpoints are real provider integrations. Their advanced llama.cpp server/process profiles are the next configuration layer; this page does not pretend that an HTTP endpoint setting has launched a model process.</p></section>}

    <section className="settings-card"><div className="settings-card-title"><Zap className="w-4 h-4" /><h2>Execution budgets</h2></div><div className="runtime-list"><div><span>Model calls</span><strong>{config?.agent?.maxModelCalls ?? '—'}</strong></div><div><span>Tool calls</span><strong>{config?.agent?.maxToolCalls ?? '—'}</strong></div><div><span>Retries</span><strong>{config?.agent?.maxRetries ?? '—'}</strong></div><div><span>Total model tokens</span><strong>{config?.agent?.maxTotalModelTokens === 0 ? 'Unlimited' : config?.agent?.maxTotalModelTokens ?? '—'}</strong></div></div></section>

    <section className="settings-card"><div className="settings-card-title"><Activity className="w-4 h-4" /><h2>Diagnostics</h2></div><div className="runtime-list"><div><span>Collection</span><strong>{diagnosticsEnabled ? 'Enabled' : 'Disabled'}</strong></div><div><span>Session</span><strong className="font-mono text-xs">{diagnosticSession || 'loading'}</strong></div></div><div className="flex flex-wrap gap-3 mt-4"><button className="secondary-button" onClick={() => toggleDiagnostics(!diagnosticsEnabled)}>{diagnosticsEnabled ? 'Disable diagnostics' : 'Enable diagnostics'}</button><button className="primary-button" onClick={exportDiagnostics} disabled={!diagnosticsEnabled}><Download className="w-4 h-4" />Export diagnostic session</button></div></section>
  </div>;
};
