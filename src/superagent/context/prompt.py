from __future__ import annotations

from typing import Sequence

from superagent.context.models import ChatMessage, ContextItem, ContextItemKind


class PromptBuilder:
    """Formats selected context into provider-neutral chat messages."""

    @staticmethod
    def build_prompt_messages(selected_items: Sequence[ContextItem]) -> list[ChatMessage]:
        system_sections: list[str] = []
        conversation_messages: list[ChatMessage] = []
        user_query: str | None = None

        knowledge = [item for item in selected_items if item.kind == ContextItemKind.KNOWLEDGE_CHUNK]
        memories = [item for item in selected_items if item.kind == ContextItemKind.MEMORY]
        tool_results = [item for item in selected_items if item.kind == ContextItemKind.TOOL_RESULT]
        research = [item for item in selected_items if item.kind == ContextItemKind.RESEARCH_EVIDENCE]

        for item in selected_items:
            if item.kind == ContextItemKind.SYSTEM_INSTRUCTION:
                system_sections.append(item.content)
            elif item.kind == ContextItemKind.CONVERSATION_MESSAGE:
                conversation_messages.append(
                    ChatMessage(role=str(item.metadata.get("role", "user")), content=item.content)
                )
            elif item.kind == ContextItemKind.USER_QUERY:
                user_query = item.content

        if knowledge:
            lines = ["--- RETRIEVED KNOWLEDGE CONTEXT ---"]
            for idx, item in enumerate(knowledge, 1):
                refs = ", ".join(
                    value for value in (
                        f"doc_id={item.document_id}" if item.document_id else "",
                        f"chunk_id={item.chunk_id}" if item.chunk_id else "",
                        f"score={item.score:.3f}",
                    ) if value
                )
                lines.append(f"[{idx}] {refs}\n{item.content}")
            system_sections.append("\n\n".join(lines))

        if memories:
            lines = [
                "--- RELEVANT MEMORIES ---",
                "These records are durable user memory retrieved from persistent storage. "
                "Treat them as user-provided facts. Use them when relevant, do not invent "
                "additional facts, and do not claim to remember information that is not present here.",
            ]
            for idx, item in enumerate(memories, 1):
                lines.append(
                    f"[{idx}] kind={item.metadata.get('kind', 'memory')}, "
                    f"confidence={item.score:.2f}\n{item.content}"
                )
            system_sections.append("\n\n".join(lines))

        if tool_results:
            lines = ["--- TOOL RESULTS ---"]
            lines.extend(f"[{idx}] {item.content}" for idx, item in enumerate(tool_results, 1))
            system_sections.append("\n\n".join(lines))

        if research:
            lines = ["--- WEB RESEARCH EVIDENCE ---"]
            lines.extend(f"[{idx}] {item.content}" for idx, item in enumerate(research, 1))
            system_sections.append("\n\n".join(lines))

        messages: list[ChatMessage] = []
        if system_sections:
            messages.append(ChatMessage(role="system", content="\n\n".join(system_sections)))
        messages.extend(conversation_messages)
        if user_query is not None:
            messages.append(ChatMessage(role="user", content=user_query))
        return messages
