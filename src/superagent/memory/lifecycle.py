from __future__ import annotations

from typing import Sequence

from superagent.memory.consolidation import MemoryConsolidator
from superagent.memory.extraction import MemoryExtractor
from superagent.memory.models import MemoryAction
from superagent.memory.ports import MemoryConsolidatorPort, MemoryExtractorPort, MemoryLifecyclePort
from superagent.models.domain import MemoryRecord
from superagent.repositories.ports import MemoryRepository


class MemoryLifecycle(MemoryLifecyclePort):
    """Coordinates memory extraction, consolidation, and persistence."""

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
    ) -> list[MemoryRecord]:
        candidates = self.extractor.extract_candidates(
            user_message=user_message,
            assistant_message=assistant_message,
            execution_id=execution_id,
        )

        if not candidates:
            return []

        existing_memories = self.repository.list_memories()
        processed_memories: list[MemoryRecord] = []

        for candidate in candidates:
            result = self.consolidator.consolidate(
                candidate=candidate,
                existing_memories=existing_memories,
            )

            if result.action == MemoryAction.CREATED and result.memory:
                created = self.repository.create_memory(result.memory)
                processed_memories.append(created)
            elif result.action in (MemoryAction.MERGED, MemoryAction.SUPERSEDED) and result.memory:
                # Save or update memory
                created = self.repository.create_memory(result.memory)
                processed_memories.append(created)

        return processed_memories
