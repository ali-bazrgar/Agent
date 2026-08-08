import React, { useEffect, useState } from 'react';
import { Navbar } from './components/Navbar';
import { ChatTab } from './components/ChatTab';
import { DashboardTab } from './components/DashboardTab';
import { DataCenterTab } from './components/DataCenterTab';
import { KnowledgeGraphTab } from './components/KnowledgeGraphTab';
import { LearningTab } from './components/LearningTab';
import { ExecutionsTab } from './components/ExecutionsTab';
import { SettingsCenterTab } from './components/SettingsCenterTab';
import { ApiDocsTab } from './components/ApiDocsTab';
import { SystemHealth, MemoryRecord, Document, Flashcard, ExecutionState, MemoryKind, DueReview } from './types';
import { installDiagnostics, isDiagnosticsEnabled } from './diagnostics';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [flashcards, setFlashcards] = useState<Flashcard[]>([]);
  const [dueReviews, setDueReviews] = useState<DueReview[]>([]);
  const [executions, setExecutions] = useState<ExecutionState[]>([]);
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('superagent.theme') === 'dark');

  useEffect(() => {
    if (!isDiagnosticsEnabled()) return;
    return installDiagnostics();
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('superagent.theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  const safeFetchJson = async (url: string, init?: RequestInit) => {
    const res = await fetch(url, init);
    const contentType = res.headers.get('content-type') || '';
    if (!res.ok) throw new Error(`HTTP ${res.status} when fetching ${url}`);
    if (!contentType.includes('application/json')) throw new Error(`Expected JSON from ${url}`);
    return res.json();
  };

  const refreshHealth = async () => {
    try { setHealth(await safeFetchJson('/api/v1/health')); }
    catch (error) { console.error(error); }
  };

  const refreshExecutions = async () => {
    try { setExecutions(await safeFetchJson('/api/v1/executions')); }
    catch (error) { console.error(error); }
  };

  const refreshLearningData = async () => {
    const results = await Promise.allSettled([
      safeFetchJson('/api/v1/learning/flashcards'),
      safeFetchJson('/api/v1/learning/review?limit=50'),
    ]);
    if (results[0].status === 'fulfilled') setFlashcards(results[0].value);
    if (results[1].status === 'fulfilled') setDueReviews(results[1].value);
    results.filter((item) => item.status === 'rejected').forEach((item) => console.error(item.reason));
  };

  const fetchData = async () => {
    const results = await Promise.allSettled([
      safeFetchJson('/api/v1/health'), safeFetchJson('/api/v1/memories'), safeFetchJson('/api/v1/documents'),
      safeFetchJson('/api/v1/learning/flashcards'), safeFetchJson('/api/v1/learning/review?limit=50'), safeFetchJson('/api/v1/executions'),
    ]);
    const [healthRes, memRes, docRes, fcRes, dueRes, execRes] = results;
    if (healthRes.status === 'fulfilled') setHealth(healthRes.value);
    if (memRes.status === 'fulfilled') setMemories(memRes.value);
    if (docRes.status === 'fulfilled') setDocuments(docRes.value);
    if (fcRes.status === 'fulfilled') setFlashcards(fcRes.value);
    if (dueRes.status === 'fulfilled') setDueReviews(dueRes.value);
    if (execRes.status === 'fulfilled') setExecutions(execRes.value);
    results.filter((item) => item.status === 'rejected').forEach((item) => console.error(item.reason));
  };

  useEffect(() => {
    void fetchData();
    const healthTimer = window.setInterval(() => void refreshHealth(), 30000);
    const executionTimer = window.setInterval(() => void refreshExecutions(), 15000);
    const learningTimer = window.setInterval(() => void refreshLearningData(), 30000);
    return () => {
      window.clearInterval(healthTimer);
      window.clearInterval(executionTimer);
      window.clearInterval(learningTimer);
    };
  }, []);

  const handleCreateMemory = async (mem: { kind: MemoryKind; content: string; confidence: number; importance: number; relevance: number }) => {
    const newMem = await safeFetchJson('/api/v1/memories', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(mem) });
    setMemories((prev) => [newMem, ...prev]);
  };
  const handleDeleteMemory = async (id: string) => { const res = await fetch(`/api/v1/memories/${id}`, { method: 'DELETE' }); if (!res.ok) throw new Error(`HTTP ${res.status}`); setMemories((prev) => prev.filter((m) => m.memory_id !== id)); };
  const handleCreateDocument = async (doc: { title: string; content: string; document_type: string }) => { const newDoc = await safeFetchJson('/api/v1/documents', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(doc) }); setDocuments((prev) => [newDoc, ...prev]); };
  const handleDeleteDocument = async (id: string) => { const res = await fetch(`/api/v1/documents/${id}`, { method: 'DELETE' }); if (!res.ok) throw new Error(`HTTP ${res.status}`); setDocuments((prev) => prev.filter((document) => document.document_id !== id)); };
  const handleCreateFlashcard = async (fc: { front: string; back: string; difficulty: number }) => { const newFc = await safeFetchJson('/api/v1/learning/flashcards', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(fc) }); setFlashcards((prev) => [newFc, ...prev]); await refreshLearningData(); };
  const handleReviewFlashcard = async (id: string, rating: 'again' | 'hard' | 'good' | 'easy') => { await safeFetchJson('/api/v1/learning/review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ flashcard_id: id, rating }) }); await refreshLearningData(); };
  const handleTriggerExecution = async (taskDescription: string) => { const newExec = await safeFetchJson('/api/v1/executions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_description: taskDescription }) }); setExecutions((prev) => [newExec, ...prev]); };

  return (
    <div className="app-shell min-h-screen flex flex-col">
      <Navbar health={health} activeTab={activeTab} setActiveTab={setActiveTab} darkMode={darkMode} setDarkMode={setDarkMode} />
      <main className="flex-1 w-full max-w-[1500px] mx-auto px-4 sm:px-6 xl:px-8 py-6 sm:py-8">
        {activeTab === 'chat' && <ChatTab />}
        {activeTab === 'overview' && <DashboardTab health={health} documentsCount={documents.length} memoriesCount={memories.length} flashcardsCount={flashcards.length} executionsCount={executions.length} onTriggerExecution={handleTriggerExecution} />}
        {activeTab === 'datacenter' && <DataCenterTab documents={documents} memories={memories} flashcards={flashcards} onCreateDocument={handleCreateDocument} onDeleteDocument={handleDeleteDocument} onCreateMemory={handleCreateMemory} onDeleteMemory={handleDeleteMemory} />}
        {activeTab === 'knowledge_graph' && <KnowledgeGraphTab />}
        {activeTab === 'learning' && <LearningTab flashcards={flashcards} dueReviews={dueReviews} onCreateFlashcard={handleCreateFlashcard} onReviewFlashcard={handleReviewFlashcard} />}
        {activeTab === 'executions' && <ExecutionsTab executions={executions} onTriggerExecution={handleTriggerExecution} />}
        {activeTab === 'settings' && <SettingsCenterTab darkMode={darkMode} setDarkMode={setDarkMode} />}
        {activeTab === 'api' && <ApiDocsTab />}
      </main>
      <footer className="app-footer"><span>SuperAgent · Local-first AI orchestration</span><span>FastAPI · React · llama.cpp</span></footer>
    </div>
  );
}
