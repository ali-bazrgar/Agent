from __future__ import annotations

import uuid
from typing import Any, Callable

from superagent.context.budget import ContextBudgetManager, TokenEstimator
from superagent.context.models import ContextBuildResult, ContextItem, ContextItemKind, ContextRequest, ContextSelection
from superagent.context.ports import ContextEnginePort
from superagent.context.prompt import PromptBuilder
from superagent.context.ranking import deduplicate_context_items, sort_context_items_deterministically
from superagent.core.errors import ValidationError


class ContextEngine(ContextEnginePort):
    """Deterministic context assembly with strict prompt-budget enforcement.

    The runtime context window is a fixed ceiling selected by the user/model
    profile.  ``_context_allocation`` is a per-request policy that controls which
    external memory sources may consume that ceiling.  This keeps durable
    memory and knowledge outside the short-term chat transcript while allowing
    the model to work with a small working window as if it had a much larger
    searchable memory.
    """

    def __init__(self, tokenizer_fn: Callable[[str], int] | None = None) -> None:
        self.estimator = TokenEstimator(tokenizer_fn=tokenizer_fn)

    @staticmethod
    def _allocation(metadata: dict[str, Any]) -> dict[str, Any]:
        raw = metadata.get("_context_allocation")
        return dict(raw) if isinstance(raw, dict) else {}

    @staticmethod
    def _positive_limit(value: Any) -> int | None:
        if value is None:
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return max(0, parsed)

    def build_context(self, request: ContextRequest) -> ContextBuildResult:
        if not request.query or not request.query.strip():
            raise ValidationError("Context request query cannot be empty or blank")

        allocation = self._allocation(request.metadata)
        use_conversation = bool(allocation.get("use_conversation_history", True))
        use_memory = bool(allocation.get("use_memory", True))
        use_knowledge = bool(allocation.get("use_knowledge", True))
        max_memory_tokens = self._positive_limit(allocation.get("max_memory_tokens"))
        max_knowledge_tokens = self._positive_limit(allocation.get("max_knowledge_tokens"))
        max_history_tokens = self._positive_limit(allocation.get("max_history_tokens"))
        min_retrieval_score = allocation.get("min_retrieval_score")
        try:
            min_retrieval_score = float(min_retrieval_score) if min_retrieval_score is not None else None
        except (TypeError, ValueError):
            min_retrieval_score = None

        budget_manager = ContextBudgetManager(request.budget)
        all_items: list[ContextItem] = []
        query_item = ContextItem(
            item_id=f"query-{uuid.uuid4().hex[:8]}", kind=ContextItemKind.USER_QUERY,
            content=request.query.strip(), priority=20, score=1.0,
            estimated_tokens=self.estimator.estimate_text(request.query),
        )
        if query_item.estimated_tokens > request.budget.available_prompt_tokens:
            raise ValidationError(f"User query token count ({query_item.estimated_tokens}) exceeds available prompt budget ({request.budget.available_prompt_tokens})")

        if request.system_instructions:
            for idx, sys_text in enumerate(request.system_instructions):
                if sys_text and sys_text.strip():
                    all_items.append(ContextItem(item_id=f"sys-{idx}-{uuid.uuid4().hex[:6]}", kind=ContextItemKind.SYSTEM_INSTRUCTION, content=sys_text.strip(), priority=10, score=1.0, estimated_tokens=self.estimator.estimate_text(sys_text)))

        # Raw conversation history is short-term working context, not durable
        # memory. Bound both message count and its optional token allocation.
        try:
            max_history = max(0, int(request.metadata.get("_conversation_history_max_messages", 8)))
        except (TypeError, ValueError):
            max_history = 8
        bounded_history = request.conversation_history[-max_history:] if max_history and use_conversation else []
        num_conv = len(bounded_history)
        history_tokens = 0
        for idx, msg in enumerate(bounded_history):
            if not msg.content:
                continue
            estimated = self.estimator.estimate_message(msg)
            if max_history_tokens is not None and history_tokens + estimated > max_history_tokens:
                continue
            is_recent = (num_conv - idx) <= 4
            all_items.append(ContextItem(item_id=f"conv-{idx}-{uuid.uuid4().hex[:6]}", kind=ContextItemKind.CONVERSATION_MESSAGE, content=msg.content, priority=30 if is_recent else 60, score=float(idx + 1) / float(max(1, num_conv)), estimated_tokens=estimated, metadata={"role": msg.role, "history_index": idx, **msg.metadata}))
            history_tokens += estimated

        retrieval_candidates = list(request.retrieval_candidates) if use_knowledge else []
        if request.retrieval_result and request.retrieval_result.candidates and use_knowledge:
            for cand in request.retrieval_result.candidates:
                global_score = cand.metadata.get("global_score")
                try:
                    score = float(global_score) if global_score is not None else (cand.reranker_score if cand.reranker_score is not None else (cand.fused_score if cand.fused_score is not None else cand.retrieval_score))
                except (TypeError, ValueError):
                    score = cand.retrieval_score
                if min_retrieval_score is not None and score < min_retrieval_score:
                    continue
                retrieval_candidates.append(ContextItem(item_id=f"k-{cand.chunk_id}", kind=ContextItemKind.KNOWLEDGE_CHUNK, content=cand.content, priority=40, score=score, estimated_tokens=self.estimator.estimate_text(cand.content), source_id=cand.source_id, document_id=cand.document_id, version_id=cand.version_id, chunk_id=cand.chunk_id, retrieval_method=cand.retrieval_method, metadata=dict(cand.metadata), provenance=dict(cand.provenance)))
        if use_knowledge and min_retrieval_score is not None:
            retrieval_candidates = [item for item in retrieval_candidates if item.score >= min_retrieval_score]

        if max_knowledge_tokens is not None:
            knowledge_budget = 0
            bounded_knowledge: list[ContextItem] = []
            for item in retrieval_candidates:
                if knowledge_budget + item.estimated_tokens > max_knowledge_tokens:
                    continue
                bounded_knowledge.append(item)
                knowledge_budget += item.estimated_tokens
            retrieval_candidates = bounded_knowledge
        all_items.extend(retrieval_candidates)

        if request.memories and use_memory:
            memory_budget = 0
            for mem in request.memories:
                score = mem.confidence * mem.importance * mem.relevance
                estimated = self.estimator.estimate_text(mem.content)
                if max_memory_tokens is not None and memory_budget + estimated > max_memory_tokens:
                    continue
                all_items.append(ContextItem(item_id=f"mem-{mem.memory_id}", kind=ContextItemKind.MEMORY, content=mem.content, priority=50, score=score, estimated_tokens=estimated, memory_id=mem.memory_id, metadata={"kind": mem.kind.value, "status": mem.status.value}, provenance={"memory_id": mem.memory_id, "kind": mem.kind.value}))
                memory_budget += estimated

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

        selected_conv = [item for item in selected_items if item.kind == ContextItemKind.CONVERSATION_MESSAGE]
        selected_conv.sort(key=lambda item: item.metadata.get("history_index", 0))
        final_selected_order: list[ContextItem] = []
        for kind in (ContextItemKind.SYSTEM_INSTRUCTION, ContextItemKind.KNOWLEDGE_CHUNK, ContextItemKind.MEMORY, ContextItemKind.TOOL_RESULT, ContextItemKind.RESEARCH_EVIDENCE):
            final_selected_order.extend(item for item in selected_items if item.kind == kind)
        final_selected_order.extend(selected_conv)
        final_selected_order.append(query_item)

        while True:
            prompt_messages = PromptBuilder.build_prompt_messages(final_selected_order)
            total_prompt_tokens = sum(self.estimator.estimate_message(message) for message in prompt_messages)
            if total_prompt_tokens + request.budget.reserved_output_tokens <= request.budget.total_context_window:
                break
            removable = [item for item in final_selected_order if item.kind not in (ContextItemKind.SYSTEM_INSTRUCTION, ContextItemKind.USER_QUERY)]
            if not removable:
                raise ValidationError("Context Engine cannot fit mandatory system instructions and user query within the prompt budget")
            weakest = max(removable, key=lambda item: (item.priority, -item.score, item.item_id))
            final_selected_order.remove(weakest)
            dropped_items.append(weakest)

        allocated_by_kind = {kind: 0 for kind in ContextItemKind}
        total_selected_tokens = 0
        for item in final_selected_order:
            allocated_by_kind[item.kind] += item.estimated_tokens
            total_selected_tokens += item.estimated_tokens

        provenance_records: list[dict[str, object]] = []
        for item in final_selected_order:
            if item.kind in (ContextItemKind.KNOWLEDGE_CHUNK, ContextItemKind.MEMORY, ContextItemKind.RESEARCH_EVIDENCE):
                provenance_records.append({"item_id": item.item_id, "kind": item.kind.value, "score": round(item.score, 4), "source_id": item.source_id, "document_id": item.document_id, "version_id": item.version_id, "chunk_id": item.chunk_id, "memory_id": item.memory_id, "retrieval_method": item.retrieval_method, "content": item.content, "provenance": item.provenance})

        selection = ContextSelection(selected_items=final_selected_order, dropped_items=dropped_items, allocated_tokens={kind.value: tokens for kind, tokens in allocated_by_kind.items() if tokens > 0}, total_selected_tokens=total_selected_tokens)
        return ContextBuildResult(prompt_messages=prompt_messages, selection=selection, total_prompt_tokens=total_prompt_tokens, reserved_output_tokens=request.budget.reserved_output_tokens, total_context_window=request.budget.total_context_window, provenance=provenance_records, metadata=dict(request.metadata))
