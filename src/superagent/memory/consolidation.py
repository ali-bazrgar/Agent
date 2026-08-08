from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from superagent.memory.models import ConsolidationResult, MemoryAction, MemoryCandidate
from superagent.memory.ports import MemoryConsolidatorPort
from superagent.models.domain import MemoryKind, MemoryRecord, MemoryStatus, Source


class MemoryConsolidator(MemoryConsolidatorPort):
    """Consolidates memory candidates against existing stored memories."""

    def consolidate(
        self,
        candidate: MemoryCandidate,
        existing_memories: Sequence[MemoryRecord],
    ) -> ConsolidationResult:
        cand_clean = candidate.content.strip().lower()

        # Check existing active memories
        for existing in existing_memories:
            if existing.status != MemoryStatus.ACTIVE:
                continue

            ex_clean = existing.content.strip().lower()

            # Exact match
            if cand_clean == ex_clean:
                # Boost confidence slightly up to 1.0
                new_confidence = min(1.0, round(existing.confidence + 0.1, 2))
                updated_memory = existing.model_copy(
                    update={
                        "confidence": new_confidence,
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
                return ConsolidationResult(
                    action=MemoryAction.MERGED,
                    memory=updated_memory,
                    reasoning=f"Exact content match with memory {existing.memory_id}; confidence boosted to {new_confidence}.",
                )

            # Prefix/Subject match for USER preference updates (e.g., "my name is Alice" vs "my name is Bob")
            if (
                candidate.kind == MemoryKind.USER
                and existing.kind == MemoryKind.USER
                and ("my name is" in cand_clean and "my name is" in ex_clean)
            ):
                # Mark existing as superseded, create new memory
                superseded_existing = existing.model_copy(
                    update={
                        "status": MemoryStatus.SUPERSEDED,
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
                new_memory = MemoryRecord(
                    memory_id=f"mem-{uuid.uuid4().hex[:12]}",
                    kind=candidate.kind,
                    content=candidate.content,
                    confidence=candidate.confidence,
                    importance=candidate.importance,
                    relevance=candidate.relevance,
                    status=MemoryStatus.ACTIVE,
                    source=Source(
                        source_id=f"src-{uuid.uuid4().hex[:8]}",
                        source_type="execution",
                        uri=candidate.source_execution_id,
                    ),
                    provenance=f"supersedes:{existing.memory_id}",
                    metadata=dict(candidate.metadata),
                )
                return ConsolidationResult(
                    action=MemoryAction.SUPERSEDED,
                    memory=new_memory,
                    reasoning=f"New user record supersedes old memory {existing.memory_id}.",
                )

        # Default: Create new memory record
        new_memory = MemoryRecord(
            memory_id=f"mem-{uuid.uuid4().hex[:12]}",
            kind=candidate.kind,
            content=candidate.content,
            confidence=candidate.confidence,
            importance=candidate.importance,
            relevance=candidate.relevance,
            status=MemoryStatus.ACTIVE,
            source=Source(
                source_id=f"src-{uuid.uuid4().hex[:8]}",
                source_type="execution",
                uri=candidate.source_execution_id,
            ),
            provenance="extracted_candidate",
            metadata=dict(candidate.metadata),
        )
        return ConsolidationResult(
            action=MemoryAction.CREATED,
            memory=new_memory,
            reasoning="Created new memory record.",
        )
