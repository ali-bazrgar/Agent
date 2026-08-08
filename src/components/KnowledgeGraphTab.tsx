import React, { useEffect, useState } from 'react';
import { Network, RefreshCw, Search, Share2 } from 'lucide-react';

interface GraphNode { id: string; label: string; group: string; [key: string]: unknown }
interface GraphEdge { id: string; source: string; target: string; relation: string }

export const KnowledgeGraphTab: React.FC = () => {
  const [nodes, setNodes] = useState<GraphNode[]>([]); const [edges, setEdges] = useState<GraphEdge[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [query, setQuery] = useState(''); const [mode, setMode] = useState<'graph' | 'list'>('graph');
  const load = async () => { setLoading(true); setError(''); try { const res = await fetch('/api/v1/knowledge-graph'); const data = await res.json(); if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`); setNodes(data.nodes || []); setEdges(data.edges || []); } catch (err) { setError(err instanceof Error ? err.message : 'Unable to load knowledge graph'); } finally { setLoading(false); } };
  useEffect(() => { void load(); }, []);
  const visible = query.trim() ? nodes.filter((n) => n.label.toLowerCase().includes(query.toLowerCase()) || n.group.toLowerCase().includes(query.toLowerCase())) : nodes;
  return <div className="space-y-6">
    <div className="page-header"><div><div className="eyebrow"><Network className="w-4 h-4" /> KNOWLEDGE GRAPH</div><h1>Knowledge relationships</h1><p>Real document → chunk → knowledge relationships from the persistent store. Semantic edges can be added without changing this contract.</p></div><button className="secondary-button" onClick={() => void load()} disabled={loading}><RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh</button></div>
    <div className="toolbar"><div className="search-field"><Search className="w-4 h-4" /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter nodes…" /></div><div className="segmented"><button className={mode === 'graph' ? 'selected' : ''} onClick={() => setMode('graph')}>Graph</button><button className={mode === 'list' ? 'selected' : ''} onClick={() => setMode('list')}>Relations</button></div></div>
    {error && <div className="error-banner">Knowledge graph unavailable: {error}</div>}
    {loading ? <div className="empty-state"><RefreshCw className="w-7 h-7 animate-spin" /><p>Loading persisted relationships…</p></div> : mode === 'graph' ? <div className="graph-board"><div className="graph-grid" />{visible.length ? <div className="graph-node-grid">{visible.map((node) => <div className="graph-node" key={node.id}><div className="graph-node-icon"><Share2 className="w-4 h-4" /></div><strong>{node.label}</strong><span>{node.group}</span><small>{node.id}</small></div>)}</div> : <div className="graph-empty">No nodes match this filter.</div>}<div className="graph-footer">{visible.length} nodes · {edges.length} relationships</div></div> : <div className="data-table"><table><thead><tr><th>Source</th><th>Relation</th><th>Target</th></tr></thead><tbody>{edges.filter((e) => !query || `${e.source} ${e.target} ${e.relation}`.toLowerCase().includes(query.toLowerCase())).map((edge) => <tr key={edge.id}><td>{edge.source}</td><td><span className="status-chip">{edge.relation}</span></td><td>{edge.target}</td></tr>)}</tbody></table>{!edges.length && <div className="empty-inline">No persisted relationships yet.</div>}</div>}
  </div>;
};
