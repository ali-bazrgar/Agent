from __future__ import annotations

import uuid
from typing import Callable, Sequence

from superagent.context.budget import ContextBudgetManager, TokenEstimator
from superagent.context.models import (
    ChatMessage,
    ContextBuildResult,
    ContextItem,
    ContextItemKind,
    ContextRequest,
    ContextSelection,
)
from superagent.context.ports import ContextEnginePort
from superagent.context.prompt import PromptBuilder
from superagent.context.ranking import deduplicate_context_items, sort_context_items_deterministically
from superagent.core.errors import ValidationError
from superagent.models.domain import MemoryRecord


class ContextEngine(ContextEnginePort):
    """Core Context Engine implementation for deterministic context assembly."""

    def __init__(self, tokenizer_fn: Callable[[str], int] | None = None) -> None:
        self.estimator = TokenEstimator(tokenizer_fn=tokenizer_fn)

    def build_context(self, request: ContextRequest) -> ContextBuildResult:
        if not request.query or not request.query.strip():
            raise ValidationError("Context request query cannot be empty or blank")

        budget_manager = ContextBudgetManager(request.budget)
        all_items: list[ContextItem] = []

        # 1. User Query (Mandatory, highest priority)
        query_item = ContextItem(
            item_id=f"query-{uuid.uuid4().hex[:8]}",
            kind=ContextItemKind.USER_QUERY,
            content=request.query,
            priority=20,
            score=1.0,
            estimated_tokens=self.estimator.estimate_text(request.query),
        )

        # Ensure user query fits in available prompt tokens
        if query_item.estimated_tokens > request.budget.available_prompt_tokens:
            raise ValidationError(
                f"User query token count ({query_item.estimated_tokens}) exceeds available "
                f"prompt budget ({request.budget.available_prompt_tokens})"
            )

        # 2. System Instructions
        if request.system_instructions:
            for idx, sys_text in enumerate(request.system_instructions):
                if sys_text and sys_text.strip():
                    item = ContextItem(
                        item_id=f"sys-{idx}-{uuid.uuid4().hex[:6]}",
                        kind=ContextItemKind.SYSTEM_INSTRUCTION,
                        content=sys_text.strip(),
                        priority=10,
                        score=1.0,
                        estimated_tokens=self.estimator.estimate_text(sys_text),
                    )
                    all_items.append(item)

        # 3. Conversation History
        num_conv = len(request.conversation_history)
        for idx, msg in enumerate(request.conversation_history):
            if not msg.content:
                continue
            # Mark recent 4 messages with priority 30, older with priority 60
            is_recent = (num_conv - idx) <= 4
            prio = 30 if is_recent else 60
            recency_score = float(idx + 1) / float(max(1, num_conv))

            item = ContextItem(
                item_id=f"conv-{idx}-{uuid.uuid4().hex[:6]}",
                kind=ContextItemKind.CONVERSATION_MESSAGE,
                content=msg.content,
                priority=prio,
                score=recency_score,
                estimated_tokens=self.estimator.estimate_message(msg),
                metadata={"role": msg.role, "history_index": idx, **msg.metadata},
            )
            all_items.append(item)

        # 4. Retrieved Knowledge Candidates
        if request.retrieval_result and request.retrieval_result.candidates:
            for idx, cand in enumerate(request.retrieval_result.candidates):
                score = cand.reranker_score or cand.fused_score or cand.retrieval_score or 0.0
                item = ContextItem(
                    item_id=f"k-{cand.chunk_id}",
                    kind=ContextItemKind.KNOWLEDGE_CHUNK,
                    content=cand.content,
                    priority=40,
                    score=score,
                    estimated_tokens=self.estimator.estimate_text(cand.content),
                    source_id=cand.source_id,
                    document_id=cand.document_id,
                    version_id=cand.version_id,
                    chunk_id=cand.chunk_id,
                    retrieval_method=cand.retrieval_method,
                    metadata=dict(cand.metadata),
                    provenance=dict(cand.provenance),
                )
                all_items.append(item)

        # 5. Memories
        if request.memories:
            for idx, mem in enumerate(request.memories):
                score = (mem.confidence * mem.importance * mem.relevance) if (
                    mem.confidence and mem.importance and mem.relevance
                ) else mem.confidence or 0.5
                item = ContextItem(
                    item_id=f"mem-{mem.memory_id}",
                    kind=ContextItemKind.MEMORY,
                    content=mem.content,
                    priority=50,
                    score=score,
                    estimated_tokens=self.estimator.estimate_text(mem.content),
                    memory_id=mem.memory_id,
                    metadata={"kind": mem.kind.value, "status": mem.status.value},
                    provenance={"memory_id": mem.memory_id, "kind": mem.kind.value},
                )
                all_items.append(item)

        # Step A: Deduplicate items
        deduped_items = deduplicate_context_items(all_items)

        # Step B: Sort deterministically by priority (asc), score (desc), item_id (asc)
        ranked_items = sort_context_items_deterministically(deduped_items)

        # Step C: Allocate budget (User query mandatory)
        budget_manager.consume(query_item)
        selected_items: list[ContextItem] = [query_item]
        dropped_items: list[ContextItem] = []

        for item in ranked_items:
            if budget_manager.can_fit(item):
                budget_manager.consume(item)
                selected_items.append(item)
            else:
                dropped_items.append(item)

        # Step D: Preserve original chronological order for selected conversation messages
        selected_conv = [
            it for it in selected_items if it.kind == ContextItemKind.CONVERSATION_MESSAGE
        ]
        selected_conv.sort(key=lambda it: it.metadata.get("history_index", 0))

        # Re-arrange selected items into coherent prompt build order
        final_selected_order: list[ContextItem] = []
        final_selected_order.extend(
            [it for it in selected_items if it.kind == ContextItemKind.SYSTEM_INSTRUCTION]
        )
        final_selected_order.extend(
            [it for it in selected_items if it.kind == ContextItemKind.KNOWLEDGE_CHUNK]
        )
        final_selected_order.extend(
            [it for it in selected_items if it.kind == ContextItemKind.MEMORY]
        )
        final_selected_order.extend(selected_conv)
        final_selected_order.append(query_item)

        # Step E: Construct Chat Messages
        prompt_messages = PromptBuilder.build_prompt_messages(final_selected_order)

        total_selected_tokens = sum(it.estimated_tokens for it in final_selected_order)
        total_prompt_tokens = sum(self.estimator.estimate_message(msg) for msg in prompt_messages)

        # Step F: Assemble Provenance Records
        provenance_records: list[dict[str, Any]] = []
        for it in final_selected_order:
            if it.kind in (ContextItemKind.KNOWLEDGE_CHUNK, ContextItemKind.MEMORY):
                rec = {
                    "item_id": it.item_id,
                    "kind": it.kind.value,
                    "score": round(it.score, 4),
                    "source_id": it.source_id,
                    "document_id": it.document_id,
                    "version_id": it.version_id,
                    "chunk_id": it.chunk_id,
                    "memory_id": it.memory_id,
                    "retrieval_method": it.retrieval_method,
                    "provenance": it.provenance,
                }
                provenance_records.append(rec)

        selection = ContextSelection(
            selected_items=final_selected_order,
            dropped_items=dropped_items,
            allocated_tokens={
                k.value: v for k, v in budget_manager.allocated_by_kind.items() if v > 0
            },
            total_selected_tokens=total_selected_tokens,
        )

        return ContextBuildResult(
            prompt_messages=prompt_messages,
            selection=selection,
            total_prompt_tokens=total_prompt_tokens,
            reserved_output_tokens=request.budget.reserved_output_tokens,
            total_context_window=request.budget.total_context_window,
            provenance=provenance_records,
            metadata=dict(request.metadata),
        )
