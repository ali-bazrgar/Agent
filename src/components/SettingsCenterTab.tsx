import React, { useEffect, useState } from 'react';
import { CheckCircle2, Moon, Settings, Sun, Wifi, Database, Cpu, ShieldCheck } from 'lucide-react';

interface Props { darkMode: boolean; setDarkMode: (value: boolean) => void; }

export const SettingsCenterTab: React.FC<Props> = ({ darkMode, setDarkMode }) => {
  const [config, setConfig] = useState<Record<string, any> | null>(null); const [health, setHealth] = useState<any>(null); const [error, setError] = useState('');
  useEffect(() => { Promise.all([fetch('/api/v1/config').then((r) => r.json()), fetch('/api/v1/health').then((r) => r.json())]).then(([c, h]) => { setConfig(c); setHealth(h); }).catch((e) => setError(e instanceof Error ? e.message : 'Failed to load runtime settings')); }, []);
  return <div className="space-y-6">
    <div className="page-header"><div><div className="eyebrow"><Settings className="w-4 h-4" /> SETTINGS</div><h1>Runtime & appearance</h1><p>Environment-backed configuration is intentionally read-only here. Change infrastructure values in <code>.env</code> and restart the backend.</p></div></div>
    {error && <div className="error-banner">{error}</div>}
    <div className="settings-grid">
      <section className="settings-card"><div className="settings-card-title"><Sun className="w-4 h-4" /><h2>Appearance</h2></div><p className="muted text-sm">Choose a calm light workspace or a low-glare dark workspace. The preference is stored locally in your browser.</p><div className="theme-choice-grid"><button className={`theme-choice ${!darkMode ? 'selected' : ''}`} onClick={() => setDarkMode(false)}><Sun className="w-5 h-5" /><span>Light</span><small>Clean, soft surfaces</small></button><button className={`theme-choice ${darkMode ? 'selected' : ''}`} onClick={() => setDarkMode(true)}><Moon className="w-5 h-5" /><span>Dark</span><small>Low-glare workspace</small></button></div></section>
      <section className="settings-card"><div className="settings-card-title"><Wifi className="w-4 h-4" /><h2>Runtime status</h2></div><div className="runtime-list"><div><span>Backend</span><strong><i className={`status-dot ${health?.status === 'ok' || health?.status === 'healthy' ? 'online' : 'offline'}`} />{health?.status || 'unknown'}</strong></div><div><span>Environment</span><strong>{health?.environment || config?.environment || 'unknown'}</strong></div><div><span>Database</span><strong>{health?.database || 'unknown'}</strong></div><div><span>Storage</span><strong>{health?.storage || 'unknown'}</strong></div></div></section>
    </div>
    {config && <section className="settings-card"><div className="settings-card-title"><Cpu className="w-4 h-4" /><h2>Providers</h2></div><div className="provider-grid">{[['LLM', config.llm, Cpu], ['Embeddings', config.embeddings, Database], ['Reranker', config.reranker, ShieldCheck]].map(([name, item, Icon]) => { const I = Icon as React.ElementType; return <div className="provider-card" key={String(name)}><I className="w-4 h-4" /><div><strong>{String(name)}</strong><span>{item?.provider} · {item?.baseUrl}</span><small>{item?.modelId}</small></div><CheckCircle2 className="w-4 h-4 text-emerald-500" /></div>; })}</div><p className="muted text-xs mt-4">Configuration source: {config.runtime?.configurationSource || 'environment/.env'} · Mutable at runtime: {String(config.runtime?.mutableAtRuntime ?? false)}</p></section>}
  </div>;
};
