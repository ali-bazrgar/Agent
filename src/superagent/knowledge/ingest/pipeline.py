from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from superagent.core.errors import ValidationError
from superagent.database.engine import DatabaseEngine
from superagent.knowledge.ingest.chunker import TextChunker
from superagent.models.domain import (
    Document,
    DocumentChunk,
    DocumentVersion,
    EmbeddingRecord,
    KnowledgeItem,
    Source,
)
from superagent.providers.contracts import EmbeddingProvider, EmbeddingRequest
from superagent.repositories.ports import (
    ChunkRepository,
    DocumentRepository,
    DocumentVersionRepository,
    EmbeddingRepository,
    KnowledgeRepository,
    SourceRepository,
    TagRepository,
)


@dataclass(slots=True)
class IngestionRequest:
    title: str
    content: str
    source_type: str = "file"
    uri: str | None = None
    locator: str | None = None
    content_type: str | None = "text/plain"
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] | None = None


@dataclass(slots=True)
class IngestionResult:
    source: Source
    document: Document
    version: DocumentVersion
    chunks: list[DocumentChunk]
    embeddings: list[EmbeddingRecord]
    is_duplicate: bool = False


class DocumentIngestionPipeline:
    def __init__(
        self,
        source_repository: SourceRepository,
        document_repository: DocumentRepository,
        document_version_repository: DocumentVersionRepository,
        chunk_repository: ChunkRepository,
        embedding_repository: EmbeddingRepository,
        knowledge_repository: KnowledgeRepository,
        tag_repository: TagRepository,
        embedding_provider: EmbeddingProvider,
        chunker: TextChunker | None = None,
        database_engine: DatabaseEngine | None = None,
    ) -> None:
        self.source_repository = source_repository
        self.document_repository = document_repository
        self.document_version_repository = document_version_repository
        self.chunk_repository = chunk_repository
        self.embedding_repository = embedding_repository
        self.knowledge_repository = knowledge_repository
        self.tag_repository = tag_repository
        self.embedding_provider = embedding_provider
        self.chunker = chunker or TextChunker()
        self.database_engine = database_engine

    def ingest(self, request: IngestionRequest) -> IngestionResult:
        if not request.title or not request.title.strip():
            raise ValidationError("Ingestion request title must not be blank")
        if not request.content or not request.content.strip():
            raise ValidationError("Ingestion request content must not be blank")

        normalized_content = self.chunker.normalize_text(request.content)
        content_hash = hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()

        existing_source = self.source_repository.get_source_by_content_hash(content_hash)
        if existing_source is not None:
            documents = self.document_repository.list_documents()
            for doc in documents:
                if doc.content_hash == content_hash or (doc.source and doc.source.source_id == existing_source.source_id):
                    versions = self.document_version_repository.list_versions_for_document(doc.document_id)
                    for ver in versions:
                        if ver.content_hash == content_hash:
                            chunks = list(self.chunk_repository.list_chunks_for_document(doc.document_id))
                            embeddings: list[EmbeddingRecord] = []
                            for chk in chunks:
                                embeddings.extend(self.embedding_repository.list_embeddings_for_chunk(chk.chunk_id))
                            return IngestionResult(
                                source=existing_source,
                                document=doc,
                                version=ver,
                                chunks=chunks,
                                embeddings=embeddings,
                                is_duplicate=True,
                            )

        chunk_results = self.chunker.chunk_text(
            normalized_content,
            base_metadata=request.metadata,
        )

        chunk_texts = [c.content for c in chunk_results]

        embedding_response = self.embedding_provider.embed(EmbeddingRequest(texts=chunk_texts))

        source = existing_source
        if source is None:
            source = Source(
                source_id=f"src-{uuid.uuid4().hex[:12]}",
                source_type=request.source_type,
                uri=request.uri,
                locator=request.locator,
                title=request.title,
                content_hash=content_hash,
                metadata=request.metadata,
                provenance=request.provenance,
            )
            self.source_repository.create_source(source)

        document = Document(
            document_id=f"doc-{uuid.uuid4().hex[:12]}",
            title=request.title,
            source=source,
            source_id=source.source_id,
            document_type="document",
            content_type=request.content_type,
            content_hash=content_hash,
            status="active",
            version=1,
            metadata=request.metadata,
        )
        self.document_repository.create_document(document)

        version = DocumentVersion(
            version_id=f"ver-{uuid.uuid4().hex[:12]}",
            document_id=document.document_id,
            title=request.title,
            content=normalized_content,
            content_hash=content_hash,
            content_type=request.content_type,
            status="active",
            metadata=request.metadata,
        )
        self.document_version_repository.create_version(version)

        domain_chunks: list[DocumentChunk] = []
        for res in chunk_results:
            chk_hash = hashlib.sha256(res.content.encode("utf-8")).hexdigest()
            chunk = DocumentChunk(
                chunk_id=f"chk-{uuid.uuid4().hex[:12]}",
                document_id=document.document_id,
                version_id=version.version_id,
                content=res.content,
                content_hash=chk_hash,
                chunk_index=res.chunk_index,
                token_count=res.token_count,
                character_count=res.character_count,
                metadata=res.metadata,
            )
            saved_chunk = self.chunk_repository.create_chunk(chunk)
            domain_chunks.append(saved_chunk)

        domain_embeddings: list[EmbeddingRecord] = []
        model_id = embedding_response.provider_name or "embedding"
        for chunk, vec in zip(domain_chunks, embedding_response.embeddings):
            record = EmbeddingRecord(
                embedding_id=f"emb-{uuid.uuid4().hex[:12]}",
                chunk_id=chunk.chunk_id,
                document_id=document.document_id,
                version_id=version.version_id,
                model_id=model_id,
                dimension=len(vec),
                vector_json=json.dumps(vec),
                content_hash=chunk.content_hash,
                metadata={"chunk_index": chunk.chunk_index},
            )
            saved_emb = self.embedding_repository.create_embedding(record)
            domain_embeddings.append(saved_emb)

        knowledge_item = KnowledgeItem(
            knowledge_id=f"kno-{uuid.uuid4().hex[:12]}",
            kind="document",
            title=request.title,
            content=normalized_content,
            content_hash=content_hash,
            source_id=source.source_id,
            document_id=document.document_id,
            version_id=version.version_id,
            metadata=request.metadata,
            provenance=request.provenance,
        )
        self.knowledge_repository.create_knowledge(knowledge_item)

        return IngestionResult(
            source=source,
            document=document,
            version=version,
            chunks=domain_chunks,
            embeddings=domain_embeddings,
            is_duplicate=False,
        )
