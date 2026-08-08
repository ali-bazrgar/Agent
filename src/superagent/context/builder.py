from __future__ import annotations

import uuid
from typing import Any, Callable, Sequence

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


class ContextEngine(ContextEnginePort):
    """Core Context Engine implementation for deterministic context assembly."""

    def __init__(self, tokenizer_fn: Callable[[str], int] | None = None) -> None:
        self.estimator = TokenEstimator(tokenizer_fn=tokenizer_fn)

    def build_context(self, request: ContextRequest) -> ContextBuildResult:
        if not request.query or not request.query.strip():
            raise ValidationError("Context request query cannot be empty or blank")

        budget_manager = ContextBudgetManager(request.budget)
        all_items: list[ContextItem] = []

        query_item = ContextItem(
            item_id=f"query-{uuid.uuid4().hex[:8]}",
            kind=ContextItemKind.USER_QUERY,
            content=request.query.strip(),
            priority=20,
            score=1.0,
            estimated_tokens=self.estimator.estimate_text(request.query),
        )

        if query_item.estimated_tokens > request.budget.available_prompt_tokens:
            raise ValidationError(
                f"User query token count ({query_item.estimated_tokens}) exceeds available "
                f"prompt budget ({request.budget.available_prompt_tokens})"
            )

        if request.system_instructions:
            for idx, sys_text in enumerate(request.system_instructions):
                if sys_text and sys_text.strip():
                    all_items.append(
                        ContextItem(
                            item_id=f"sys-{idx}-{uuid.uuid4().hex[:6]}",
                            kind=ContextItemKind.SYSTEM_INSTRUCTION,
                            content=sys_text.strip(),
                            priority=10,
                            score=1.0,
                            estimated_tokens=self.estimator.estimate_text(sys_text),
                        )
                    )

        num_conv = len(request.conversation_history)
        for idx, msg in enumerate(request.conversation_history):
            if not msg.content:
                continue
            is_recent = (num_conv - idx) <= 4
            priority = 30 if is_recent else 60
            recency_score = float(idx + 1) / float(max(1, num_conv))
            all_items.append(
                ContextItem(
                    item_id=f"conv-{idx}-{uuid.uuid4().hex[:6]}",
                    kind=ContextItemKind.CONVERSATION_MESSAGE,
                    content=msg.content,
                    priority=priority,
                    score=recency_score,
                    estimated_tokens=self.estimator.estimate_message(msg),
                    metadata={"role": msg.role, "history_index": idx, **msg.metadata},
                )
            )

        if request.retrieval_result and request.retrieval_result.candidates:
            for cand in request.retrieval_result.candidates:
                score = cand.reranker_score or cand.fused_score or cand.retrieval_score or 0.0
                all_items.append(
                    ContextItem(
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
                )

        if request.memories:
            for mem in request.memories:
                score = (
                    mem.confidence * mem.importance * mem.relevance
                    if mem.confidence and mem.importance and mem.relevance
                    else mem.confidence or 0.5
                )
                all_items.append(
                    ContextItem(
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
                )

        ranked_items = sort_context_items_deterministically(deduplicate_context_items(all_items))

        budget_manager.consume(query_item)
        selected_items: list[ContextItem] = [query_item]
        dropped_items: list[ContextItem] = []

        for item in ranked_items:
            if budget_manager.can_fit(item):
                budget_manager.consume(item)
                selected_items.append(item)
            else:
                dropped_items.append(item)

        selected_conv = [
            item for item in selected_items if item.kind == ContextItemKind.CONVERSATION_MESSAGE
        ]
        selected_conv.sort(key=lambda item: item.metadata.get("history_index", 0))

        final_selected_order: list[ContextItem] = []
        final_selected_order.extend(
            item for item in selected_items if item.kind == ContextItemKind.SYSTEM_INSTRUCTION
        )
        final_selected_order.extend(
            item for item in selected_items if item.kind == ContextItemKind.KNOWLEDGE_CHUNK
        )
        final_selected_order.extend(
            item for item in selected_items if item.kind == ContextItemKind.MEMORY
        )
        final_selected_order.extend(selected_conv)
        final_selected_order.append(query_item)

        prompt_messages = PromptBuilder.build_prompt_messages(final_selected_order)
        total_selected_tokens = sum(item.estimated_tokens for item in final_selected_order)
        total_prompt_tokens = sum(
            self.estimator.estimate_message(message) for message in prompt_messages
        )

        provenance_records: list[dict[str, Any]] = []
        for item in final_selected_order:
            if item.kind in (ContextItemKind.KNOWLEDGE_CHUNK, ContextItemKind.MEMORY):
                provenance_records.append(
                    {
                        "item_id": item.item_id,
                        "kind": item.kind.value,
                        "score": round(item.score, 4),
                        "source_id": item.source_id,
                        "document_id": item.document_id,
                        "version_id": item.version_id,
                        "chunk_id": item.chunk_id,
                        "memory_id": item.memory_id,
                        "retrieval_method": item.retrieval_method,
                        "provenance": item.provenance,
                    }
                )

        selection = ContextSelection(
            selected_items=final_selected_order,
            dropped_items=dropped_items,
            allocated_tokens={
                kind.value: tokens
                for kind, tokens in budget_manager.allocated_by_kind.items()
                if tokens > 0
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
