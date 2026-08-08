import React, { useState } from 'react';
import { Document } from '../types';
import { BookOpen, Plus, FileText, Hash, Layers, Trash2, Search } from 'lucide-react';

interface KnowledgeTabProps {
  documents: Document[];
  onCreateDocument: (doc: { title: string; content: string; document_type: string }) => void;
  onDeleteDocument: (id: string) => void;
}

export const KnowledgeTab: React.FC<KnowledgeTabProps> = ({
  documents,
  onCreateDocument,
  onDeleteDocument,
}) => {
  const [showModal, setShowModal] = useState(false);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [docType, setDocType] = useState('technical_spec');
  const [searchTerm, setSearchTerm] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) return;
    onCreateDocument({ title, content, document_type: docType });
    setTitle('');
    setContent('');
    setShowModal(false);
  };

  const filteredDocs = documents.filter(
    (d) =>
      d.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.chunks.some((c) => c.content.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center space-x-2">
            <BookOpen className="w-5 h-5 text-emerald-600" />
            <h2 className="text-lg font-bold text-slate-900">Knowledge Ingestion & Chunking</h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Lexical and vector indexed knowledge documents split into deterministic RAG context chunks.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl transition-colors flex items-center justify-center space-x-2 shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>Ingest Document</span>
        </button>
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search documents and RAG chunks..."
          className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 shadow-xs"
        />
      </div>

      {/* Document List */}
      <div className="space-y-4">
        {filteredDocs.map((doc) => (
          <div
            key={doc.document_id}
            className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4"
          >
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <FileText className="w-4 h-4 text-emerald-600" />
                  <h3 className="font-bold text-slate-900 text-base">{doc.title}</h3>
                  <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-[11px] font-mono font-medium rounded-md border border-emerald-100">
                    {doc.document_type}
                  </span>
                </div>
                <div className="flex items-center space-x-3 text-xs text-slate-400 font-mono">
                  <span>ID: {doc.document_id}</span>
                  <span>·</span>
                  <span>Version {doc.version}</span>
                  <span>·</span>
                  <span>{doc.chunks?.length || 0} Chunks</span>
                </div>
              </div>

              <button
                onClick={() => onDeleteDocument(doc.document_id)}
                className="text-slate-400 hover:text-red-600 p-1.5 rounded-lg hover:bg-slate-50 transition-colors"
                title="Delete document"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            {/* Chunks Inspector */}
            <div className="space-y-2">
              <div className="flex items-center space-x-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <Layers className="w-3.5 h-3.5" />
                <span>Indexed RAG Chunks</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {doc.chunks.map((chunk) => (
                  <div
                    key={chunk.chunk_id}
                    className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between text-slate-400 font-mono text-[10px]">
                      <span>Chunk #{chunk.chunk_index}</span>
                      <span>~{chunk.token_count} tokens</span>
                    </div>
                    <p className="text-slate-700 leading-relaxed font-mono text-[11px]">
                      {chunk.content}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}

        {filteredDocs.length === 0 && (
          <div className="bg-white p-12 text-center rounded-2xl border border-dashed border-slate-300 space-y-3">
            <BookOpen className="w-8 h-8 text-slate-300 mx-auto" />
            <p className="text-sm text-slate-500 font-medium">No documents match search "{searchTerm}"</p>
          </div>
        )}
      </div>

      {/* Ingest Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-base">Ingest Knowledge Document</h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Document Title</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Memory Model Specification"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Document Type</label>
                <input
                  type="text"
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  placeholder="technical_spec, architecture_doc, user_guide"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Full Document Content</label>
                <textarea
                  required
                  rows={5}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Paste document markdown or text content here. It will be automatically chunked..."
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono text-xs"
                />
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
                  className="px-4 py-2 bg-emerald-600 text-white rounded-xl text-xs font-semibold hover:bg-emerald-500 shadow-xs"
                >
                  Process & Chunk
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
