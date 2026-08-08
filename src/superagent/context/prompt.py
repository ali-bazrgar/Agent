from __future__ import annotations

from typing import Sequence

from superagent.context.models import ChatMessage, ContextItem, ContextItemKind


class PromptBuilder:
    """Formats selected context items into structured chat messages for LLM completion."""

    @staticmethod
    def build_prompt_messages(selected_items: Sequence[ContextItem]) -> list[ChatMessage]:
        system_instructions: list[str] = []
        knowledge_chunks: list[ContextItem] = []
        memory_items: list[ContextItem] = []
        conversation_messages: list[ChatMessage] = []
        user_query: str | None = None

        # Categorize selected items
        for item in selected_items:
            if item.kind == ContextItemKind.SYSTEM_INSTRUCTION:
                system_instructions.append(item.content)
            elif item.kind == ContextItemKind.KNOWLEDGE_CHUNK:
                knowledge_chunks.append(item)
            elif item.kind == ContextItemKind.MEMORY:
                memory_items.append(item)
            elif item.kind == ContextItemKind.CONVERSATION_MESSAGE:
                role = item.metadata.get("role", "user")
                conversation_messages.append(ChatMessage(role=role, content=item.content))
            elif item.kind == ContextItemKind.USER_QUERY:
                user_query = item.content

        messages: list[ChatMessage] = []

        # 1. Build System Message (System instructions + Knowledge + Memories)
        system_sections: list[str] = []
        if system_instructions:
            system_sections.append("\n\n".join(system_instructions))

        if knowledge_chunks:
            k_lines = ["--- RETRIEVED KNOWLEDGE CONTEXT ---"]
            for idx, k_item in enumerate(knowledge_chunks, 1):
                doc_str = f"doc_id={k_item.document_id}" if k_item.document_id else ""
                chk_str = f"chunk_id={k_item.chunk_id}" if k_item.chunk_id else ""
                score_str = f"score={k_item.score:.3f}" if k_item.score else ""
                meta_str = ", ".join(filter(None, [doc_str, chk_str, score_str]))
                header = f"[{idx}] {meta_str}".strip() if meta_str else f"[{idx}]"
                k_lines.append(f"{header}\n{k_item.content}")
            system_sections.append("\n\n".join(k_lines))

        if memory_items:
            m_lines = ["--- RELEVANT MEMORIES ---"]
            for idx, m_item in enumerate(memory_items, 1):
                kind_str = f"kind={m_item.metadata.get('kind', 'memory')}"
                conf_str = f"confidence={m_item.score:.2f}" if m_item.score else ""
                header = f"[{idx}] {kind_str}" + (f", {conf_str}" if conf_str else "")
                m_lines.append(f"{header}\n{m_item.content}")
            system_sections.append("\n\n".join(m_lines))

        if system_sections:
            system_content = "\n\n".join(system_sections)
            messages.append(ChatMessage(role="system", content=system_content))

        # 2. Add Conversation History
        messages.extend(conversation_messages)

        # 3. Add Current User Query
        if user_query is not None:
            messages.append(ChatMessage(role="user", content=user_query))

        return messages
