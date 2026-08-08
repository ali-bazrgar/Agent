import express from 'express';
import cors from 'cors';
import path from 'path';
import { createServer as createViteServer } from 'vite';
import { 
  MemoryRecord, 
  Document, 
  Flashcard, 
  Review, 
  ExecutionState 
} from './src/types.js';

const startTime = Date.now();
const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

// In-Memory Data Store (seeded with initial foundation records)
let memories: MemoryRecord[] = [
  {
    memory_id: 'mem_01h87a',
    kind: 'working',
    content: 'User requested local-first memory distillation strategy for task execution.',
    confidence: 0.95,
    importance: 0.88,
    relevance: 0.92,
    status: 'active',
    source: {
      source_id: 'src_usr_1',
      source_type: 'user_prompt',
      title: 'User Context Input',
      created_at: new Date().toISOString()
    },
    provenance: 'direct_user_input',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    updated_at: new Date(Date.now() - 3600000).toISOString()
  },
  {
    memory_id: 'mem_02b98c',
    kind: 'semantic',
    content: 'Vector index dimension for text-embedding-3-small is 1536 float32 values.',
    confidence: 0.99,
    importance: 0.75,
    relevance: 0.80,
    status: 'active',
    source: {
      source_id: 'src_doc_emb',
      source_type: 'knowledge_ingestion',
      title: 'Embedding Spec v2',
      created_at: new Date().toISOString()
    },
    provenance: 'extracted_fact',
    created_at: new Date(Date.now() - 7200000).toISOString(),
    updated_at: new Date(Date.now() - 7200000).toISOString()
  },
  {
    memory_id: 'mem_03c10d',
    kind: 'procedural',
    content: 'Always run RAG context retrieval step before calling generative reasoning LLM.',
    confidence: 0.92,
    importance: 0.95,
    relevance: 0.90,
    status: 'active',
    source: {
      source_id: 'src_agent_policy',
      source_type: 'system_rule',
      title: 'Orchestration Guardrails',
      created_at: new Date().toISOString()
    },
    provenance: 'system_policy',
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 86400000).toISOString()
  }
];

let documents: Document[] = [
  {
    document_id: 'doc_101',
    title: 'SuperAgent System Architecture',
    document_type: 'architecture_doc',
    status: 'active',
    version: 1,
    source: {
      source_id: 'src_git_01',
      source_type: 'file_import',
      uri: '/docs/01_SYSTEM_ARCHITECTURE.md',
      title: 'System Architecture Specification'
    },
    chunks: [
      {
        chunk_id: 'chk_101_1',
        document_id: 'doc_101',
        chunk_index: 0,
        content: 'SuperAgent is a modular local-first AI orchestration engine designed with explicit memory layers and deterministic execution guarantees.',
        token_count: 24,
        character_count: 138,
        language: 'en',
        created_at: new Date(Date.now() - 86400000).toISOString()
      },
      {
        chunk_id: 'chk_101_2',
        document_id: 'doc_101',
        chunk_index: 1,
        content: 'Memory models decouple working context, episodic session history, and long-term semantic knowledge into SQLite queryable stores.',
        token_count: 22,
        character_count: 132,
        language: 'en',
        created_at: new Date(Date.now() - 86400000).toISOString()
      }
    ],
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 86400000).toISOString()
  }
];

let flashcards: Flashcard[] = [
  {
    flashcard_id: 'fc_01',
    front: 'What are the 7 memory kinds in SuperAgent?',
    back: 'Working, Session, Episodic, Semantic, Procedural, User, Temporal.',
    difficulty: 0.3,
    source: { source_id: 'src_fc', source_type: 'documentation', title: 'Memory Architecture' },
    created_at: new Date(Date.now() - 172800000).toISOString(),
    updated_at: new Date(Date.now() - 172800000).toISOString()
  },
  {
    flashcard_id: 'fc_02',
    front: 'What is the purpose of the ExecutionState model?',
    back: 'Tracks request lifecycle, status, model calls, tool calls, and retries deterministically.',
    difficulty: 0.5,
    source: { source_id: 'src_fc', source_type: 'documentation', title: 'Execution Engine' },
    created_at: new Date(Date.now() - 172800000).toISOString(),
    updated_at: new Date(Date.now() - 172800000).toISOString()
  }
];

let reviews: Review[] = [
  {
    review_id: 'rev_1001',
    flashcard_id: 'fc_01',
    reviewed_at: new Date(Date.now() - 3600000).toISOString(),
    outcome: 'correct',
    interval_days: 3,
    ease_factor: 2.5
  }
];

let executions: ExecutionState[] = [
  {
    execution_id: 'exec_9001',
    request_id: 'req_init_health_check',
    status: 'completed',
    model_calls: 3,
    tool_calls: 2,
    retries: 0,
    created_at: new Date(Date.now() - 1800000).toISOString(),
    completed_at: new Date(Date.now() - 1795000).toISOString(),
    metadata: { agent: 'orchestration_worker', phase: 1 },
    logs: [
      '[03:30:00] Initialized execution run req_init_health_check',
      '[03:30:01] RAG retriever scanned 2 document chunks',
      '[03:30:03] LLM response synthesized successfully',
      '[03:30:05] Execution state marked as completed'
    ]
  }
];

// --- REST API ENDPOINTS ---

// Health route matching FastAPI /api/v1/health
app.get('/api/v1/health', (req, res) => {
  const settings = {
    status: 'ok',
    environment: process.env.SUPERAGENT_ENV || 'development',
    debug: process.env.SUPERAGENT_DEBUG !== 'false',
    database: process.env.SUPERAGENT_DATABASE_PATH || 'data/superagent.db',
    storage: process.env.SUPERAGENT_STORAGE_PATH || 'data/storage',
    uptime_seconds: Math.floor((Date.now() - startTime) / 1000),
    timestamp: new Date().toISOString()
  };
  res.json(settings);
});

// Memory Records routes
app.get('/api/v1/memories', (req, res) => {
  const { kind, status } = req.query;
  let filtered = [...memories];
  if (kind) {
    filtered = filtered.filter(m => m.kind === kind);
  }
  if (status) {
    filtered = filtered.filter(m => m.status === status);
  }
  res.json(filtered);
});

app.post('/api/v1/memories', (req, res) => {
  const { kind, content, confidence, importance, relevance, source_title, provenance } = req.body;
  if (!content) {
    return res.status(400).json({ error: 'content is required' });
  }

  const newMem: MemoryRecord = {
    memory_id: `mem_${Math.random().toString(36).substring(2, 9)}`,
    kind: kind || 'working',
    content,
    confidence: confidence !== undefined ? Number(confidence) : 0.9,
    importance: importance !== undefined ? Number(importance) : 0.8,
    relevance: relevance !== undefined ? Number(relevance) : 0.85,
    status: 'active',
    source: {
      source_id: `src_${Math.random().toString(36).substring(2, 7)}`,
      source_type: 'user_input',
      title: source_title || 'User Ingestion',
      created_at: new Date().toISOString()
    },
    provenance: provenance || 'user_creation',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };

  memories.unshift(newMem);
  res.status(201).json(newMem);
});

app.delete('/api/v1/memories/:id', (req, res) => {
  const { id } = req.params;
  memories = memories.filter(m => m.memory_id !== id);
  res.json({ success: true, deleted_id: id });
});

// Documents routes
app.get('/api/v1/documents', (req, res) => {
  res.json(documents);
});

app.post('/api/v1/documents', (req, res) => {
  const { title, content, document_type } = req.body;
  if (!title || !content) {
    return res.status(400).json({ error: 'title and content are required' });
  }

  const docId = `doc_${Math.random().toString(36).substring(2, 8)}`;
  
  // Simple chunking simulation (splitting by paragraphs or 200 chars)
  const rawChunks = content.split('\n\n').filter((c: string) => c.trim().length > 0);
  const chunks = rawChunks.map((chunkText: string, idx: number) => ({
    chunk_id: `chk_${docId}_${idx + 1}`,
    document_id: docId,
    chunk_index: idx,
    content: chunkText.trim(),
    token_count: Math.ceil(chunkText.length / 4),
    character_count: chunkText.length,
    language: 'en',
    created_at: new Date().toISOString()
  }));

  const newDoc: Document = {
    document_id: docId,
    title,
    document_type: document_type || 'user_document',
    status: 'active',
    version: 1,
    source: {
      source_id: `src_${docId}`,
      source_type: 'manual_upload',
      title
    },
    chunks,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };

  documents.unshift(newDoc);
  res.status(201).json(newDoc);
});

app.delete('/api/v1/documents/:id', (req, res) => {
  const { id } = req.params;
  documents = documents.filter(d => d.document_id !== id);
  res.json({ success: true, deleted_id: id });
});

// Flashcards routes
app.get('/api/v1/flashcards', (req, res) => {
  res.json(flashcards);
});

app.post('/api/v1/flashcards', (req, res) => {
  const { front, back, difficulty } = req.body;
  if (!front || !back) {
    return res.status(400).json({ error: 'front and back text required' });
  }

  const newFc: Flashcard = {
    flashcard_id: `fc_${Math.random().toString(36).substring(2, 8)}`,
    front,
    back,
    difficulty: difficulty !== undefined ? Number(difficulty) : 0.5,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };

  flashcards.unshift(newFc);
  res.status(201).json(newFc);
});

app.post('/api/v1/flashcards/:id/review', (req, res) => {
  const { id } = req.params;
  const { outcome } = req.body;
  
  const card = flashcards.find(f => f.flashcard_id === id);
  if (!card) {
    return res.status(404).json({ error: 'Flashcard not found' });
  }

  const newReview: Review = {
    review_id: `rev_${Math.random().toString(36).substring(2, 8)}`,
    flashcard_id: id,
    reviewed_at: new Date().toISOString(),
    outcome: outcome || 'correct',
    interval_days: outcome === 'correct' ? 3 : outcome === 'easy' ? 7 : 1,
    ease_factor: 2.5
  };

  reviews.unshift(newReview);
  res.status(201).json({ review: newReview, card });
});

// Executions routes
app.get('/api/v1/executions', (req, res) => {
  res.json(executions);
});

app.post('/api/v1/executions', (req, res) => {
  const { request_id, task_description } = req.body;
  
  const execId = `exec_${Math.random().toString(36).substring(2, 8)}`;
  const now = new Date().toISOString();
  
  const newExec: ExecutionState = {
    execution_id: execId,
    request_id: request_id || `req_${Date.now()}`,
    status: 'running',
    model_calls: 1,
    tool_calls: 2,
    retries: 0,
    created_at: now,
    metadata: { task: task_description || 'SuperAgent orchestration routine' },
    logs: [
      `[${new Date().toLocaleTimeString()}] Task received: ${task_description || 'Standard orchestration'}`,
      `[${new Date().toLocaleTimeString()}] Querying memory store for procedural guardrails`,
      `[${new Date().toLocaleTimeString()}] Executing tool calls & context synthesis`
    ]
  };

  executions.unshift(newExec);

  // Simulate execution completion
  setTimeout(() => {
    const target = executions.find(e => e.execution_id === execId);
    if (target) {
      target.status = 'completed';
      target.completed_at = new Date().toISOString();
      target.model_calls += 1;
      target.logs?.push(`[${new Date().toLocaleTimeString()}] Task finished successfully with status 200`);
    }
  }, 3000);

  res.status(201).json(newExec);
});

// --- SERVER INTEGRATION & MIDDLEWARE ---

async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[SuperAgent] Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
