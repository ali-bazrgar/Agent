import React, { useState, useEffect } from 'react';
import { Settings, Cpu, Database, Shield, RefreshCw, Save, Download, Upload, CheckCircle2, AlertCircle } from 'lucide-react';

export const SettingsCenterTab: React.FC = () => {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [activeCategory, setActiveCategory] = useState<'llm' | 'embeddings' | 'reranker' | 'agent' | 'context' | 'learning' | 'database' | 'observability'>('llm');

  useEffect(() => {
    fetch('/api/v1/config')
      .then((res) => res.json())
      .then((data) => {
        setConfig(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load config:', err);
        setLoading(false);
      });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch('/api/v1/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (res.ok) {
        alert('Configuration saved successfully.');
      }
    } catch (err) {
      console.error('Failed to save config:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async (providerType: string) => {
    setTesting(true);
    setTestResult(null);
    try {
      const targetConfig = config[providerType] || config.llm;
      const res = await fetch('/api/v1/config/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_type: providerType,
          base_url: targetConfig.baseUrl,
          model_id: targetConfig.modelId,
          api_key: targetConfig.apiKey,
        }),
      });
      const data = await res.json();
      setTestResult(data);
    } catch (err: any) {
      setTestResult({ success: false, message: err.message || 'Connection failed' });
    } finally {
      setTesting(false);
    }
  };

  const handleExport = async () => {
    try {
      const res = await fetch('/api/v1/config/export', { method: 'POST' });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'superagent-config.json';
      a.click();
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  if (loading || !config) {
    return <div className="p-12 text-center text-slate-500">Loading Configuration Center...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-slate-900 text-white rounded-xl">
            <Settings className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">Settings Center & Configuration Architecture</h1>
            <p className="text-xs text-slate-500">Manage LLM infrastructure, embeddings, rerankers, agent policies, and budgets</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleExport}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-xl text-xs flex items-center space-x-2 transition-colors"
          >
            <Download className="w-4 h-4" />
            <span>Export Config</span>
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl text-xs flex items-center space-x-2 shadow-xs transition-colors"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving...' : 'Save Changes'}</span>
          </button>
        </div>
      </div>

      {/* Categories & Form */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-1">
          {[
            { id: 'llm', label: 'LLM Infrastructure', icon: Cpu },
            { id: 'embeddings', label: 'Embeddings', icon: Database },
            { id: 'reranker', label: 'Reranker', icon: Shield },
            { id: 'agent', label: 'Agent Policy', icon: Cpu },
            { id: 'context', label: 'Context Budgets', icon: Settings },
            { id: 'learning', label: 'Learning Engine', icon: Settings },
            { id: 'database', label: 'Database & Storage', icon: Database },
            { id: 'observability', label: 'Observability', icon: Settings },
          ].map((cat) => {
            const Icon = cat.icon;
            const isActive = activeCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => setActiveCategory(cat.id as any)}
                className={`w-full flex items-center space-x-3 px-4 py-3 text-sm font-medium rounded-xl transition-colors ${
                  isActive ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-blue-400' : 'text-slate-500'}`} />
                <span>{cat.label}</span>
              </button>
            );
          })}
        </div>

        <div className="lg:col-span-3 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
          {activeCategory === 'llm' && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-slate-900">LLM Provider Configuration</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Provider Type</label>
                  <input
                    type="text"
                    value={config.llm.provider}
                    onChange={(e) => setConfig({ ...config, llm: { ...config.llm, provider: e.target.value } })}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Model ID</label>
                  <input
                    type="text"
                    value={config.llm.modelId}
                    onChange={(e) => setConfig({ ...config, llm: { ...config.llm, modelId: e.target.value } })}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Base URL</label>
                  <input
                    type="text"
                    value={config.llm.baseUrl}
                    onChange={(e) => setConfig({ ...config, llm: { ...config.llm, baseUrl: e.target.value } })}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-mono text-xs"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">API Key (Server-Side Secure)</label>
                  <input
                    type="password"
                    value={config.llm.apiKey}
                    onChange={(e) => setConfig({ ...config, llm: { ...config.llm, apiKey: e.target.value } })}
                    placeholder="sk-..."
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-mono text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Temperature ({config.llm.temperature})</label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={config.llm.temperature}
                    onChange={(e) => setConfig({ ...config, llm: { ...config.llm, temperature: parseFloat(e.target.value) } })}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Max Output Tokens</label>
                  <input
                    type="number"
                    value={config.llm.maxOutputTokens}
                    onChange={(e) => setConfig({ ...config, llm: { ...config.llm, maxOutputTokens: parseInt(e.target.value) } })}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm"
                  />
                </div>
              </div>
              <div className="pt-4 flex items-center justify-between border-t border-slate-100">
                <button
                  onClick={() => handleTestConnection('llm')}
                  disabled={testing}
                  className="px-4 py-2.5 bg-slate-900 text-white font-medium rounded-xl text-xs hover:bg-slate-800 transition-colors flex items-center space-x-2"
                >
                  <RefreshCw className={`w-4 h-4 ${testing ? 'animate-spin' : ''}`} />
                  <span>Test LLM Connection</span>
                </button>
                {testResult && (
                  <div className={`text-xs font-medium flex items-center ${testResult.success ? 'text-emerald-600' : 'text-red-600'}`}>
                    <CheckCircle2 className="w-4 h-4 mr-1" />
                    <span>{testResult.message} ({testResult.latency_ms}ms)</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeCategory === 'embeddings' && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-slate-900">Embedding Model Configuration</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Provider</label>
                  <input
                    type="text"
                    value={config.embeddings.provider}
                    onChange={(e) => setConfig({ ...config, embeddings: { ...config.embeddings, provider: e.target.value } })}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Model ID</label>
                  <input
                    type="text"
                    value={config.embeddings.modelId}
                    onChange={(e) => setConfig({ ...config, embeddings: { ...config.embeddings, modelId: e.target.value } })}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Base URL</label>
                  <input
                    type="text"
                    value={config.embeddings.baseUrl}
                    onChange={(e) => setConfig({ ...config, embeddings: { ...config.embeddings, baseUrl: e.target.value } })}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-mono text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Dimensions</label>
                  <input
                    type="number"
                    value={config.embeddings.dimensions}
                    onChange={(e) => setConfig({ ...config, embeddings: { ...config.embeddings, dimensions: parseInt(e.target.value) } })}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm"
                  />
                </div>
              </div>
            </div>
          )}

          {activeCategory === 'database' && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-slate-900">Database & Storage Configuration</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">SQLite Database Path</label>
                  <input
                    type="text"
                    value={config.database.path}
                    onChange={(e) => setConfig({ ...config, database: { ...config.database, path: e.target.value } })}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Local Storage Path</label>
                  <input
                    type="text"
                    value={config.database.storagePath}
                    onChange={(e) => setConfig({ ...config, database: { ...config.database, storagePath: e.target.value } })}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-mono"
                  />
                </div>
              </div>
            </div>
          )}

          {activeCategory !== 'llm' && activeCategory !== 'embeddings' && activeCategory !== 'database' && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-slate-900 capitalize">{activeCategory} Configuration</h2>
              <p className="text-sm text-slate-600">
                Configure advanced parameters for {activeCategory} within SuperAgent's centralized architecture.
              </p>
              <pre className="p-4 bg-slate-50 rounded-xl text-xs font-mono text-slate-700 overflow-x-auto border border-slate-200">
                {JSON.stringify(config[activeCategory], null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
