import React, { useState } from 'react';
import { Send, Bot, User, Sparkles, Terminal, CheckCircle2, ShieldAlert, Cpu } from 'lucide-react';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  timestamp: string;
  executionId?: string;
  provenance?: any[];
  status?: string;
  retrievalUsed?: boolean;
  memoryUsed?: boolean;
}

export const ChatTab: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-1',
      sender: 'assistant',
      content: 'Hello! I am SuperAgent, your local-first AI orchestration assistant. How can I help you research, organize knowledge, or execute tasks today?',
      timestamp: new Date().toLocaleTimeString(),
      status: 'completed',
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [developerMode, setDeveloperMode] = useState(false);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || loading) return;

    const userText = inputMessage.trim();
    setInputMessage('');

    const userMsg: Message = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      content: userText,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();

      const assistantMsg: Message = {
        id: `asst-${Date.now()}`,
        sender: 'assistant',
        content: data.answer || 'Response received from SuperAgent orchestrator.',
        timestamp: new Date().toLocaleTimeString(),
        executionId: data.execution_id,
        provenance: data.provenance || [],
        status: data.status,
        retrievalUsed: data.retrieval_used,
        memoryUsed: data.memory_used,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: Message = {
        id: `err-${Date.now()}`,
        sender: 'assistant',
        content: `Error communicating with SuperAgent backend: ${err.message || 'Unknown error'}. Please check model configuration in Settings.`,
        timestamp: new Date().toLocaleTimeString(),
        status: 'failed',
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center justify-between px-6 py-4 bg-slate-50 border-b border-slate-200">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-blue-600 text-white rounded-lg">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">SuperAgent Orchestration Chat</h2>
            <p className="text-xs text-slate-500">Connected to local SQLite persistence & RAG retrieval engine</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <label className="flex items-center space-x-2 text-xs font-medium text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={developerMode}
              onChange={(e) => setDeveloperMode(e.target.checked)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <span>Developer Trace Mode</span>
          </label>
        </div>
      </div>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start space-x-3 ${msg.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}
          >
            <div
              className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
                msg.sender === 'user' ? 'bg-slate-900 text-white' : 'bg-blue-50 text-blue-600 border border-blue-100'
              }`}
            >
              {msg.sender === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
            </div>
            <div
              className={`max-w-2xl rounded-2xl px-5 py-4 shadow-xs ${
                msg.sender === 'user'
                  ? 'bg-blue-600 text-white rounded-tr-none'
                  : 'bg-slate-50 border border-slate-200/80 text-slate-900 rounded-tl-none'
              }`}
            >
              <div className="flex items-center justify-between space-x-4 mb-1">
                <span className={`text-xs font-semibold ${msg.sender === 'user' ? 'text-blue-100' : 'text-slate-500'}`}>
                  {msg.sender === 'user' ? 'You' : 'SuperAgent'}
                </span>
                <span className={`text-[10px] ${msg.sender === 'user' ? 'text-blue-200' : 'text-slate-400'}`}>
                  {msg.timestamp}
                </span>
              </div>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>

              {/* Developer / Execution metadata badges */}
              {developerMode && msg.executionId && (
                <div className="mt-3 pt-3 border-t border-slate-200/60 text-xs font-mono space-y-1 text-slate-600">
                  <div className="flex items-center space-x-2">
                    <Cpu className="w-3.5 h-3.5 text-blue-600" />
                    <span>Execution ID: {msg.executionId}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Status: {msg.status} | Retrieval: {msg.retrievalUsed ? 'Yes' : 'No'} | Memory: {msg.memoryUsed ? 'Yes' : 'No'}</span>
                  </div>
                  {msg.provenance && msg.provenance.length > 0 && (
                    <div className="text-[11px] text-slate-500">
                      Provenance references: {msg.provenance.length} attached
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center">
              <Bot className="w-5 h-5 animate-spin" />
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-2xl px-5 py-3 text-sm text-slate-500">
              SuperAgent orchestrator is reasoning and synthesizing response...
            </div>
          </div>
        )}
      </div>

      {/* Input Form */}
      <form onSubmit={handleSendMessage} className="p-4 bg-slate-50 border-t border-slate-200 flex items-center space-x-3">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Ask SuperAgent anything or request a task execution..."
          className="flex-1 px-4 py-3 bg-white border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <button
          type="submit"
          disabled={loading || !inputMessage.trim()}
          className="px-5 py-3 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center space-x-2 shadow-xs"
        >
          <span>Send</span>
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
