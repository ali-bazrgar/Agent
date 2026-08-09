from __future__ import annotations

import re

from superagent.memory.consolidation import MemoryConsolidator
from superagent.memory.extraction import MemoryExtractor
from superagent.memory.models import MemoryAction
from superagent.memory.ports import MemoryConsolidatorPort, MemoryExtractorPort, MemoryLifecyclePort
from superagent.models.domain import MemoryRecord, MemoryScope
from superagent.repositories.ports import MemoryRepository


class MemoryLifecycle(MemoryLifecyclePort):
    """Coordinates optional legacy extraction, consolidation, and persistence.

    LLM-driven tool execution is the authoritative memory-write path. The
    heuristic extractor is retained only for explicitly enabled legacy/fallback
    flows and must never silently duplicate an LLM-selected memory.write call.
    """

    def __init__(
        self,
        memory_repository: MemoryRepository,
        extractor: MemoryExtractorPort | None = None,
        consolidator: MemoryConsolidatorPort | None = None,
    ) -> None:
        self.repository = memory_repository
        self.extractor = extractor or MemoryExtractor()
        self.consolidator = consolidator or MemoryConsolidator()

    def process_interaction(
        self,
        user_message: str,
        assistant_message: str,
        execution_id: str | None = None,
        *,
        scope: MemoryScope | None = None,
        enable_heuristic_extraction: bool = False,
    ) -> list[MemoryRecord]:
        """Persist explicitly enabled legacy candidates inside one trusted scope."""
        if not enable_heuristic_extraction:
            return []
        if scope is None:
            raise ValueError("A trusted MemoryScope is required for lifecycle persistence")

        candidates = self.extractor.extract_candidates(
            user_message=user_message,
            assistant_message=assistant_message,
            execution_id=execution_id,
        )
        if not candidates:
            return []

        existing_memories = list(self.repository.list_memories(scope))
        processed_memories: list[MemoryRecord] = []

        for candidate in candidates:
            result = self.consolidator.consolidate(
                candidate=candidate,
                existing_memories=existing_memories,
            )
            if result.memory is None:
                continue

            scoped_memory = result.memory.model_copy(update={"scope": scope})

            if result.action == MemoryAction.CREATED:
                persisted = self.repository.create_memory(scoped_memory)
                processed_memories.append(persisted)
                existing_memories.append(persisted)

            elif result.action == MemoryAction.MERGED:
                persisted = self.repository.update_memory(scoped_memory)
                processed_memories.append(persisted)
                existing_memories = [
                    persisted if memory.memory_id == persisted.memory_id else memory
                    for memory in existing_memories
                ]

            elif result.action == MemoryAction.SUPERSEDED:
                old_id = self._superseded_memory_id(scoped_memory.provenance)
                if old_id:
                    old_memory = self.repository.get_memory(old_id, scope)
                    if old_memory is not None:
                        self.repository.update_status(old_id, "superseded")
                        existing_memories = [
                            memory for memory in existing_memories if memory.memory_id != old_id
                        ]
                persisted = self.repository.create_memory(scoped_memory)
                processed_memories.append(persisted)
                existing_memories.append(persisted)

        return processed_memories

    @staticmethod
    def _superseded_memory_id(provenance: str | None) -> str | None:
        if not provenance:
            return None
        match = re.fullmatch(r"supersedes:(.+)", provenance.strip())
        return match.group(1) if match else None
