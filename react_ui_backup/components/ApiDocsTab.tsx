import React, { useState } from 'react';
import { Code2, Play, CheckCircle2, Server, Copy, Check } from 'lucide-react';

export const ApiDocsTab: React.FC = () => {
  const [copiedPath, setCopiedPath] = useState<string | null>(null);
  const [activeEndpoint, setActiveEndpoint] = useState('/api/v1/health');
  const [apiResponse, setApiResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const endpoints = [
    { method: 'GET', path: '/api/v1/health', desc: 'Get platform health status & system settings' },
    { method: 'GET', path: '/api/v1/memories', desc: 'List 7-type memory records' },
    { method: 'POST', path: '/api/v1/memories', desc: 'Create new memory record' },
    { method: 'GET', path: '/api/v1/documents', desc: 'List ingested documents & chunks' },
    { method: 'POST', path: '/api/v1/documents', desc: 'Ingest and chunk new document' },
    { method: 'GET', path: '/api/v1/flashcards', desc: 'List spaced repetition flashcards' },
    { method: 'GET', path: '/api/v1/executions', desc: 'List agent orchestration executions' },
  ];

  const handleTestApi = async (path: string) => {
    setActiveEndpoint(path);
    setLoading(true);
    setApiResponse(null);
    try {
      const res = await fetch(path);
      const data = await res.json();
      setApiResponse(JSON.stringify(data, null, 2));
    } catch (err: any) {
      setApiResponse(JSON.stringify({ error: err.message }, null, 2));
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedPath(text);
    setTimeout(() => setCopiedPath(null), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-1">
        <div className="flex items-center space-x-2">
          <Code2 className="w-5 h-5 text-blue-600" />
          <h2 className="text-lg font-bold text-slate-900">Interactive REST API Playground</h2>
        </div>
        <p className="text-xs text-slate-500">
          Native FastAPI endpoint compatibility layer matching original SuperAgent Python routing under <code className="font-mono text-blue-600 bg-blue-50 px-1 py-0.5 rounded">/api/v1/*</code>.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Endpoint Catalog */}
        <div className="space-y-3">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Available Routes</h3>

          <div className="space-y-2">
            {endpoints.map((ep) => (
              <div
                key={ep.path + ep.method}
                className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between hover:border-slate-300 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2 font-mono text-xs">
                    <span className={`px-2 py-0.5 rounded font-bold ${
                      ep.method === 'GET' ? 'bg-blue-100 text-blue-800' : 'bg-emerald-100 text-emerald-800'
                    }`}>
                      {ep.method}
                    </span>
                    <span className="font-bold text-slate-900">{ep.path}</span>
                  </div>
                  <p className="text-xs text-slate-500">{ep.desc}</p>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => copyToClipboard(ep.path)}
                    className="p-1.5 text-slate-400 hover:text-slate-600 rounded-md hover:bg-slate-50"
                    title="Copy path"
                  >
                    {copiedPath === ep.path ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                  </button>

                  {ep.method === 'GET' && (
                    <button
                      onClick={() => handleTestApi(ep.path)}
                      className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg flex items-center space-x-1"
                    >
                      <Play className="w-3 h-3 text-blue-400" />
                      <span>Test</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* API Response Inspector */}
        <div className="bg-slate-950 rounded-2xl p-6 text-slate-200 border border-slate-800 space-y-4 shadow-md font-mono">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <Server className="w-4 h-4 text-blue-400" />
              <span className="text-xs font-bold text-white">Response: {activeEndpoint}</span>
            </div>
            <span className="text-[11px] text-emerald-400 font-semibold">200 OK</span>
          </div>

          <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 text-xs text-blue-300 min-h-[300px] max-h-[450px] overflow-auto">
            {loading ? (
              <div className="text-slate-400 animate-pulse">Executing request to {activeEndpoint}...</div>
            ) : apiResponse ? (
              <pre className="whitespace-pre-wrap">{apiResponse}</pre>
            ) : (
              <div className="text-slate-500 text-center py-12">
                Click "Test" on any endpoint on the left to inspect JSON response payload.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
