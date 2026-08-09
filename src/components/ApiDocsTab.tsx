import React, { useState } from 'react';
import { Code2, Play, Server, Copy, Check } from 'lucide-react';

interface Endpoint { method: 'GET' | 'POST'; path: string; desc: string; }

export const ApiDocsTab: React.FC = () => {
  const [copiedPath, setCopiedPath] = useState<string | null>(null);
  const [activeEndpoint, setActiveEndpoint] = useState('/api/v1/health');
  const [apiResponse, setApiResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<number | null>(null);

  const endpoints: Endpoint[] = [
    { method: 'GET', path: '/api/v1/health', desc: 'Runtime, database, storage, and provider health' },
    { method: 'GET', path: '/api/v1/config', desc: 'Active runtime and model capability configuration' },
    { method: 'GET', path: '/api/v1/tools', desc: 'Exact tool registry exposed to the agent' },
    { method: 'GET', path: '/api/v1/memories', desc: 'Persistent memory records' },
    { method: 'GET', path: '/api/v1/documents', desc: 'Persisted knowledge documents and chunks' },
    { method: 'GET', path: '/api/v1/learning/flashcards', desc: 'Persisted FSRS flashcards' },
    { method: 'GET', path: '/api/v1/learning/review?limit=50', desc: 'Currently due reviews' },
    { method: 'GET', path: '/api/v1/executions', desc: 'Agent execution history and diagnostics' },
    { method: 'GET', path: '/api/v1/knowledge-graph', desc: 'Persisted document/chunk/knowledge relationships' },
  ];

  const handleTestApi = async (path: string) => {
    setActiveEndpoint(path); setLoading(true); setApiResponse(null); setStatus(null);
    try {
      const res = await fetch(path);
      const data = await res.json().catch(() => ({}));
      setStatus(res.status);
      setApiResponse(JSON.stringify(data, null, 2));
    } catch (err) {
      setApiResponse(JSON.stringify({ error: err instanceof Error ? err.message : 'Unknown request error' }, null, 2));
    } finally { setLoading(false); }
  };

  const copyToClipboard = (text: string) => {
    void navigator.clipboard.writeText(text);
    setCopiedPath(text);
    window.setTimeout(() => setCopiedPath(null), 2000);
  };

  return <div className="space-y-6">
    <div className="settings-card space-y-1">
      <div className="flex items-center gap-2"><Code2 className="w-5 h-5" /><h2 className="text-lg font-bold">Interactive REST API Playground</h2></div>
      <p className="muted text-xs">Temporary integration-test surface. Routes are derived from the current FastAPI contract rather than the future production UI.</p>
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-3">
        <h3 className="muted text-xs font-semibold uppercase tracking-wider">Current routes</h3>
        {endpoints.map((ep) => <div key={`${ep.method}-${ep.path}`} className="settings-card flex items-center justify-between gap-4 py-4">
          <div className="min-w-0"><div className="flex items-center gap-2 font-mono text-xs"><span className="status-chip">{ep.method}</span><span className="font-bold truncate">{ep.path}</span></div><p className="muted text-xs mt-1">{ep.desc}</p></div>
          <div className="flex items-center gap-2 shrink-0"><button onClick={() => copyToClipboard(ep.path)} className="icon-button" title="Copy path">{copiedPath === ep.path ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}</button><button onClick={() => void handleTestApi(ep.path)} className="primary-button"><Play className="w-3.5 h-3.5" />Test</button></div>
        </div>)}
      </div>
      <div className="bg-slate-950 rounded-2xl p-6 text-slate-200 border border-slate-800 space-y-4 shadow-md font-mono">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3"><div className="flex items-center gap-2"><Server className="w-4 h-4" /><span className="text-xs font-bold text-white">{activeEndpoint}</span></div>{status !== null && <span className="text-[11px] font-semibold">HTTP {status}</span>}</div>
        <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 text-xs min-h-[300px] max-h-[550px] overflow-auto">{loading ? <div className="text-slate-400 animate-pulse">Executing request…</div> : apiResponse ? <pre className="whitespace-pre-wrap">{apiResponse}</pre> : <div className="text-slate-500 text-center py-12">Select an endpoint and run it to inspect the real JSON contract.</div>}</div>
      </div>
    </div>
  </div>;
};
