import React, { useEffect, useMemo, useState } from 'react';
import { Send, Bot, User, Sparkles, CheckCircle2, Cpu } from 'lucide-react';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  timestamp: string;
  executionId?: string;
  provenance?: unknown[];
  status?: string;
  retrievalUsed?: boolean;
  memoryUsed?: boolean;
}

const CONVERSATION_KEY = 'superagent.conversation.id';
const MESSAGES_KEY = 'superagent.conversation.messages';

export const ChatTab: React.FC = () => {
  const [conversationId, setConversationId] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [developerMode, setDeveloperMode] = useState(false);

  useEffect(() => {
    const storedId = localStorage.getItem(CONVERSATION_KEY) || crypto.randomUUID();
    setConversationId(storedId);
    localStorage.setItem(CONVERSATION_KEY, storedId);
    const storedMessages = localStorage.getItem(MESSAGES_KEY);
    if (storedMessages) {
      try { setMessages(JSON.parse(storedMessages) as Message[]); return; } catch { localStorage.removeItem(MESSAGES_KEY); }
    }
    setMessages([{ id: `msg-${Date.now()}`, sender: 'assistant', content: 'Hello! I am SuperAgent, your local-first AI orchestration assistant. How can I help you research, organize knowledge, or execute tasks today?', timestamp: new Date().toLocaleTimeString(), status: 'completed' }]);
  }, []);

  useEffect(() => { if (messages.length) localStorage.setItem(MESSAGES_KEY, JSON.stringify(messages)); }, [messages]);

  const history = useMemo(() => messages.map((message) => ({ role: message.sender, content: message.content })), [messages]);

  const handleSendMessage = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!inputMessage.trim() || loading || !conversationId) return;
    const userText = inputMessage.trim();
    const userMsg: Message = { id: `usr-${Date.now()}`, sender: 'user', content: userText, timestamp: new Date().toLocaleTimeString() };
    setMessages((previous) => [...previous, userMsg]);
    setInputMessage('');
    setLoading(true);
    try {
      const response = await fetch('/api/v1/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ conversation_id: conversationId, message: userText, conversation_history: history }) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setMessages((previous) => [...previous, { id: `asst-${Date.now()}`, sender: 'assistant', content: data.answer || 'No answer was returned.', timestamp: new Date().toLocaleTimeString(), executionId: data.execution_id, provenance: data.provenance || [], status: data.status, retrievalUsed: data.retrieval_used, memoryUsed: data.memory_used }]);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      setMessages((previous) => [...previous, { id: `err-${Date.now()}`, sender: 'assistant', content: `Error communicating with SuperAgent backend: ${message}`, timestamp: new Date().toLocaleTimeString(), status: 'failed' }]);
    } finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 bg-slate-50 border-b border-slate-200">
        <div className="flex items-center space-x-3"><div className="p-2 bg-blue-600 text-white rounded-lg"><Sparkles className="w-5 h-5" /></div><div><h2 className="text-base font-bold text-slate-900">SuperAgent Orchestration Chat</h2><p className="text-xs text-slate-500">Persistent local conversation context + RAG + execution telemetry</p></div></div>
        <label className="flex items-center space-x-2 text-xs font-medium text-slate-600 cursor-pointer"><input type="checkbox" checked={developerMode} onChange={(e) => setDeveloperMode(e.target.checked)} /><span>Developer Trace Mode</span></label>
      </div>
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((message) => <div key={message.id} className={`flex items-start space-x-3 ${message.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${message.sender === 'user' ? 'bg-slate-900 text-white' : 'bg-blue-50 text-blue-600 border border-blue-100'}`}>{message.sender === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}</div>
          <div className={`max-w-2xl rounded-2xl px-5 py-4 shadow-xs ${message.sender === 'user' ? 'bg-blue-600 text-white' : 'bg-slate-50 border border-slate-200 text-slate-900'}`}>
            <div className="flex items-center justify-between space-x-4 mb-1"><span className="text-xs font-semibold">{message.sender === 'user' ? 'You' : 'SuperAgent'}</span><span className="text-[10px] opacity-60">{message.timestamp}</span></div>
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
            {developerMode && message.executionId && <div className="mt-3 pt-3 border-t border-slate-200/60 text-xs font-mono space-y-1"><div className="flex items-center space-x-2"><Cpu className="w-3.5 h-3.5" /><span>Execution: {message.executionId}</span></div><div className="flex items-center space-x-2"><CheckCircle2 className="w-3.5 h-3.5" /><span>Status: {message.status} | Retrieval: {message.retrievalUsed ? 'Yes' : 'No'} | Memory: {message.memoryUsed ? 'Yes' : 'No'}</span></div></div>}
          </div>
        </div>)}
        {loading && <div className="flex items-center space-x-3"><Bot className="w-9 h-9 p-2 text-blue-600 animate-spin" /><div className="bg-slate-50 border border-slate-200 rounded-2xl px-5 py-3 text-sm text-slate-500">SuperAgent is reasoning and synthesizing...</div></div>}
      </div>
      <form onSubmit={handleSendMessage} className="p-4 bg-slate-50 border-t border-slate-200 flex items-center space-x-3"><input type="text" value={inputMessage} onChange={(e) => setInputMessage(e.target.value)} placeholder="Ask SuperAgent anything or request a task..." className="flex-1 px-4 py-3 bg-white border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" /><button type="submit" disabled={loading || !inputMessage.trim()} className="px-5 py-3 bg-blue-600 text-white font-medium rounded-xl disabled:opacity-50 flex items-center space-x-2"><span>Send</span><Send className="w-4 h-4" /></button></form>
    </div>
  );
};
