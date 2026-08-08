import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { OverviewTab } from './components/OverviewTab';
import { MemoryTab } from './components/MemoryTab';
import { KnowledgeTab } from './components/KnowledgeTab';
import { LearningTab } from './components/LearningTab';
import { ExecutionsTab } from './components/ExecutionsTab';
import { ApiDocsTab } from './components/ApiDocsTab';

import {
  SystemHealth,
  MemoryRecord,
  Document,
  Flashcard,
  ExecutionState,
  MemoryKind,
} from './types';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [flashcards, setFlashcards] = useState<Flashcard[]>([]);
  const [executions, setExecutions] = useState<ExecutionState[]>([]);

  // Fetch initial state from Express backend
  const fetchData = async () => {
    try {
      const [healthRes, memRes, docRes, fcRes, execRes] = await Promise.all([
        fetch('/api/v1/health').then((r) => r.json()),
        fetch('/api/v1/memories').then((r) => r.json()),
        fetch('/api/v1/documents').then((r) => r.json()),
        fetch('/api/v1/flashcards').then((r) => r.json()),
        fetch('/api/v1/executions').then((r) => r.json()),
      ]);

      setHealth(healthRes);
      setMemories(memRes);
      setDocuments(docRes);
      setFlashcards(fcRes);
      setExecutions(execRes);
    } catch (err) {
      console.error('Error fetching backend data:', err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  // Handlers
  const handleCreateMemory = async (mem: {
    kind: MemoryKind;
    content: string;
    confidence: number;
    importance: number;
    relevance: number;
  }) => {
    try {
      const res = await fetch('/api/v1/memories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mem),
      });
      if (res.ok) {
        const newMem = await res.json();
        setMemories((prev) => [newMem, ...prev]);
      }
    } catch (err) {
      console.error('Failed to create memory:', err);
    }
  };

  const handleDeleteMemory = async (id: string) => {
    try {
      await fetch(`/api/v1/memories/${id}`, { method: 'DELETE' });
      setMemories((prev) => prev.filter((m) => m.memory_id !== id));
    } catch (err) {
      console.error('Failed to delete memory:', err);
    }
  };

  const handleCreateDocument = async (doc: {
    title: string;
    content: string;
    document_type: string;
  }) => {
    try {
      const res = await fetch('/api/v1/documents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(doc),
      });
      if (res.ok) {
        const newDoc = await res.json();
        setDocuments((prev) => [newDoc, ...prev]);
      }
    } catch (err) {
      console.error('Failed to create document:', err);
    }
  };

  const handleDeleteDocument = async (id: string) => {
    try {
      await fetch(`/api/v1/documents/${id}`, { method: 'DELETE' });
      setDocuments((prev) => prev.filter((d) => d.document_id !== id));
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  const handleCreateFlashcard = async (fc: {
    front: string;
    back: string;
    difficulty: number;
  }) => {
    try {
      const res = await fetch('/api/v1/flashcards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fc),
      });
      if (res.ok) {
        const newFc = await res.json();
        setFlashcards((prev) => [newFc, ...prev]);
      }
    } catch (err) {
      console.error('Failed to create flashcard:', err);
    }
  };

  const handleReviewFlashcard = async (
    id: string,
    outcome: 'correct' | 'incorrect' | 'easy' | 'hard'
  ) => {
    try {
      await fetch(`/api/v1/flashcards/${id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ outcome }),
      });
    } catch (err) {
      console.error('Failed to review flashcard:', err);
    }
  };

  const handleTriggerExecution = async (taskDescription: string) => {
    try {
      const res = await fetch('/api/v1/executions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_description: taskDescription }),
      });
      if (res.ok) {
        const newExec = await res.json();
        setExecutions((prev) => [newExec, ...prev]);
      }
    } catch (err) {
      console.error('Failed to trigger execution:', err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <Navbar health={health} activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'overview' && (
          <OverviewTab
            health={health}
            memories={memories}
            documents={documents}
            flashcards={flashcards}
            executions={executions}
            onTriggerExecution={handleTriggerExecution}
          />
        )}

        {activeTab === 'memory' && (
          <MemoryTab
            memories={memories}
            onCreateMemory={handleCreateMemory}
            onDeleteMemory={handleDeleteMemory}
          />
        )}

        {activeTab === 'knowledge' && (
          <KnowledgeTab
            documents={documents}
            onCreateDocument={handleCreateDocument}
            onDeleteDocument={handleDeleteDocument}
          />
        )}

        {activeTab === 'learning' && (
          <LearningTab
            flashcards={flashcards}
            onCreateFlashcard={handleCreateFlashcard}
            onReviewFlashcard={handleReviewFlashcard}
          />
        )}

        {activeTab === 'executions' && (
          <ExecutionsTab
            executions={executions}
            onTriggerExecution={handleTriggerExecution}
          />
        )}

        {activeTab === 'api' && <ApiDocsTab />}
      </main>

      <footer className="bg-white border-t border-slate-200 py-6 mt-12 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>SuperAgent AI Orchestration Platform · Local-First Foundation</span>
          <span>FastAPI Compatible API · Express & React Node.js Runtime</span>
        </div>
      </footer>
    </div>
  );
}
