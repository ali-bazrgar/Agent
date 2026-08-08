import React, { useState } from 'react';
import { Database, BookOpen, Brain, Layers, Search, Trash2, Plus, FileText, CheckCircle2 } from 'lucide-react';
import { Document, MemoryRecord, Flashcard } from '../types';

interface DataCenterTabProps {
  documents: Document[];
  memories: MemoryRecord[];
  flashcards: Flashcard[];
  onCreateDocument: (doc: { title: string; content: string; document_type: string }) => void;
  onDeleteDocument: (id: string) => void;
  onCreateMemory: (mem: any) => void;
  onDeleteMemory: (id: string) => void;
}

export const DataCenterTab: React.FC<DataCenterTabProps> = ({
  documents,
  memories,
  flashcards,
  onCreateDocument,
  onDeleteDocument,
  onCreateMemory,
  onDeleteMemory,
}) => {
  const [subTab, setSubTab] = useState<'documents' | 'memories' | 'flashcards'>('documents');
  const [searchTerm, setSearchTerm] = useState('');

  // Modal / Form state for adding document
  const [showDocModal, setShowDocModal] = useState(false);
  const [docTitle, setDocTitle] = useState('');
  const [docContent, setDocContent] = useState('');

  const handleDocSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!docTitle || !docContent) return;
    onCreateDocument({ title: docTitle, content: docContent, document_type: 'user_upload' });
    setDocTitle('');
    setDocContent('');
    setShowDocModal(false);
  };

  return (
    <div className="space-y-6">
      {/* Header & Sub-navigation */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-slate-900 text-white rounded-xl">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900">Data Center & Knowledge Base</h1>
              <p className="text-xs text-slate-500">Centralized inspection of persistent documents, chunks, memories, and flashcards</p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 bg-slate-100 p-1 rounded-xl">
          <button
            onClick={() => setSubTab('documents')}
            className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
              subTab === 'documents' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Documents ({documents.length})
          </button>
          <button
            onClick={() => setSubTab('memories')}
            className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
              subTab === 'memories' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Memories ({memories.length})
          </button>
          <button
            onClick={() => setSubTab('flashcards')}
            className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
              subTab === 'flashcards' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Flashcards ({flashcards.length})
          </button>
        </div>
      </div>

      {/* Actions & Search */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search persistent records..."
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        {subTab === 'documents' && (
          <button
            onClick={() => setShowDocModal(true)}
            className="w-full sm:w-auto px-5 py-2.5 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 transition-colors flex items-center justify-center space-x-2 text-sm shadow-xs"
          >
            <Plus className="w-4 h-4" />
            <span>Ingest New Document</span>
          </button>
        )}
      </div>

      {/* Content Table / Cards */}
      {subTab === 'documents' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-600">
                  <th className="px-6 py-4">Title & ID</th>
                  <th className="px-6 py-4">Type</th>
                  <th className="px-6 py-4">Chunks</th>
                  <th className="px-6 py-4">Created</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-sm">
                {documents.map((doc) => (
                  <tr key={doc.document_id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-semibold text-slate-900">{doc.title}</div>
                      <div className="text-xs font-mono text-slate-400">{doc.document_id}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2.5 py-1 bg-blue-50 text-blue-700 rounded-lg text-xs font-medium">
                        {doc.document_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-600 font-mono text-xs">
                      {doc.chunks?.length || 0} chunks
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => onDeleteDocument(doc.document_id)}
                        className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Delete Document"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {subTab === 'memories' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {memories.map((mem) => (
            <div key={mem.memory_id} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-lg text-xs font-semibold uppercase">
                  {mem.kind}
                </span>
                <span className="text-xs font-mono text-slate-400">{mem.memory_id}</span>
              </div>
              <p className="text-sm text-slate-800 leading-relaxed">{mem.content}</p>
              <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs text-slate-500">
                <span>Confidence: {(mem.confidence * 100).toFixed(0)}%</span>
                <button
                  onClick={() => onDeleteMemory(mem.memory_id)}
                  className="text-red-600 hover:underline flex items-center space-x-1"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Delete</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {subTab === 'flashcards' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {flashcards.map((fc) => (
            <div key={fc.flashcard_id} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-1 bg-purple-50 text-purple-700 rounded-lg text-xs font-semibold">
                  Difficulty: {fc.difficulty}
                </span>
                <span className="text-xs font-mono text-slate-400">{fc.flashcard_id}</span>
              </div>
              <div>
                <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Front</div>
                <div className="text-sm font-semibold text-slate-900 mt-0.5">{fc.front}</div>
              </div>
              <div>
                <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Back</div>
                <div className="text-sm text-slate-700 mt-0.5">{fc.back}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal for adding document */}
      {showDocModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-xl">
            <h3 className="text-lg font-bold text-slate-900">Ingest Knowledge Document</h3>
            <form onSubmit={handleDocSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Document Title</label>
                <input
                  type="text"
                  required
                  value={docTitle}
                  onChange={(e) => setDocTitle(e.target.value)}
                  placeholder="e.g. Advanced Agentic Architecture"
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Content / Markdown</label>
                <textarea
                  required
                  rows={6}
                  value={docContent}
                  onChange={(e) => setDocContent(e.target.value)}
                  placeholder="Paste document text or markdown content here..."
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowDocModal(false)}
                  className="px-4 py-2.5 bg-slate-100 text-slate-700 font-medium rounded-xl hover:bg-slate-200 text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2.5 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 text-sm shadow-xs"
                >
                  Ingest & Chunk
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
