from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from superagent.models.domain import (
    Document,
    DocumentChunk,
    DocumentVersion,
    EmbeddingRecord,
    ExecutionState,
    Flashcard,
    KnowledgeItem,
    MemoryRecord,
    Review,
    Source,
    Tag,
)


class SourceRepository(ABC):
    """Persistence contract for source records."""
    @abstractmethod
    def create_source(self, source: Source) -> Source: ...
    @abstractmethod
    def get_source(self, source_id: str) -> Source | None: ...
    @abstractmethod
    def get_source_by_content_hash(self, content_hash: str) -> Source | None: ...
    @abstractmethod
    def list_sources(self) -> Sequence[Source]: ...


class DocumentRepository(ABC):
    """Persistence contract for documents."""
    @abstractmethod
    def create_document(self, document: Document) -> Document: ...
    @abstractmethod
    def get_document(self, document_id: str) -> Document | None: ...
    @abstractmethod
    def list_documents(self) -> Sequence[Document]: ...
    @abstractmethod
    def delete_document(self, document_id: str) -> bool: ...


class DocumentVersionRepository(ABC):
    """Persistence contract for document versions."""
    @abstractmethod
    def create_version(self, version: DocumentVersion) -> DocumentVersion: ...
    @abstractmethod
    def get_version(self, version_id: str) -> DocumentVersion | None: ...
    @abstractmethod
    def list_versions_for_document(self, document_id: str) -> Sequence[DocumentVersion]: ...


class ChunkRepository(ABC):
    """Persistence contract for document chunks."""
    @abstractmethod
    def create_chunk(self, chunk: DocumentChunk) -> DocumentChunk: ...
    @abstractmethod
    def list_chunks_for_document(self, document_id: str) -> Sequence[DocumentChunk]: ...
    @abstractmethod
    def get_chunk(self, chunk_id: str) -> DocumentChunk | None: ...


class EmbeddingRepository(ABC):
    """Persistence contract for embedding records."""
    @abstractmethod
    def create_embedding(self, embedding: EmbeddingRecord) -> EmbeddingRecord: ...
    @abstractmethod
    def get_embedding(self, embedding_id: str) -> EmbeddingRecord | None: ...
    @abstractmethod
    def list_embeddings_for_chunk(self, chunk_id: str) -> Sequence[EmbeddingRecord]: ...


class KnowledgeRepository(ABC):
    """Persistence contract for knowledge items."""
    @abstractmethod
    def create_knowledge(self, item: KnowledgeItem) -> KnowledgeItem: ...
    @abstractmethod
    def get_knowledge(self, knowledge_id: str) -> KnowledgeItem | None: ...
    @abstractmethod
    def list_knowledge(self) -> Sequence[KnowledgeItem]: ...


class TagRepository(ABC):
    """Persistence contract for generic tags."""
    @abstractmethod
    def add_tag(self, tag: Tag) -> Tag: ...
    @abstractmethod
    def list_tags(self, resource_type: str, resource_id: str) -> Sequence[Tag]: ...


class MemoryRepository(ABC):
    """Persistence contract for memory records."""
    @abstractmethod
    def create_memory(self, memory: MemoryRecord) -> MemoryRecord: ...
    @abstractmethod
    def get_memory(self, memory_id: str) -> MemoryRecord | None: ...
    @abstractmethod
    def list_memories(self) -> Sequence[MemoryRecord]: ...
    @abstractmethod
    def update_memory(self, memory: MemoryRecord) -> MemoryRecord: ...
    @abstractmethod
    def update_status(self, memory_id: str, status: str) -> None: ...


class ExecutionRepository(ABC):
    """Persistence contract for execution state."""
    @abstractmethod
    def create_execution(self, execution: ExecutionState) -> ExecutionState: ...
    @abstractmethod
    def update_execution(self, execution: ExecutionState) -> ExecutionState: ...
    @abstractmethod
    def get_execution(self, execution_id: str) -> ExecutionState | None: ...
    @abstractmethod
    def list_executions(self) -> Sequence[ExecutionState]: ...


class FlashcardRepository(ABC):
    """Persistence contract for flashcards."""
    @abstractmethod
    def create_flashcard(self, flashcard: Flashcard) -> Flashcard: ...
    @abstractmethod
    def get_flashcard(self, flashcard_id: str) -> Flashcard | None: ...
    @abstractmethod
    def list_flashcards(self) -> Sequence[Flashcard]: ...


class ReviewRepository(ABC):
    """Persistence contract for reviews."""
    @abstractmethod
    def create_review(self, review: Review) -> Review: ...
    @abstractmethod
    def list_reviews_for_flashcard(self, flashcard_id: str) -> Sequence[Review]: ...
