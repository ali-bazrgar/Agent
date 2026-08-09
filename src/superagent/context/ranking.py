from __future__ import annotations

import hashlib
from typing import Sequence

from superagent.context.models import ContextItem, ContextItemKind


def compute_content_hash(content: str) -> str:
    """Utility to compute a SHA256 hex digest for string content."""
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


def _dedup_key(item: ContextItem) -> tuple[str, str]:
    if item.chunk_id:
        return ("chunk", item.chunk_id)
    if item.memory_id:
        return ("memory", item.memory_id)
    return ("content", compute_content_hash(item.content))


def _strength(item: ContextItem) -> tuple[int, float, str]:
    """Lower priority wins; higher score wins; item_id is deterministic tie-breaker."""
    return (item.priority, -item.score, item.item_id)


def deduplicate_context_items(items: Sequence[ContextItem]) -> list[ContextItem]:
    """Deduplicate context while retaining the strongest representative of each item."""
    deduped: dict[tuple[str, str], ContextItem] = {}
    passthrough: list[ContextItem] = []

    for item in items:
        if item.kind in (ContextItemKind.SYSTEM_INSTRUCTION, ContextItemKind.USER_QUERY):
            passthrough.append(item)
            continue

        key = _dedup_key(item)
        previous = deduped.get(key)
        if previous is None or _strength(item) < _strength(previous):
            deduped[key] = item

    return passthrough + list(deduped.values())


def sort_context_items_deterministically(items: Sequence[ContextItem]) -> list[ContextItem]:
    """Sort context by priority, descending score, then stable item id."""
    sorted_items = list(items)
    sorted_items.sort(key=lambda item: (item.priority, -item.score, item.item_id))
    return sorted_items
