import React, { useState, useEffect } from 'react';
import { Network, Share2, Layers, BookOpen, CheckCircle2 } from 'lucide-react';

export const KnowledgeGraphTab: React.FC = () => {
  const [graphData, setGraphData] = useState<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] });
  const [viewMode, setViewMode] = useState<'graph' | 'list'>('graph');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/v1/knowledge-graph')
      .then((res) => res.json())
      .then((data) => {
        setGraphData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load knowledge graph:', err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-purple-600 text-white rounded-xl">
            <Network className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">Knowledge Relationship Graph</h1>
            <p className="text-xs text-slate-500">Semantic connections, prerequisites, and hierarchical links across SuperAgent</p>
          </div>
        </div>

        <div className="flex items-center space-x-2 bg-slate-100 p-1 rounded-xl">
          <button
            onClick={() => setViewMode('graph')}
            className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
              viewMode === 'graph' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Graph View
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
              viewMode === 'list' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            List / Table View
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-500">Loading knowledge relationships...</div>
      ) : viewMode === 'graph' ? (
        <div className="bg-slate-900 rounded-2xl p-8 text-white min-h-[450px] flex flex-col items-center justify-center relative overflow-hidden shadow-lg">
          <div className="absolute inset-0 bg-[radial-gradient(#334155_1px,transparent_1px)] [background-size:16px_16px] opacity-30" />
          
          <div className="relative z-10 grid grid-cols-1 md:grid-cols-3 gap-8 w-full max-w-4xl items-center justify-center">
            {graphData.nodes.map((node, idx) => (
              <div
                key={node.id}
                className="bg-slate-800/90 border border-slate-700 p-5 rounded-2xl shadow-xl backdrop-blur-md flex flex-col items-center text-center space-y-2 hover:border-blue-500 transition-all"
              >
                <div className="p-3 bg-blue-500/20 text-blue-400 rounded-xl">
                  <Share2 className="w-5 h-5" />
                </div>
                <div className="font-bold text-sm text-white">{node.label}</div>
                <span className="px-2.5 py-0.5 bg-slate-700 text-slate-300 rounded-full text-[10px] font-mono">
                  {node.group}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-8 text-xs text-slate-400 font-mono">
            Connected graph nodes: {graphData.nodes.length} | Relationships: {graphData.edges.length}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-600">
                <th className="px-6 py-4">Source ID</th>
                <th className="px-6 py-4">Target ID</th>
                <th className="px-6 py-4">Relation Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-sm">
              {graphData.edges.map((edge) => (
                <tr key={edge.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="px-6 py-4 font-mono text-xs font-semibold text-slate-900">{edge.source}</td>
                  <td className="px-6 py-4 font-mono text-xs font-semibold text-slate-900">{edge.target}</td>
                  <td className="px-6 py-4">
                    <span className="px-2.5 py-1 bg-purple-50 text-purple-700 rounded-lg text-xs font-medium">
                      {edge.relation}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
