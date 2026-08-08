export type MemoryKind = 'working' | 'session' | 'episodic' | 'semantic' | 'procedural' | 'user' | 'temporal';
export type MemoryStatus = 'draft' | 'active' | 'superseded' | 'expired' | 'deleted';
export interface Source { source_id: string; source_type: string; uri?: string; locator?: string; title?: string; content_hash?: string; metadata?: Record<string, any>; created_at?: string; }
export interface MemoryRecord { memory_id: string; kind: MemoryKind; content: string; confidence: number; importance: number; relevance: number; status: MemoryStatus; source: Source; provenance?: string; created_at: string; updated_at: string; }
export interface DocumentChunk { chunk_id: string; document_id: string; content: string; chunk_index: number; token_count?: number; character_count?: number; language?: string; created_at: string; }
export interface Document { document_id: string; title: string; source: Source; document_type: string; status: string; version: number; chunks: DocumentChunk[]; created_at: string; updated_at: string; }
export interface Flashcard { flashcard_id: string; front: string; back: string; difficulty: number; source?: Source; created_at: string; updated_at: string; }
export interface LearningState { flashcard_id: string; state: 'new' | 'learning' | 'review' | 'relearning'; due_date: string; interval_days: number; repetition: number; stability: number; difficulty: number; last_reviewed_at?: string; }
export interface DueReview { flashcard: Flashcard; learning_state: LearningState; }
export interface Review { review_id: string; flashcard_id: string; reviewed_at: string; outcome: 'again' | 'hard' | 'good' | 'easy' | 'correct' | 'incorrect'; interval_days: number; ease_factor: number; }
export interface ExecutionState { execution_id: string; request_id?: string; status: 'initialized' | 'running' | 'completed' | 'failed' | 'retrying'; model_calls: number; tool_calls: number; retries: number; created_at: string; completed_at?: string; metadata?: Record<string, any>; logs?: string[]; }
export interface SystemHealth { status: string; environment: string; debug: boolean; database: string; database_status?: string; database_error?: string | null; storage: string; storage_status?: string; uptime_seconds?: number; timestamp?: string; providers?: Record<string, { status: string; message?: string | null; details?: Record<string, unknown> }>; }
