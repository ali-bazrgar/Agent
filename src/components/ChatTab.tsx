import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Paperclip, Send, Bot, User, Sparkles, CheckCircle2, Cpu, X, Image, Mic, Film, FileText, SlidersHorizontal } from 'lucide-react';
import './ChatTab.css';

type AttachmentKind = 'image' | 'audio' | 'video' | 'file';
interface Attachment { name: string; mime_type: string; kind: AttachmentKind; data: string; text_content?: string; }
interface Message { id: string; sender: 'user' | 'assistant'; content: string; timestamp: string; executionId?: string; provenance?: unknown[]; status?: string; retrievalUsed?: boolean; memoryUsed?: boolean; toolsUsed?: boolean; attachments?: Pick<Attachment, 'name' | 'mime_type' | 'kind'>[]; telemetry?: { contextWindow?: number; promptTokens?: number; outputTokens?: number; totalTokens?: number; promptTps?: number; generationTps?: number; memoryTokens?: number; knowledgeTokens?: number }; requestId?: string; }
const CONVERSATION_KEY = 'superagent.conversation.id';
const MESSAGES_KEY = 'superagent.conversation.messages';
const CHAT_OPTIONS_KEY = 'superagent.chat.options';
const MAX_BYTES = 12 * 1024 * 1024;
interface ChatOptions { contextWindow: number; reasoningMode: 'auto' | 'on' | 'off'; }
const DEFAULT_OPTIONS: ChatOptions = { contextWindow: 8192, reasoningMode: 'auto' };
function kindForFile(file: File): AttachmentKind { if (file.type.startsWith('image/')) return 'image'; if (file.type.startsWith('audio/')) return 'audio'; if (file.type.startsWith('video/')) return 'video'; return 'file'; }
function toBase64(file: File): Promise<string> { return new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => { const value = String(reader.result || ''); resolve(value.includes(',') ? value.split(',', 2)[1] : value); }; reader.onerror = () => reject(reader.error || new Error('Unable to read file')); reader.readAsDataURL(file); }); }

export const ChatTab: React.FC = () => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [conversationId, setConversationId] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [loading, setLoading] = useState(false);
  const [developerMode, setDeveloperMode] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState('');
  const [showControls, setShowControls] = useState(false);
  const [modelContextMax, setModelContextMax] = useState<number | null>(null);
  const [options, setOptions] = useState<ChatOptions>(() => { try { return { ...DEFAULT_OPTIONS, ...JSON.parse(localStorage.getItem(CHAT_OPTIONS_KEY) || '{}') }; } catch { return DEFAULT_OPTIONS; } });

  useEffect(() => {
    const storedId = localStorage.getItem(CONVERSATION_KEY) || crypto.randomUUID();
    setConversationId(storedId); localStorage.setItem(CONVERSATION_KEY, storedId);
    const storedMessages = localStorage.getItem(MESSAGES_KEY);
    if (storedMessages) { try { setMessages(JSON.parse(storedMessages) as Message[]); } catch { localStorage.removeItem(MESSAGES_KEY); } }
    else setMessages([{ id: `msg-${Date.now()}`, sender: 'assistant', content: 'SuperAgent is ready. Ask a question, research a topic, or attach an image, audio, video, or file.', timestamp: new Date().toLocaleTimeString(), status: 'completed' }]);
    void fetch('/api/v1/config').then(async (r) => r.ok ? r.json() : null).then((config) => { const maximum = config?.llm?.capabilities?.context_window_tokens; if (typeof maximum === 'number' && maximum >= 256) { setModelContextMax(maximum); setOptions((current) => ({ ...current, contextWindow: Math.min(Math.max(current.contextWindow, 256), maximum) })); } }).catch(() => undefined);
  }, []);
  useEffect(() => { if (messages.length) localStorage.setItem(MESSAGES_KEY, JSON.stringify(messages)); }, [messages]);
  useEffect(() => { localStorage.setItem(CHAT_OPTIONS_KEY, JSON.stringify(options)); }, [options]);
  const history = useMemo(() => messages.filter((m) => m.status !== 'failed').map((m) => ({ role: m.sender, content: m.content })), [messages]);
  const addFiles = async (files: FileList | File[]) => { setError(''); const incoming = Array.from(files); if (incoming.length + attachments.length > 8) { setError('Maximum 8 attachments per message.'); return; } const next: Attachment[] = []; for (const file of incoming) { if (file.size > MAX_BYTES) { setError(`${file.name} is larger than 12 MiB.`); continue; } try { const kind = kindForFile(file); const data = await toBase64(file); let text_content: string | undefined; if (kind === 'file' && (file.type.startsWith('text/') || /\.(md|txt|json|csv|xml|py|ts|tsx|js|css|html)$/i.test(file.name)) && file.size <= 2 * 1024 * 1024) text_content = await file.text(); next.push({ name: file.name, mime_type: file.type || 'application/octet-stream', kind, data, text_content }); } catch { setError(`Could not read ${file.name}.`); } } setAttachments((prev) => [...prev, ...next]); };

  const appendAssistantText = (id: string, delta: string) => {
    if (!delta) return;
    setMessages((previous) => previous.map((message) => message.id === id ? { ...message, content: `${message.content}${delta}` } : message));
  };

  const handleSendMessage = async (event: React.FormEvent) => {
    event.preventDefault();
    if ((!inputMessage.trim() && !attachments.length) || loading || !conversationId) return;
    const userText = inputMessage.trim() || 'Please analyze the attached files.';
    const userMsg: Message = { id: `usr-${Date.now()}`, sender: 'user', content: userText, timestamp: new Date().toLocaleTimeString(), attachments: attachments.map(({ name, mime_type, kind }) => ({ name, mime_type, kind })) };
    const outgoing = attachments;
    const assistantId = `asst-${Date.now()}`;
    const requestId = `web-${crypto.randomUUID()}`;
    setMessages((previous) => [...previous, userMsg, { id: assistantId, sender: 'assistant', content: '', timestamp: new Date().toLocaleTimeString(), status: 'streaming', requestId }]);
    setInputMessage(''); setAttachments([]); setLoading(true); setError('');
    try {
      const response = await fetch('/api/v1/chat/stream', { method: 'POST', headers: { 'Content-Type': 'application/json', 'x-request-id': requestId }, body: JSON.stringify({ conversation_id: conversationId, message: userText, conversation_history: history, attachments: outgoing, runtime_options: { context_window: options.contextWindow, reasoning_mode: options.reasoningMode } }) });
      const responseRequestId = response.headers.get('x-request-id') || requestId;
      if (!response.ok || !response.body) {
        const data = await response.json().catch(() => ({}));
        const detail = typeof data?.detail === 'string' ? data.detail : `HTTP ${response.status}`;
        throw new Error(`${detail} (request ${responseRequestId})`);
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let finished = false;
      while (!finished) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split(/\r?\n\r?\n/);
        buffer = frames.pop() || '';
        for (const frame of frames) {
          const lines = frame.split(/\r?\n/);
          const eventName = lines.find((line) => line.startsWith('event:'))?.slice(6).trim() || 'message';
          const dataText = lines.filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trimStart()).join('\n');
          if (!dataText) continue;
          if (eventName === 'token') {
            try {
              const eventData = JSON.parse(dataText) as { text?: string };
              appendAssistantText(assistantId, eventData.text || '');
            } catch { /* Ignore malformed intermediate event; final event remains authoritative. */ }
          } else if (eventName === 'final') {
            const data = JSON.parse(dataText) as { answer?: string; execution_id?: string; status?: string; retrieval_used?: boolean; memory_used?: boolean; tools_used?: boolean; provenance?: unknown[]; telemetry?: Message['telemetry']; request_id?: string };
            setMessages((previous) => previous.map((message) => message.id === assistantId ? { ...message, content: data.answer || message.content, timestamp: new Date().toLocaleTimeString(), executionId: data.execution_id, provenance: data.provenance || [], status: data.status || 'completed', retrievalUsed: data.retrieval_used, memoryUsed: data.memory_used, toolsUsed: data.tools_used, telemetry: data.telemetry, requestId: data.request_id || responseRequestId } : message));
          } else if (eventName === 'error') {
            const data = JSON.parse(dataText) as { detail?: string };
            throw new Error(`${data.detail || 'Streaming request failed'} (request ${responseRequestId})`);
          } else if (eventName === 'done') {
            finished = true;
            break;
          }
        }
      }
      setMessages((previous) => previous.map((message) => message.id === assistantId && message.status === 'streaming' ? { ...message, status: 'completed', requestId: responseRequestId } : message));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown network error';
      setMessages((previous) => previous.map((item) => item.id === assistantId ? { ...item, content: `Backend error: ${message}`, status: 'failed', requestId } : item));
    } finally { setLoading(false); }
  };

  const contextLimit = modelContextMax ?? undefined;
  return <section className="chat-shell"><div className="chat-header"><div className="flex items-center gap-3"><div className="brand-mark"><Sparkles className="w-5 h-5" /></div><div><h1 className="text-[15px] font-semibold">SuperAgent</h1><p className="muted text-xs">Reasoning · memory · RAG · tools · multimodal · streaming</p></div></div><div className="flex items-center gap-2"><button type="button" className={`icon-button ${showControls ? 'active' : ''}`} onClick={() => setShowControls((value) => !value)} title="Chat runtime controls" aria-label="Chat runtime controls"><SlidersHorizontal className="w-4 h-4" /></button><label className="toggle-label"><input type="checkbox" checked={developerMode} onChange={(e) => setDeveloperMode(e.target.checked)} /><span>Trace</span></label></div></div>{showControls && <div className="chat-controls"><div className="chat-control-card"><div className="chat-control-title"><Cpu className="w-4 h-4" /><span>Working context</span><strong>{options.contextWindow.toLocaleString()} tokens</strong></div><input aria-label="Working context tokens" type="number" min={256} max={contextLimit} step={256} value={options.contextWindow} onChange={(e) => { const value = Number(e.target.value); if (Number.isFinite(value) && value >= 256) setOptions((current) => ({ ...current, contextWindow: contextLimit ? Math.min(value, contextLimit) : value })); }} /><div className="flex justify-between muted text-[10px]"><span>256 tokens minimum</span><span>{modelContextMax ? `model maximum ${modelContextMax.toLocaleString()}` : 'model maximum reported by provider when available'}</span></div><p className="control-help">Working context is the prompt ceiling. Retrieval is selective and does not automatically fill the entire model context.</p></div><div className="chat-control-card"><div className="chat-control-title"><Sparkles className="w-4 h-4" /><span>Thinking</span><strong>{options.reasoningMode === 'off' ? 'Off' : options.reasoningMode === 'on' ? 'On' : 'Auto'}</strong></div><select aria-label="Thinking mode" value={options.reasoningMode} onChange={(e) => setOptions((current) => ({ ...current, reasoningMode: e.target.value as ChatOptions['reasoningMode'] }))}><option value="auto">Auto — let llama.cpp/model decide</option><option value="on">On — keep server reasoning enabled</option><option value="off">Off — disable reasoning for this request</option></select><p className="control-help">Off is enforced per request. On/Auto respect the llama.cpp server/template policy; thinking budget is controlled by the llama.cpp server.</p></div></div>}<div className="chat-messages">{messages.map((message) => <div key={message.id} className={`message-row ${message.sender === 'user' ? 'user' : ''}`}><div className={`avatar ${message.sender === 'user' ? 'user' : 'assistant'}`}>{message.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}</div><div className={`message-card ${message.sender === 'user' ? 'user-card' : ''}`}><div className="message-meta"><span>{message.sender === 'user' ? 'You' : 'SuperAgent'}</span><span>{message.timestamp}</span></div><p className="whitespace-pre-wrap leading-7 text-sm">{message.content || (message.status === 'streaming' ? 'SuperAgent is reasoning…' : '')}</p>{message.attachments?.length ? <div className="attachment-list mt-3">{message.attachments.map((a) => <span className="attachment-chip" key={a.name}><FileText className="w-3.5 h-3.5" />{a.name}</span>)}</div> : null}{developerMode && message.executionId && <div className="trace-box"><div><Cpu className="w-3.5 h-3.5" /> {message.executionId}</div><div><CheckCircle2 className="w-3.5 h-3.5" /> {message.status} · RAG {message.retrievalUsed ? 'on' : 'off'} · memory {message.memoryUsed ? 'on' : 'off'} · tools {message.toolsUsed ? 'on' : 'off'}</div>{message.telemetry && <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2"><span>Context {message.telemetry.contextWindow?.toLocaleString() ?? '—'}</span><span>Prompt {message.telemetry.promptTokens ?? '—'}</span><span>Output {message.telemetry.outputTokens ?? '—'}</span><span>Total {message.telemetry.totalTokens ?? '—'}</span><span>Generation {message.telemetry.generationTps ? `${message.telemetry.generationTps.toFixed(1)} tok/s` : '—'}</span><span>Memory {message.telemetry.memoryTokens ?? '—'} tok</span><span>Knowledge {message.telemetry.knowledgeTokens ?? '—'} tok</span></div>}</div>}{developerMode && message.requestId && <div className="muted text-[10px] mt-1">request {message.requestId}</div>}</div></div>)}</div><div className={`chat-composer ${dragging ? 'dragging' : ''}`} onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(e) => { e.preventDefault(); setDragging(false); void addFiles(e.dataTransfer.files); }}>{attachments.length > 0 && <div className="attachment-preview">{attachments.map((a, index) => <div className="attachment-chip" key={`${a.name}-${index}`}><span>{a.kind === 'image' ? <Image className="w-3.5 h-3.5" /> : a.kind === 'audio' ? <Mic className="w-3.5 h-3.5" /> : a.kind === 'video' ? <Film className="w-3.5 h-3.5" /> : <FileText className="w-3.5 h-3.5" />}</span>{a.name}<button type="button" onClick={() => setAttachments((prev) => prev.filter((_, i) => i !== index))}><X className="w-3 h-3" /></button></div>)}</div>}{error && <div className="error-banner">{error}</div>}<form onSubmit={handleSendMessage} className="flex items-end gap-2"><input ref={inputRef} type="file" hidden multiple accept="image/*,audio/*,video/*,.txt,.md,.json,.csv,.xml,.py,.js,.ts,.tsx,.css,.html,.pdf,.doc,.docx" onChange={(e) => { if (e.target.files) void addFiles(e.target.files); e.currentTarget.value = ''; }} /><button type="button" className="icon-button composer-button" onClick={() => inputRef.current?.click()} title="Attach files"><Paperclip className="w-4 h-4" /></button><textarea value={inputMessage} onChange={(e) => setInputMessage(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void handleSendMessage(e as unknown as React.FormEvent); } }} rows={1} placeholder="Message SuperAgent…" className="composer-input" /><button type="submit" disabled={loading || (!inputMessage.trim() && !attachments.length)} className="send-button"><Send className="w-4 h-4" /><span className="hidden sm:inline">Send</span></button></form><div className="flex items-center justify-between mt-2 px-1"><span className="muted text-[10px]">Drop files here · responses stream live · thinking mode and context are request controls</span><Sparkles className="w-3.5 h-3.5 muted" /></div></div></section>;
};
