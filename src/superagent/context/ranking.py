from __future__ import annotations

import hashlib
from typing import Sequence

from superagent.context.models import ContextItem, ContextItemKind


def compute_content_hash(content: str) -> str:
    """Utility to compute a SHA256 hex digest for string content."""
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


def deduplicate_context_items(items: Sequence[ContextItem]) -> list[ContextItem]:
    """Deduplicates context items while preserving higher priority/score instances."""
    seen_chunk_ids: set[str] = set()
    seen_memory_ids: set[str] = set()
    seen_content_hashes: set[str] = set()

    deduped: list[ContextItem] = []

    for item in items:
        # System instructions & user query are never deduplicated
        if item.kind in (ContextItemKind.SYSTEM_INSTRUCTION, ContextItemKind.USER_QUERY):
            deduped.append(item)
            continue

        if item.chunk_id:
            if item.chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(item.chunk_id)

        if item.memory_id:
            if item.memory_id in seen_memory_ids:
                continue
            seen_memory_ids.add(item.memory_id)

        c_hash = compute_content_hash(item.content)
        if c_hash in seen_content_hashes:
            continue
        seen_content_hashes.add(c_hash)

        deduped.append(item)

    return deduped


def sort_context_items_deterministically(items: Sequence[ContextItem]) -> list[ContextItem]:
    """Sorts context items deterministically by priority (asc), score (desc), item_id (asc)."""
    sorted_items = list(items)
    sorted_items.sort(key=lambda item: (item.priority, -item.score, item.item_id))
    return sorted_items
