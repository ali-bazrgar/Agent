import React, { useState } from 'react';
import { MemoryRecord, MemoryKind } from '../types';
import { Brain, Plus, Trash2, Filter, Sparkles, Tag, ShieldAlert } from 'lucide-react';

interface MemoryTabProps {
  memories: MemoryRecord[];
  onCreateMemory: (mem: { kind: MemoryKind; content: string; confidence: number; importance: number; relevance: number }) => void;
  onDeleteMemory: (id: string) => void;
}

const memoryKinds: MemoryKind[] = [
  'working',
  'session',
  'episodic',
  'semantic',
  'procedural',
  'user',
  'temporal',
];

export const MemoryTab: React.FC<MemoryTabProps> = ({
  memories,
  onCreateMemory,
  onDeleteMemory,
}) => {
  const [selectedKind, setSelectedKind] = useState<string>('all');
  const [showModal, setShowModal] = useState(false);
  const [content, setContent] = useState('');
  const [kind, setKind] = useState<MemoryKind>('working');
  const [confidence, setConfidence] = useState(0.9);
  const [importance, setImportance] = useState(0.8);
  const [relevance, setRelevance] = useState(0.85);

  const filteredMemories = selectedKind === 'all'
    ? memories
    : memories.filter((m) => m.kind === selectedKind);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    onCreateMemory({
      kind,
      content,
      confidence,
      importance,
      relevance,
    });
    setContent('');
    setShowModal(false);
  };

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center space-x-2">
            <Brain className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-bold text-slate-900">7-Type Memory Engine</h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Deterministic layer separating working memory, session history, procedural rules & semantic facts.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl transition-colors flex items-center justify-center space-x-2 shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>New Memory Record</span>
        </button>
      </div>

      {/* Filter Chips */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-1">
        <button
          onClick={() => setSelectedKind('all')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
            selectedKind === 'all'
              ? 'bg-slate-900 text-white'
              : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
          }`}
        >
          All ({memories.length})
        </button>
        {memoryKinds.map((k) => {
          const count = memories.filter((m) => m.kind === k).length;
          return (
            <button
              key={k}
              onClick={() => setSelectedKind(k)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors whitespace-nowrap ${
                selectedKind === k
                  ? 'bg-slate-900 text-white'
                  : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
              }`}
            >
              {k} ({count})
            </button>
          );
        })}
      </div>

      {/* Memory List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredMemories.map((mem) => (
          <div
            key={mem.memory_id}
            className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3 relative group hover:border-slate-300 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-2">
                <span className="px-2.5 py-1 bg-slate-100 text-slate-800 rounded-md text-xs font-mono font-semibold capitalize border border-slate-200">
                  {mem.kind}
                </span>
                <span className="font-mono text-xs text-slate-400">{mem.memory_id}</span>
              </div>
              <button
                onClick={() => onDeleteMemory(mem.memory_id)}
                className="text-slate-400 hover:text-red-600 p-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity"
                title="Delete memory"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            <p className="text-sm text-slate-800 leading-relaxed font-normal">
              {mem.content}
            </p>

            {/* Metrics Bar */}
            <div className="grid grid-cols-3 gap-2 pt-3 border-t border-slate-100 text-xs">
              <div className="bg-slate-50 p-2 rounded-lg text-center">
                <div className="text-slate-400 text-[10px] uppercase font-semibold">Confidence</div>
                <div className="font-mono font-bold text-slate-700">{(mem.confidence * 100).toFixed(0)}%</div>
              </div>
              <div className="bg-slate-50 p-2 rounded-lg text-center">
                <div className="text-slate-400 text-[10px] uppercase font-semibold">Importance</div>
                <div className="font-mono font-bold text-slate-700">{(mem.importance * 100).toFixed(0)}%</div>
              </div>
              <div className="bg-slate-50 p-2 rounded-lg text-center">
                <div className="text-slate-400 text-[10px] uppercase font-semibold">Relevance</div>
                <div className="font-mono font-bold text-slate-700">{(mem.relevance * 100).toFixed(0)}%</div>
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
              <span>Source: {mem.source?.title || 'System'}</span>
              <span>{new Date(mem.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        ))}

        {filteredMemories.length === 0 && (
          <div className="col-span-full bg-white p-12 text-center rounded-2xl border border-dashed border-slate-300 space-y-3">
            <Brain className="w-8 h-8 text-slate-300 mx-auto" />
            <p className="text-sm text-slate-500 font-medium">No memory records found for filter "{selectedKind}"</p>
          </div>
        )}
      </div>

      {/* New Memory Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-base">Create Memory Record</h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Memory Kind</label>
                <select
                  value={kind}
                  onChange={(e) => setKind(e.target.value as MemoryKind)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm capitalize text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {memoryKinds.map((k) => (
                    <option key={k} value={k}>{k}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Memory Content</label>
                <textarea
                  required
                  rows={3}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Enter explicit factual observation or procedural rule..."
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Confidence</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={confidence}
                    onChange={(e) => setConfidence(parseFloat(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Importance</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={importance}
                    onChange={(e) => setImportance(parseFloat(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Relevance</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={relevance}
                    onChange={(e) => setRelevance(parseFloat(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-xs font-medium hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-semibold hover:bg-blue-500 shadow-xs"
                >
                  Save Record
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
