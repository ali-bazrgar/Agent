from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from superagent.agents.critic import AgentCritic
from superagent.agents.models import AgentExecutionStatus, AgentRequest, AgentResponse, AgentRoute, CritiqueResult, VerificationResult
from superagent.agents.planner import AgentPlanner
from superagent.agents.ports import AgentCriticPort, AgentOrchestratorPort, AgentPlannerPort, AgentRouterPort, AgentVerifierPort
from superagent.agents.router import AgentRouter
from superagent.agents.state import AgentStateMachine
from superagent.agents.verifier import AgentVerifier
from superagent.context.builder import ContextEngine
from superagent.context.models import ContextBudget, ContextItem, ContextItemKind, ContextRequest
from superagent.context.ports import MemoryRetrieverPort
from superagent.memory.lifecycle import MemoryLifecycle
from superagent.memory.ports import MemoryLifecyclePort
from superagent.models.domain import MemoryRecord
from superagent.providers.contracts import LLMProvider, LLMRequest
from superagent.repositories.ports import ExecutionRepository, MemoryRepository
from superagent.retrieval import HybridRetriever
from superagent.tools import ResearchPipeline, ToolCall, ToolExecutionContext
from superagent.tools.ports import ToolExecutorPort

logger = logging.getLogger(__name__)


class AgentOrchestrator(AgentOrchestratorPort):
    """Central bounded execution engine for routing, retrieval, tools, reasoning and memory."""

    def __init__(self, llm_provider: LLMProvider, router: AgentRouterPort | None = None, planner: AgentPlannerPort | None = None, hybrid_retriever: HybridRetriever | None = None, memory_retriever: MemoryRetrieverPort | None = None, tool_executor: ToolExecutorPort | None = None, research_pipeline: ResearchPipeline | None = None, context_engine: ContextEngine | None = None, critic: AgentCriticPort | None = None, verifier: AgentVerifierPort | None = None, memory_lifecycle: MemoryLifecyclePort | None = None, execution_repository: ExecutionRepository | None = None, memory_repository: MemoryRepository | None = None) -> None:
        self.llm_provider = llm_provider
        self.router = router or AgentRouter()
        self.planner = planner or AgentPlanner()
        self.hybrid_retriever = hybrid_retriever
        self.memory_retriever = memory_retriever
        self.tool_executor = tool_executor
        self.research_pipeline = research_pipeline
        self.context_engine = context_engine or ContextEngine()
        self.critic = critic or AgentCritic(llm_provider=llm_provider)
        self.verifier = verifier or AgentVerifier()
        self.memory_repository = memory_repository
        self.memory_lifecycle = memory_lifecycle or (MemoryLifecycle(memory_repository=memory_repository) if memory_repository else None)
        self.execution_repository = execution_repository

    @staticmethod
    def _multimodal_user_content(text: str, attachments: list[dict[str, Any]]) -> list[dict[str, Any]] | str:
        if not attachments:
            return text
        blocks: list[dict[str, Any]] = [{"type": "text", "text": text}]
        for attachment in attachments:
            kind = attachment.get("kind")
            data = attachment.get("data")
            mime = attachment.get("mime_type") or "application/octet-stream"
            name = attachment.get("name") or "attachment"
            if not isinstance(data, str) or not data:
                continue
            if kind == "image":
                blocks.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}})
            elif kind == "audio":
                fmt = mime.split("/", 1)[-1].split(";", 1)[0]
                blocks.append({"type": "input_audio", "input_audio": {"data": data, "format": fmt}})
            elif kind == "video":
                blocks.append({"type": "input_video", "input_video": {"data": data}})
            elif kind == "file":
                text_content = attachment.get("text_content")
                if isinstance(text_content, str) and text_content.strip():
                    blocks.append({"type": "text", "text": f"[File: {name}]\n{text_content}"})
                else:
                    blocks.append({"type": "text", "text": f"[File attached: {name} ({mime})]. No text representation is available to the model for this file."})
        return blocks

    def execute(self, request: AgentRequest) -> AgentResponse:
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        state = AgentStateMachine(execution_id, request.request_id, self.execution_repository)
        try:
            state.transition_to(AgentExecutionStatus.ROUTING)
            route = self.router.route_request(request)
            state.add_diagnostic("route", route.value)
            state.transition_to(AgentExecutionStatus.PLANNING)
            plan = self.planner.create_plan(request, route)
            state.add_diagnostic("plan", plan.model_dump(mode="json"))

            context_items: list[ContextItem] = []
            used_tools = False
            llm_driven_tools = bool(request.execution_config.get("llm_driven_tools", True))
            if plan.tool_required and not llm_driven_tools:
                state.transition_to(AgentExecutionStatus.TOOL_EXECUTION)
                if self.tool_executor is None:
                    state.add_diagnostic("tool_error", "tool execution requested but no executor is configured")
                elif route == AgentRoute.TOOL:
                    call = self._build_tool_call(request.message)
                    state.reserve_tool_call()
                    result = self.tool_executor.execute_tool(call, ToolExecutionContext(execution_id=execution_id))
                    used_tools = True
                    rendered = str(result.output) if result.output is not None else (result.error or "No tool output")
                    context_items.append(ContextItem(item_id=f"tool-res-{call.tool_call_id}", kind=ContextItemKind.TOOL_RESULT, content=f"Tool '{result.tool_name}' result: {rendered}", priority=20, score=1.0 if result.status.value == "success" else 0.2, estimated_tokens=max(1, len(rendered) // 4), metadata={"tool_call_id": result.tool_call_id, "status": result.status.value}))
                elif route == AgentRoute.RESEARCH and self.research_pipeline is not None:
                    state.reserve_tool_call()
                    evidences = self.research_pipeline.conduct_research(request.message, ToolExecutionContext(execution_id=execution_id))
                    used_tools = bool(evidences)
                    for idx, evidence in enumerate(evidences):
                        context_items.append(ContextItem(item_id=f"research-evid-{idx + 1}", kind=ContextItemKind.RESEARCH_EVIDENCE, content=f"Research evidence [{evidence.title}] ({evidence.source_url}): {evidence.content}", priority=30, score=0.9, estimated_tokens=max(1, len(evidence.content) // 4), metadata={"source_url": evidence.source_url, "title": evidence.title, "snippet": evidence.snippet}, provenance={"source_url": evidence.source_url, "title": evidence.title}))

            state.transition_to(AgentExecutionStatus.RETRIEVING)
            retrieved_chunks: list[dict[str, Any]] = []
            retrieved_memories: list[MemoryRecord] = []
            if plan.memory_required and self.memory_retriever is not None:
                try:
                    retrieved_memories = list(self.memory_retriever.retrieve_memories(request.message, top_k=5))
                except Exception as exc:
                    state.add_diagnostic("memory_error", str(exc))
                    logger.warning("Memory retrieval failed gracefully: %s", exc)
            if plan.retrieval_required and self.hybrid_retriever is not None:
                try:
                    retrieved_chunks = list(self.hybrid_retriever.retrieve(query=request.message, top_k=5))
                except Exception as exc:
                    state.add_diagnostic("retrieval_error", str(exc))
                    logger.warning("Knowledge retrieval failed gracefully: %s", exc)

            used_retrieval = bool(retrieved_chunks)
            used_memory = bool(retrieved_memories)
            for idx, chunk in enumerate(retrieved_chunks):
                content = str(chunk.get("content", ""))
                if not content:
                    continue
                metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
                context_items.append(ContextItem(item_id=str(chunk.get("chunk_id") or f"chunk-{idx}"), kind=ContextItemKind.KNOWLEDGE_CHUNK, content=content, priority=40, score=float(chunk.get("score", 0.5)), estimated_tokens=max(1, len(content) // 4), metadata=metadata, document_id=chunk.get("document_id"), version_id=chunk.get("version_id"), chunk_id=chunk.get("chunk_id"), retrieval_method=chunk.get("retrieval_method"), provenance=chunk.get("provenance") or {}))

            state.transition_to(AgentExecutionStatus.CONTEXT_BUILDING)
            context_window = int(request.execution_config["context_window_tokens"])
            reserved_output = min(int(request.execution_config.get("max_tokens", 1024)), max(0, context_window // 4))
            ctx_request = ContextRequest(query=request.message, retrieval_candidates=context_items, memories=retrieved_memories, conversation_history=request.conversation_history, system_instructions=request.system_instructions, budget=ContextBudget(total_context_window=context_window, reserved_output_tokens=reserved_output), metadata=request.metadata)
            build_result = self.context_engine.build_context(ctx_request)
            provenance = build_result.provenance
            messages: list[dict[str, Any]] = [{"role": m.role, "content": m.content} for m in build_result.prompt_messages]
            system_prompt = next((m["content"] for m in messages if m["role"] == "system"), None)
            user_prompt = next((m["content"] for m in reversed(messages) if m["role"] == "user"), request.message)
            user_index = next((idx for idx in range(len(messages) - 1, -1, -1) if messages[idx]["role"] == "user"), None)
            attachments = request.metadata.get("attachments") if isinstance(request.metadata, dict) else None
            if isinstance(attachments, list):
                if user_index is None:
                    messages.append({"role": "user", "content": request.message})
                    user_index = len(messages) - 1
                messages[user_index]["content"] = self._multimodal_user_content(request.message, [a for a in attachments if isinstance(a, dict)])
                state.add_diagnostic("attachment_count", len(attachments))

            iteration = 1
            final_answer = ""
            critique_res: CritiqueResult | None = None
            verifier_res: VerificationResult | None = None
            used_critic = False
            used_verifier = False
            current_messages = messages

            while iteration <= plan.max_iterations:
                state.transition_to(AgentExecutionStatus.GENERATING, {"iteration": iteration})
                try:
                    state.reserve_model_call()
                    response = self.llm_provider.complete(LLMRequest(prompt=user_prompt, system_prompt=system_prompt, messages=current_messages, max_tokens=request.execution_config.get("max_tokens", 1024), temperature=request.execution_config.get("temperature", 0.7), metadata=request.metadata))
                    final_answer = response.text.strip()
                    executed_tools = response.metadata.get("tool_calls_executed", []) if isinstance(response.metadata, dict) else []
                    if isinstance(executed_tools, list) and executed_tools:
                        used_tools = True
                        if any(isinstance(item, dict) and str(item.get("name", "")).startswith("memory.") for item in executed_tools):
                            used_memory = True
                        state.add_diagnostic("agentic_tool_calls", executed_tools)
                except Exception as exc:
                    state.transition_to(AgentExecutionStatus.FAILED, {"error": str(exc)})
                    return AgentResponse(request_id=request.request_id, conversation_id=request.conversation_id, answer=f"Execution failed during generation: {exc}", execution_id=execution_id, status=AgentExecutionStatus.FAILED, iterations=iteration, used_retrieval=used_retrieval, used_memory=used_memory, used_tools=used_tools, diagnostics=state.diagnostics)

                if plan.critic_required:
                    state.transition_to(AgentExecutionStatus.CRITIQUING)
                    used_critic = True
                    context_text = "\n".join(item.content for item in build_result.selection.selected_items)
                    state.add_diagnostic("critic", {"iteration": iteration, "input_chars": len(final_answer) + len(request.message) + len(context_text)})
                    state.reserve_model_call()
                    critique_res = self.critic.critique(request.message, context_text, final_answer)
                    state.add_diagnostic("critic_result", critique_res.model_dump(mode="json"))

                if plan.verifier_required and (used_retrieval or used_tools):
                    state.transition_to(AgentExecutionStatus.VERIFYING)
                    used_verifier = True
                    verifier_res = self.verifier.verify(request.message, final_answer, provenance)

                if ((critique_res.passed if critique_res else True) and (verifier_res.verified if verifier_res else True)) or iteration >= plan.max_iterations or not plan.revision_allowed:
                    break

                state.transition_to(AgentExecutionStatus.REVISING, {"iteration": iteration})
                state.increment_retries()
                iteration += 1
                feedback: list[str] = []
                if critique_res and critique_res.required_revision:
                    feedback.append(f"Critic feedback: {critique_res.required_revision}")
                if verifier_res and verifier_res.unsupported_claims:
                    feedback.append("Unsupported claims: " + "; ".join(verifier_res.unsupported_claims))
                current_messages = [*messages, {"role": "assistant", "content": final_answer}, {"role": "user", "content": "Revise the answer.\n\n" + ("\n".join(feedback) or "Re-check all evidence.")}]

            state.transition_to(AgentExecutionStatus.MEMORY_PROCESSING)
            if self.memory_lifecycle is not None:
                try:
                    self.memory_lifecycle.process_interaction(request.message, final_answer, execution_id)
                except Exception as exc:
                    state.add_diagnostic("memory_lifecycle_error", str(exc))
                    logger.warning("Memory lifecycle failed gracefully: %s", exc)
            state.transition_to(AgentExecutionStatus.COMPLETED)
            return AgentResponse(request_id=request.request_id, conversation_id=request.conversation_id, answer=final_answer, execution_id=execution_id, status=AgentExecutionStatus.COMPLETED, iterations=iteration, used_retrieval=used_retrieval, used_memory=used_memory, used_tools=used_tools, used_critic=used_critic, used_verifier=used_verifier, provenance=provenance, diagnostics={**state.diagnostics, "critique": critique_res.model_dump(mode="json") if critique_res else None, "verification": verifier_res.model_dump(mode="json") if verifier_res else None})
        except Exception as exc:
            logger.exception("Unhandled orchestrator exception: %s", exc)
            try:
                state.transition_to(AgentExecutionStatus.FAILED, {"error": str(exc)})
            except Exception:
                pass
            return AgentResponse(request_id=request.request_id, conversation_id=request.conversation_id, answer=f"Execution error: {exc}", execution_id=execution_id, status=AgentExecutionStatus.FAILED, iterations=1, diagnostics={"error": str(exc)})

    @staticmethod
    def _build_tool_call(message: str) -> ToolCall:
        lowered = message.lower().strip()
        if any(token in lowered for token in ("what time", "current time", "time in")):
            timezone_name = "UTC"
            match = re.search(r"(?:time\s+in|timezone)\s+([A-Za-z_]+(?:/[A-Za-z_]+)*)", message, re.I)
            if match:
                timezone_name = match.group(1)
            return ToolCall(tool_call_id=f"call-time-{uuid.uuid4().hex[:6]}", tool_name="current_time", arguments={"timezone": timezone_name})
        expression = message.strip()
        match = re.search(r"(?:calculate|compute|calculator|math)\s*[:=]?\s*(.+)$", expression, re.I)
        if match:
            expression = match.group(1).strip()
        return ToolCall(tool_call_id=f"call-calc-{uuid.uuid4().hex[:6]}", tool_name="calculator", arguments={"expression": expression})
