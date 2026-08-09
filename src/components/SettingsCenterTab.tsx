import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, BrainCircuit, CheckCircle2, Cpu, Database, Download, Gauge, Moon, Network, Save, Settings, ShieldCheck, Sun, Terminal, Upload, XCircle, Zap } from 'lucide-react';
import { exportDiagnostics, isDiagnosticsEnabled, setDiagnosticsEnabled } from '../diagnostics';
import './SettingsCenterTab.css';

interface Props { darkMode: boolean; setDarkMode: (value: boolean) => void; }
type Role = 'llm' | 'embedding' | 'reranker';
type Profile = { role: Role; executable_path: string; model_path: string; mmproj_path: string; draft_model_path: string; options: Record<string, any> };
type EngineStatus = { running: boolean; pid: number | null; started_at: string | null; command: string[] | null; log_path: string; returncode: number | null; default_port: number };
type EngineLog = { role: Role; path: string; lines: string[]; generation_tokens_per_second: number | null; prompt_tokens_per_second: number | null; generation_tokens: number | null; prompt_tokens: number | null };
type Runtime = { model_id: string | null; context_window_tokens: number; max_output_tokens: number | null; temperature: number; top_p: number; timeout_seconds: number; context_allocation: { use_conversation_history: boolean; use_memory: boolean; use_knowledge: boolean; max_memory_tokens: number | null; max_knowledge_tokens: number | null; max_history_tokens: number | null; min_retrieval_score: number | null; reserve_output_tokens: number } };

const roles: Role[] = ['llm', 'embedding', 'reranker'];
const emptyProfile = (role: Role): Profile => ({ role, executable_path: '', model_path: '', mmproj_path: '', draft_model_path: '', options: {} });
const fallbackRuntime = (config: any): Runtime => ({ model_id: config?.llm?.modelId ?? null, context_window_tokens: config?.llm?.runtime?.context_window_tokens ?? config?.llm?.contextWindowTokens ?? 8192, max_output_tokens: config?.llm?.runtime?.max_output_tokens ?? null, temperature: config?.llm?.runtime?.temperature ?? config?.llm?.temperature ?? 0.7, top_p: config?.llm?.runtime?.top_p ?? config?.llm?.topP ?? 1, timeout_seconds: config?.llm?.runtime?.timeout_seconds ?? 60, context_allocation: config?.llm?.runtime?.context_allocation ?? { use_conversation_history: true, use_memory: true, use_knowledge: true, max_memory_tokens: null, max_knowledge_tokens: null, max_history_tokens: null, min_retrieval_score: null, reserve_output_tokens: 0 } });

const labels: Record<Role, string> = { llm: 'LLM', embedding: 'Embedding', reranker: 'Reranker' };
const pickerExtensions = (kind: 'executable' | 'model' | 'mmproj' | 'draft') => kind === 'model' || kind === 'draft' ? ['.gguf', '.ggml', '.bin'] : kind === 'mmproj' ? ['.gguf', '.bin'] : [];

export const SettingsCenterTab: React.FC<Props> = ({ darkMode, setDarkMode }) => {
  const [config, setConfig] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [error, setError] = useState('');
  const [runtime, setRuntime] = useState<Runtime | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [diagnosticsEnabled, setDiagEnabled] = useState(isDiagnosticsEnabled());
  const [diagnosticSession, setDiagnosticSession] = useState('');
  const [role, setRole] = useState<Role>('llm');
  const [profiles, setProfiles] = useState<Record<Role, Profile>>({ llm: emptyProfile('llm'), embedding: emptyProfile('embedding'), reranker: emptyProfile('reranker') });
  const [profileJson, setProfileJson] = useState<Record<Role, string>>({ llm: '{}', embedding: '{}', reranker: '{}' });
  const [loadedRoles, setLoadedRoles] = useState<Partial<Record<Role, boolean>>>({});
  const [loadingRole, setLoadingRole] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);
  const [command, setCommand] = useState('');
  const [profileBusy, setProfileBusy] = useState(false);
  const [pickerBusy, setPickerBusy] = useState<string | null>(null);
  const [engines, setEngines] = useState<Record<Role, EngineStatus>>({
    llm: { running: false, pid: null, started_at: null, command: null, log_path: '', returncode: null, default_port: 8080 },
    embedding: { running: false, pid: null, started_at: null, command: null, log_path: '', returncode: null, default_port: 8081 },
    reranker: { running: false, pid: null, started_at: null, command: null, log_path: '', returncode: null, default_port: 8082 },
  });
  const [engineLogs, setEngineLogs] = useState<Record<Role, EngineLog | null>>({ llm: null, embedding: null, reranker: null });
  const [engineBusy, setEngineBusy] = useState<Role | null>(null);

  const loadRoleProfile = useCallback(async (targetRole: Role, signal?: AbortSignal) => {
    setLoadingRole(true); setError('');
    try {
      const response = await fetch(`/api/v1/config/llama/profiles/${targetRole}`, { signal });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Failed to load ${labels[targetRole]} profile`);
      const next = data.profile || emptyProfile(targetRole);
      setProfiles((current) => ({ ...current, [targetRole]: next }));
      setProfileJson((current) => ({ ...current, [targetRole]: JSON.stringify(next.options || {}, null, 2) }));
      setLoadedRoles((current) => ({ ...current, [targetRole]: true }));
    } catch (e) {
      if ((e as DOMException)?.name !== 'AbortError') setError(e instanceof Error ? e.message : `Failed to load ${labels[targetRole]} profile`);
    } finally { if (!signal?.aborted) setLoadingRole(false); }
  }, []);

  const loadShared = useCallback(async () => {
    try {
      const [c, h, d, s] = await Promise.all([
        fetch('/api/v1/config').then((r) => r.json()),
        fetch('/api/v1/health').then((r) => r.json()),
        fetch('/api/v1/diagnostics/status').then((r) => r.json()),
        fetch('/api/v1/engine/status').then((r) => r.json()),
      ]);
      setConfig(c); setHealth(h); setRuntime(fallbackRuntime(c)); setDiagnosticSession(d.session_id || '');
      if (s.engines) setEngines(s.engines);
    } catch (e) { setError(e instanceof Error ? e.message : 'Failed to load settings'); }
  }, []);

  useEffect(() => { void loadShared(); }, [loadShared]);
  useEffect(() => { const controller = new AbortController(); void loadRoleProfile(role, controller.signal); return () => controller.abort(); }, [role, loadRoleProfile]);
  useEffect(() => { const timer = window.setInterval(() => { void fetch('/api/v1/engine/status').then((r) => r.json()).then((data) => { if (data.engines) setEngines(data.engines); }).catch(() => undefined); }, 2500); return () => window.clearInterval(timer); }, []);
  useEffect(() => {
    let cancelled = false;
    const refreshLog = async () => {
      try {
        const response = await fetch(`/api/v1/engine/logs/${role}?lines=80`);
        const data = await response.json();
        if (!cancelled && response.ok) setEngineLogs((current) => ({ ...current, [role]: data }));
      } catch { /* telemetry is non-fatal */ }
    };
    void refreshLog();
    const timer = window.setInterval(() => void refreshLog(), 1500);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [role]);

  const activeProfile = profiles[role];
  const activeJson = profileJson[role];
  const activeLog = engineLogs[role];
  const modelMaximum = config?.context?.modelMaximumTokens ?? config?.llm?.capabilities?.context_window_tokens ?? null;
  const contextLabel = useMemo(() => modelMaximum ? `Detected model maximum: ${Number(modelMaximum).toLocaleString()} tokens` : 'Model maximum not reported; manual value is allowed', [modelMaximum]);
  const updateAllocation = (key: string, value: any) => setRuntime((r) => r ? ({ ...r, context_allocation: { ...r.context_allocation, [key]: value } }) : r);
  const updateProfile = (patch: Partial<Profile>) => setProfiles((current) => ({ ...current, [role]: { ...current[role], ...patch } }));

  const browse = async (field: 'executable_path' | 'model_path' | 'mmproj_path' | 'draft_model_path') => {
    setPickerBusy(field); setError('');
    try {
      const kind = field === 'executable_path' ? 'executable' : field === 'model_path' ? 'model' : field === 'mmproj_path' ? 'mmproj' : 'draft';
      const currentPath = activeProfile[field];
      const slash = Math.max(currentPath.lastIndexOf('/'), currentPath.lastIndexOf('\\'));
      const initialPath = slash > 0 ? currentPath.slice(0, slash) : undefined;
      const response = await fetch('/api/v1/system/file-picker', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: 'file', title: `Select ${field === 'executable_path' ? 'llama-server executable' : labels[role] + ' model file'}`, extensions: pickerExtensions(kind), initial_path: initialPath }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Native file picker is unavailable');
      if (data.path) {
        updateProfile({ [field]: data.path } as Partial<Profile>);
        if (field === 'executable_path' && role === 'llm') {
          setProfiles((current) => ({ ...current, embedding: { ...current.embedding, executable_path: current.embedding.executable_path || data.path }, reranker: { ...current.reranker, executable_path: current.reranker.executable_path || data.path } }));
        }
      }
    } catch (e) { setError(e instanceof Error ? e.message : 'Failed to open native file picker'); }
    finally { setPickerBusy(null); }
  };

  const saveRuntime = async () => { if (!runtime) return; setSaving(true); setSaved(false); setError(''); try { const response = await fetch('/api/v1/config/runtime', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(runtime) }); const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'Runtime configuration was rejected'); setRuntime(data.runtime); setSaved(true); window.setTimeout(() => setSaved(false), 2500); } catch (e) { setError(e instanceof Error ? e.message : 'Failed to save runtime'); } finally { setSaving(false); } };

  const parseOptions = () => { try { return JSON.parse(activeJson || '{}'); } catch { throw new Error('Advanced llama.cpp options must be valid JSON.'); } };
  const persistProfile = async (targetRole: Role = role) => {
    const source = profiles[targetRole];
    const options = targetRole === role ? parseOptions() : source.options || {};
    const payload = { ...source, role: targetRole, options };
    const response = await fetch(`/api/v1/config/llama/profiles/${targetRole}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `Failed to save ${labels[targetRole]} profile`);
    const next = data.profile;
    setProfiles((current) => ({ ...current, [targetRole]: next }));
    setProfileJson((current) => ({ ...current, [targetRole]: JSON.stringify(next.options || {}, null, 2) }));
    return next;
  };

  const saveProfile = async () => { setProfileBusy(true); setError(''); try { await persistProfile(); setProfileSaved(true); window.setTimeout(() => setProfileSaved(false), 2500); } catch (e) { setError(e instanceof Error ? e.message : 'Failed to save llama.cpp profile'); } finally { setProfileBusy(false); } };

  const renderCommand = async () => { setProfileBusy(true); setError(''); try { const options = parseOptions(); const response = await fetch('/api/v1/config/llama/command', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...activeProfile, role, options }) }); const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'Unable to render command'); setCommand(data.shell_command || ''); } catch (e) { setError(e instanceof Error ? e.message : 'Invalid llama.cpp configuration'); } finally { setProfileBusy(false); } };

  const engineAction = async (action: 'start' | 'stop' | 'restart') => {
    setEngineBusy(role); setError('');
    try {
      if (action === 'start' || action === 'restart') await persistProfile(role);
      const response = await fetch(`/api/v1/engine/${role}/${action}`, { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Unable to ${action} ${labels[role]}`);
      setEngines((current) => ({ ...current, [role]: data }));
      window.setTimeout(async () => {
        try { const logResponse = await fetch(`/api/v1/engine/logs/${role}?lines=80`); const logData = await logResponse.json(); if (logResponse.ok) setEngineLogs((current) => ({ ...current, [role]: logData })); } catch { /* telemetry is non-fatal */ }
      }, 800);
    } catch (e) { setError(e instanceof Error ? e.message : `Unable to ${action} engine`); }
    finally { setEngineBusy(null); }
  };
  const toggleDiagnostics = (value: boolean) => { setDiagEnabled(value); setDiagnosticsEnabled(value); window.location.reload(); };

  const pathField = (field: 'executable_path' | 'model_path' | 'mmproj_path' | 'draft_model_path', label: string, placeholder: string, pickerKind: 'executable' | 'model' | 'mmproj' | 'draft') => (
    <label className="path-field"><span>{label}</span><div className="path-input-row"><input value={activeProfile[field]} onChange={(e) => updateProfile({ [field]: e.target.value })} placeholder={placeholder} spellCheck={false} /><button type="button" className="browse-button" onClick={() => browse(field)} disabled={pickerBusy !== null} title="Open system file picker"><Upload className="w-4 h-4" />{pickerBusy === field ? 'Opening…' : 'Browse'}</button></div><small>{pickerKind === 'executable' ? 'Select the actual llama-server binary for this machine. One binary can be shared by all three roles.' : 'Select the local model file from the system file picker.'}</small></label>
  );

  return <div className="space-y-6">
    <div className="page-header"><div><div className="eyebrow"><Settings className="w-4 h-4" /> SETTINGS</div><h1>Runtime & Model Control Center</h1><p>Configure each model independently, select real local files through the operating-system picker, and start or stop llama.cpp engines without opening separate terminals.</p></div></div>
    {error && <div className="error-banner"><XCircle className="w-4 h-4" />{error}</div>}

    <section className="settings-card">
      <div className="settings-card-title"><Terminal className="w-4 h-4" /><h2>llama.cpp engine profiles</h2></div>
      <p className="muted text-sm">Each role has isolated state. Switching LLM → Embedding → Reranker no longer reuses or overwrites the previous role's form.</p>
      <div className="role-tabs">{roles.map((r) => <button key={r} className={`nav-item ${role === r ? 'active' : ''}`} onClick={() => { setRole(r); setCommand(''); }}><span>{labels[r]}</span>{loadedRoles[r] && <CheckCircle2 className="w-3 h-3" />}</button>)}</div>
      {loadingRole && <div className="settings-inline-note"><Activity className="w-4 h-4" />Loading {labels[role]} profile…</div>}
      <div className="settings-form-grid path-grid mt-4">
        {pathField('executable_path', 'llama-server executable', 'C:\\llama.cpp\\llama-server.exe', 'executable')}
        {pathField('model_path', `${labels[role]} model`, 'C:\\models\\model.gguf', 'model')}
        {pathField('mmproj_path', 'MMProj (optional)', 'C:\\models\\mmproj-BF16.gguf', 'mmproj')}
        {pathField('draft_model_path', 'Draft / MTP model (optional)', 'C:\\models\\mtp-model.gguf', 'draft')}
      </div>
      <div className="engine-toolbar">
        <div className={`engine-state ${engines[role].running ? 'running' : 'stopped'}`}><span className="status-dot" />{engines[role].running ? `Running · PID ${engines[role].pid}` : 'Stopped'}<small>default port {engines[role].default_port}</small></div>
        <div className="flex flex-wrap gap-2"><button className="primary-button" onClick={() => engineAction('start')} disabled={engineBusy !== null || engines[role].running}><Zap className="w-4 h-4" />{engineBusy === role ? 'Working…' : 'Start engine'}</button><button className="secondary-button" onClick={() => engineAction('restart')} disabled={engineBusy !== null}><Activity className="w-4 h-4" />Restart</button><button className="secondary-button" onClick={() => engineAction('stop')} disabled={engineBusy !== null || !engines[role].running}><XCircle className="w-4 h-4" />Stop</button></div>
      </div>
      {engines[role].log_path && <div className="settings-inline-note block break-all font-mono text-xs">Engine log: {engines[role].log_path}</div>}
      {activeLog && <div className="engine-telemetry-grid mt-4"><div><span>Generation</span><strong>{activeLog.generation_tokens_per_second == null ? '—' : `${activeLog.generation_tokens_per_second.toFixed(2)} tok/s`}</strong><small>{activeLog.generation_tokens == null ? 'Waiting for llama.cpp eval output' : `${activeLog.generation_tokens.toLocaleString()} tokens`}</small></div><div><span>Prompt / encode</span><strong>{activeLog.prompt_tokens_per_second == null ? '—' : `${activeLog.prompt_tokens_per_second.toFixed(2)} tok/s`}</strong><small>{activeLog.prompt_tokens == null ? 'Waiting for prompt eval output' : `${activeLog.prompt_tokens.toLocaleString()} tokens`}</small></div><div><span>Live log lines</span><strong>{activeLog.lines.length}</strong><small>Updated automatically</small></div></div>}
      {activeLog && activeLog.lines.length > 0 && <details className="mt-4"><summary className="cursor-pointer muted text-sm">Live llama.cpp log</summary><pre className="settings-log-view mt-2">{activeLog.lines.join('\n')}</pre></details>}
      <label className="block mt-4">Advanced llama.cpp options — JSON<textarea rows={12} value={activeJson} onChange={(e) => setProfileJson((current) => ({ ...current, [role]: e.target.value }))} spellCheck={false} className="font-mono text-xs" /></label>
      <div className="flex flex-wrap gap-3 mt-4"><button className="primary-button" onClick={saveProfile} disabled={profileBusy || loadingRole}><Save className="w-4 h-4" />{profileBusy ? 'Working…' : 'Save engine profile'}</button><button className="secondary-button" onClick={renderCommand} disabled={profileBusy || loadingRole}>Render command</button>{profileSaved && <span className="settings-inline-note"><CheckCircle2 className="w-4 h-4" />Saved</span>}</div>
      {command && <div className="settings-inline-note mt-4 block break-all font-mono text-xs">{command}</div>}
      <p className="muted text-xs mt-3">Start and Restart persist the current form first, then launch the engine from that exact saved profile. Embedding and reranking automatically receive their dedicated llama.cpp server mode when it is not already present in the profile.</p>
    </section>

    <section className="settings-card"><div className="settings-card-title"><Gauge className="w-4 h-4" /><h2>Active LLM runtime</h2></div><p className="muted text-sm">The user-selected context is the runtime allocation. There is no application-wide 128K ceiling; the detected model capability is used when available.</p>{runtime && <><div className="settings-form-grid"><label>Model ID<input value={runtime.model_id || ''} onChange={(e) => setRuntime({ ...runtime, model_id: e.target.value || null })} placeholder="provider/model" /></label><label>Context window<input type="number" min={256} max={modelMaximum || undefined} step={256} value={runtime.context_window_tokens} onChange={(e) => setRuntime({ ...runtime, context_window_tokens: Number(e.target.value) })} /></label><label>Max output tokens<input type="number" min={1} value={runtime.max_output_tokens ?? ''} onChange={(e) => setRuntime({ ...runtime, max_output_tokens: e.target.value ? Number(e.target.value) : null })} placeholder="Unlimited" /></label><label>Temperature<input type="number" min={0} max={2} step={0.01} value={runtime.temperature} onChange={(e) => setRuntime({ ...runtime, temperature: Number(e.target.value) })} /></label><label>Top P<input type="number" min={0.01} max={1} step={0.01} value={runtime.top_p} onChange={(e) => setRuntime({ ...runtime, top_p: Number(e.target.value) })} /></label><label>Timeout (s)<input type="number" min={1} value={runtime.timeout_seconds} onChange={(e) => setRuntime({ ...runtime, timeout_seconds: Number(e.target.value) })} /></label></div><div className="settings-inline-note mt-4"><Cpu className="w-4 h-4" />{contextLabel}</div></>}</section>

    {runtime && <section className="settings-card"><div className="settings-card-title"><BrainCircuit className="w-4 h-4" /><h2>Context intelligence & memory</h2></div><p className="muted text-sm">Keep the selected context fixed while the agent retrieves only useful memory and knowledge for each message instead of endlessly growing the prompt.</p><div className="toggle-grid mt-4">{([['use_conversation_history','Conversation history'],['use_memory','Persistent memory recall every message'],['use_knowledge','Knowledge retrieval']] as const).map(([key,label]) => <label className="toggle-row" key={key}><span>{label}</span><input type="checkbox" checked={Boolean(runtime.context_allocation[key])} onChange={(e) => updateAllocation(key, e.target.checked)} /></label>)}</div><div className="settings-form-grid mt-4"><label>Memory token budget<input type="number" min={0} value={runtime.context_allocation.max_memory_tokens ?? ''} placeholder="Automatic" onChange={(e) => updateAllocation('max_memory_tokens', e.target.value ? Number(e.target.value) : null)} /></label><label>Knowledge token budget<input type="number" min={0} value={runtime.context_allocation.max_knowledge_tokens ?? ''} placeholder="Automatic" onChange={(e) => updateAllocation('max_knowledge_tokens', e.target.value ? Number(e.target.value) : null)} /></label><label>History token budget<input type="number" min={0} value={runtime.context_allocation.max_history_tokens ?? ''} placeholder="Automatic" onChange={(e) => updateAllocation('max_history_tokens', e.target.value ? Number(e.target.value) : null)} /></label><label>Minimum retrieval score<input type="number" min={0} max={1} step={0.01} value={runtime.context_allocation.min_retrieval_score ?? ''} placeholder="No threshold" onChange={(e) => updateAllocation('min_retrieval_score', e.target.value ? Number(e.target.value) : null)} /></label><label>Reserved output tokens<input type="number" min={0} value={runtime.context_allocation.reserve_output_tokens} onChange={(e) => updateAllocation('reserve_output_tokens', Number(e.target.value))} /></label></div><div className="flex gap-3 mt-5"><button className="primary-button" onClick={saveRuntime} disabled={saving}><Save className="w-4 h-4" />{saving ? 'Applying…' : 'Apply runtime profile'}</button>{saved && <span className="settings-inline-note"><CheckCircle2 className="w-4 h-4" />Applied to subsequent executions</span>}</div></section>}

    {config && <section className="settings-card"><div className="settings-card-title"><Network className="w-4 h-4" /><h2>Provider matrix</h2></div><div className="provider-grid">{[['LLM', config.llm, Cpu], ['Embeddings', config.embeddings, Database], ['Reranker', config.reranker, ShieldCheck]].map(([name, item, Icon]) => { const I = Icon as React.ElementType; return <div className="provider-card" key={String(name)}><I className="w-4 h-4" /><div><strong>{String(name)}</strong><span>{item?.provider} · {item?.baseUrl}</span><small>{item?.modelId || 'auto'} · {item?.path || item?.chatCompletionsPath || ''}</small></div><CheckCircle2 className="w-4 h-4 text-emerald-500" /></div>; })}</div></section>}

    <section className="settings-card"><div className="settings-card-title"><Zap className="w-4 h-4" /><h2>Execution safety</h2></div><div className="runtime-list"><div><span>Model calls</span><strong>{config?.agent?.maxModelCalls ?? '—'}</strong></div><div><span>Tool calls</span><strong>{config?.agent?.maxToolCalls ?? '—'}</strong></div><div><span>Retries</span><strong>{config?.agent?.maxRetries ?? '—'}</strong></div><div><span>Total model tokens</span><strong>{config?.agent?.maxTotalModelTokens === 0 ? 'Unlimited' : config?.agent?.maxTotalModelTokens ?? '—'}</strong></div></div></section>
    <section className="settings-card"><div className="settings-card-title"><Sun className="w-4 h-4" /><h2>Appearance & diagnostics</h2></div><div className="theme-choice-grid"><button className={`theme-choice ${!darkMode ? 'selected' : ''}`} onClick={() => setDarkMode(false)}><Sun className="w-5 h-5" /><span>Light</span></button><button className={`theme-choice ${darkMode ? 'selected' : ''}`} onClick={() => setDarkMode(true)}><Moon className="w-5 h-5" /><span>Dark</span></button></div><div className="runtime-list mt-5"><div><span>Backend</span><strong><i className={`status-dot ${health?.status === 'ok' || health?.status === 'healthy' ? 'online' : 'offline'}`} />{health?.status || 'unknown'}</strong></div><div><span>Diagnostic session</span><strong className="font-mono text-xs">{diagnosticSession || 'loading'}</strong></div></div><div className="flex flex-wrap gap-3 mt-4"><button className="secondary-button" onClick={() => toggleDiagnostics(!diagnosticsEnabled)}>{diagnosticsEnabled ? 'Disable diagnostics' : 'Enable diagnostics'}</button><button className="primary-button" onClick={exportDiagnostics} disabled={!diagnosticsEnabled}><Download className="w-4 h-4" />Export diagnostic session</button></div></section>
  </div>;
};
