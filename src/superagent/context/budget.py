from __future__ import annotations

import math
from typing import Callable

from superagent.context.models import ChatMessage, ContextBudget, ContextItem, ContextItemKind
from superagent.core.errors import ValidationError


class TokenEstimator:
    """Deterministic token estimator with optional custom tokenizer override."""

    def __init__(self, tokenizer_fn: Callable[[str], int] | None = None) -> None:
        self._tokenizer_fn = tokenizer_fn

    def estimate_text(self, text: str) -> int:
        if not text:
            return 0
        if self._tokenizer_fn is not None:
            return max(0, self._tokenizer_fn(text))
        # Default deterministic character ratio (~4 characters per token)
        return max(1, math.ceil(len(text) / 4.0))

    def estimate_message(self, message: ChatMessage) -> int:
        # Message tokens = content tokens + 4 tokens overhead for role/struct framing
        content_tokens = self.estimate_text(message.content or "")
        return content_tokens + 4

    def estimate_item(self, item: ContextItem) -> int:
        # Item tokens = content tokens + overhead for metadata/formatting
        content_tokens = self.estimate_text(item.content or "")
        return content_tokens + 4


class ContextBudgetManager:
    """Enforces token budget limits and tracks allocation across context categories."""

    def __init__(self, budget: ContextBudget) -> None:
        self.budget = budget
        if self.budget.available_prompt_tokens <= 0:
            raise ValidationError(
                f"Invalid context budget: total context window ({self.budget.total_context_window}) "
                f"must be greater than reserved output tokens ({self.budget.reserved_output_tokens})"
            )

        self._remaining_tokens = self.budget.available_prompt_tokens
        self.allocated_by_kind: dict[ContextItemKind, int] = {kind: 0 for kind in ContextItemKind}

    @property
    def remaining_tokens(self) -> int:
        return self._remaining_tokens

    def get_category_cap(self, kind: ContextItemKind) -> int | None:
        if kind == ContextItemKind.SYSTEM_INSTRUCTION:
            return self.budget.system_budget
        elif kind == ContextItemKind.USER_QUERY:
            return self.budget.query_budget
        elif kind == ContextItemKind.CONVERSATION_MESSAGE:
            return self.budget.conversation_budget
        elif kind == ContextItemKind.KNOWLEDGE_CHUNK:
            return self.budget.knowledge_budget
        elif kind == ContextItemKind.MEMORY:
            return self.budget.memory_budget
        return None

    def can_fit(self, item: ContextItem) -> bool:
        needed = item.estimated_tokens
        if needed > self._remaining_tokens:
            return False

        category_cap = self.get_category_cap(item.kind)
        if category_cap is not None:
            already_used = self.allocated_by_kind.get(item.kind, 0)
            if already_used + needed > category_cap:
                return False

        return True

    def consume(self, item: ContextItem) -> None:
        needed = item.estimated_tokens
        self._remaining_tokens -= needed
        self.allocated_by_kind[item.kind] = self.allocated_by_kind.get(item.kind, 0) + needed
