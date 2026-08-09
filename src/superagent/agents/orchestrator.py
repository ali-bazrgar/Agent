from __future__ import annotations

import json
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
from superagent.llm.runtime import ModelRuntimeConfig
from superagent.memory.lifecycle import MemoryLifecycle
from superagent.memory.ports import MemoryLifecyclePort
from superagent.models.domain import MemoryRecord
from superagent.observability.diagnostics import get_diagnostic_store
from superagent.providers.contracts import LLMProvider, LLMRequest
from superagent.repositories.ports import ExecutionRepository, MemoryRepository
from superagent.retrieval import HybridRetriever
from superagent.retrieval.models import RetrievalQuery
from superagent.tools import ResearchPipeline, ToolCall, ToolExecutionContext
from superagent.tools.ports import ToolExecutorPort

logger = logging.getLogger(__name__)


class AgentOrchestrator(AgentOrchestratorPort):
    """Central bounded execution engine for routing, retrieval, tools, reasoning and memory."""

    def __init__(self, llm_provider: LLMProvider, router: AgentRouterPort | None = None, planner: AgentPlannerPort | None = None, hybrid_retriever: HybridRetriever | None = None, memory_retriever: MemoryRetrieverPort | None = None, tool_executor: ToolExecutorPort | None = None, research_pipeline: ResearchPipeline | None = None, context_engine: ContextEngine | None = None, critic: AgentCriticPort | None = None, verifier: AgentVerifierPort | None = None, memory_lifecycle: MemoryLifecyclePort | None = None, execution_repository: ExecutionRepository | None = None, memory_repository: MemoryRepository | None = None, runtime_config: ModelRuntimeConfig | None = None) -> None:
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
        self.runtime_config = runtime_config
        self.diagnostics = get_diagnostic_store()

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
        config = dict(request.execution_config)
        runtime = request.runtime_config or self.runtime_config
        if runtime is not None:
            config.setdefault("context_window_tokens", runtime.context_window_tokens)
            if runtime.max_output_tokens is not None:
                config.setdefault("max_tokens", runtime.max_output_tokens)
            config.setdefault("temperature", runtime.temperature)
            config.setdefault("top_p", runtime.top_p)
        config.setdefault("context_window_tokens", 8192)
        config.setdefault("memory_recall_every_message", True)
        config.setdefault("memory_recall_top_k", 5)
        config.setdefault("max_model_calls", 4)
        config.setdefault("max_tool_calls", 8)
        config.setdefault("max_retries", 2)
        config.setdefault("max_execution_time_seconds", 60)
        config.setdefault("max_total_model_tokens", 0)
        config.setdefault("automatic_memory_extraction_enabled", False)
        state = AgentStateMachine(execution_id, request.request_id, self.execution_repository, max_model_calls=config.get("max_model_calls"), max_tool_calls=config.get("max_tool_calls"), max_retries=config.get("max_retries"), max_execution_time_seconds=config.get("max_execution_time_seconds"), max_total_model_tokens=config.get("max_total_model_tokens"))
        try:
            state.transition_to(AgentExecutionStatus.ROUTING)
            with self.diagnostics.span("agent.route", execution_id=execution_id, request_id=request.request_id):
                route = self.router.route_request(request)
            state.add_diagnostic("route", route.value)
            state.transition_to(AgentExecutionStatus.PLANNING)
            with self.diagnostics.span("agent.plan", execution_id=execution_id, request_id=request.request_id):
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
                    with self.diagnostics.span("tools.execute", execution_id=execution_id, request_id=request.request_id, route=route.value):
                        call = self._build_tool_call(request.message)
                        state.reserve_tool_call()
                        result = self.tool_executor.execute_tool(call, ToolExecutionContext(execution_id=execution_id))
                    used_tools = True
                    rendered = str(result.output) if result.output is not None else (result.error or "No tool output")
                    context_items.append(ContextItem(item_id=f"tool-res-{call.tool_call_id}", kind=ContextItemKind.TOOL_RESULT, content=f"Tool '{result.tool_name}' result: {rendered}", priority=20, score=1.0 if result.status.value == "success" else 0.2, estimated_tokens=max(1, len(rendered) // 4), metadata={"tool_call_id": result.tool_call_id, "status": result.status.value}))
                elif route == AgentRoute.RESEARCH and self.research_pipeline is not None:
                    with self.diagnostics.span("research.execute", execution_id=execution_id, request_id=request.request_id):
                        state.reserve_tool_call()
                        evidences = self.research_pipeline.conduct_research(request.message, ToolExecutionContext(execution_id=execution_id))
                    used_tools = bool(evidences)
                    for idx, evidence in enumerate(evidences):
                        context_items.append(ContextItem(item_id=f"research-evid-{idx + 1}", kind=ContextItemKind.RESEARCH_EVIDENCE, content=f"Research evidence [{evidence.title}] ({evidence.source_url}): {evidence.content}", priority=30, score=0.9, estimated_tokens=max(1, len(evidence.content) // 4), metadata={"source_url": evidence.source_url, "title": evidence.title, "snippet": evidence.snippet}, provenance={"source_url": evidence.source_url, "title": evidence.title}))
            state.transition_to(AgentExecutionStatus.RETRIEVING)
            retrieved_chunks: list[dict[str, Any]] = []
            retrieved_memories: list[MemoryRecord] = []
            if config.get("memory_recall_every_message", True) and self.memory_retriever is not None:
                try:
                    top_k = max(1, int(config.get("memory_recall_top_k", 5)))
                    with self.diagnostics.span("memory.recall", execution_id=execution_id, request_id=request.request_id, top_k=top_k):
                        retrieved_memories = list(self.memory_retriever.retrieve_memories(request.message, top_k=top_k))
                    state.add_diagnostic("memory_recall", {"enabled": True, "top_k": top_k, "matches": len(retrieved_memories), "mode": "persistent_recall"})
                except Exception as exc:
                    state.add_diagnostic("memory_error", str(exc))
                    logger.warning("Memory retrieval failed gracefully: %s", exc)
            if plan.retrieval_required and self.hybrid_retriever is not None:
                try:
                    retrieval_query = RetrievalQuery(text=request.message, top_k=5, candidate_k=5)
                    with self.diagnostics.span("knowledge.retrieve", execution_id=execution_id, request_id=request.request_id, top_k=5, candidate_k=5):
                        retrieval_result = self.hybrid_retriever.retrieve(retrieval_query)
                    retrieved_chunks = [{"chunk_id": candidate.chunk_id, "document_id": candidate.document_id, "version_id": candidate.version_id, "content": candidate.content, "score": candidate.reranker_score if candidate.reranker_score is not None else candidate.fused_score if candidate.fused_score is not None else candidate.retrieval_score, "retrieval_method": candidate.retrieval_method, "provenance": candidate.provenance, "metadata": candidate.metadata} for candidate in retrieval_result.candidates]
                    state.add_diagnostic("knowledge_retrieval", {"candidates": len(retrieved_chunks), "dense": retrieval_result.dense_count, "lexical": retrieval_result.lexical_count, "fused": retrieval_result.fused_count, "reranked": retrieval_result.reranked, "duration_ms": retrieval_result.duration_ms})
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
            context_window = int(config["context_window_tokens"])
            reserved_output = int(config.get("reserved_output_tokens", 0))
            ctx_request = ContextRequest(query=request.message, retrieval_candidates=context_items, memories=retrieved_memories, conversation_history=request.conversation_history, system_instructions=request.system_instructions, budget=ContextBudget(total_context_window=context_window, reserved_output_tokens=reserved_output), metadata=request.metadata)
            with self.diagnostics.span("context.build", execution_id=execution_id, request_id=request.request_id, context_window_tokens=context_window):
                build_result = self.context_engine.build_context(ctx_request)
            state.add_diagnostic("context", {"context_window": build_result.total_context_window, "prompt_tokens_estimated": build_result.total_prompt_tokens, "reserved_output_tokens": build_result.reserved_output_tokens, "selected_tokens": build_result.selection.total_selected_tokens, "allocated_tokens": build_result.selection.allocated_tokens, "selected_items": len(build_result.selection.selected_items), "dropped_items": len(build_result.selection.dropped_items)})
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
            current_messages = messages
            provider_metadata = {**request.metadata, "_tool_call_reserver": state.reserve_tool_call}
            tool_evidence_text: list[str] = []
            while iteration <= plan.max_iterations:
                state.transition_to(AgentExecutionStatus.GENERATING, {"iteration": iteration})
                try:
                    state.reserve_model_call()
                    with self.diagnostics.span("llm.generate", execution_id=execution_id, request_id=request.request_id, iteration=iteration, context_window_tokens=context_window):
                        response = self.llm_provider.complete(LLMRequest(prompt=user_prompt, system_prompt=system_prompt, messages=current_messages, max_tokens=config.get("max_tokens"), temperature=config.get("temperature", 0.7), top_p=config.get("top_p", 1.0), metadata=provider_metadata))
                    final_answer = response.text.strip()
                    if not (isinstance(response.metadata, dict) and response.metadata.get("usage_recorded") is True):
                        state.record_model_usage(response.token_usage)
                    state.add_diagnostic("llm_usage", response.token_usage)
                    if isinstance(response.metadata, dict):
                        timings = response.metadata.get("timings")
                        if isinstance(timings, dict) and timings:
                            state.add_diagnostic("llm_timings", timings)
                    executed_tools = response.metadata.get("tool_calls_executed", []) if isinstance(response.metadata, dict) else []
                    raw_tool_results = response.metadata.get("tool_results", []) if isinstance(response.metadata, dict) else []
                    if isinstance(executed_tools, list) and executed_tools:
                        used_tools = True
                        if any(isinstance(item, dict) and str(item.get("name", "")).startswith("memory.") for item in executed_tools):
                            used_memory = True
                        if any(isinstance(item, dict) and str(item.get("name", "")).startswith("knowledge.") for item in executed_tools):
                            used_retrieval = True
                        state.add_diagnostic("agentic_tool_calls", executed_tools)
                    if isinstance(raw_tool_results, list):
                        for tool_result in raw_tool_results:
                            if not isinstance(tool_result, dict):
                                continue
                            name = str(tool_result.get("name", ""))
                            output = tool_result.get("output")
                            if name == "knowledge.search" and isinstance(output, dict):
                                results = output.get("results")
                                if isinstance(results, list):
                                    for result in results:
                                        if not isinstance(result, dict):
                                            continue
                                        content = result.get("content")
                                        if not isinstance(content, str) or not content.strip():
                                            continue
                                        provenance.append({"item_id": f"tool-{tool_result.get('id', 'knowledge')}", "kind": "tool_result", "score": result.get("score"), "document_id": result.get("document_id"), "version_id": result.get("version_id"), "chunk_id": result.get("chunk_id"), "content": content, "retrieval_method": result.get("retrieval_method"), "provenance": result.get("provenance") or {}})
                                        tool_evidence_text.append(content)
                            elif name in {"web.search", "web.fetch"} and isinstance(output, (dict, list, str)):
                                evidence_text = json.dumps(output, ensure_ascii=False, default=str)
                                provenance.append({"item_id": f"tool-{tool_result.get('id', name)}", "kind": "tool_result", "content": evidence_text})
                                tool_evidence_text.append(evidence_text)
                    if iteration >= plan.max_iterations:
                        break
                    critique_res = self.critic.critique(request.message, final_answer, provenance, state=state)
                    state.add_diagnostic("critique", critique_res.model_dump(mode="json"))
                    if not critique_res.required_revision:
                        verifier_res = self.verifier.verify(request.message, final_answer, provenance)
                        state.add_diagnostic("verification", verifier_res.model_dump(mode="json"))
                        if verifier_res.passed:
                            break
                    feedback: list[str] = []
                    if critique_res and critique_res.required_revision:
                        feedback.append(f"Critic feedback: {critique_res.required_revision}")
                    if verifier_res and verifier_res.unsupported_claims:
                        feedback.append("Unsupported claims: " + "; ".join(verifier_res.unsupported_claims))
                    current_messages = [*messages, {"role": "user", "content": "\n".join(feedback)}]
                    iteration += 1
                except Exception as exc:
                    logger.exception("LLM generation failed for execution %s", execution_id)
                    state.add_diagnostic("llm_error", {"type": type(exc).__name__, "message": str(exc)})
                    raise
            state.transition_to(AgentExecutionStatus.MEMORY_PROCESSING)
            if self.memory_lifecycle is not None:
                try:
                    with self.diagnostics.span("memory.process", execution_id=execution_id, request_id=request.request_id):
                        self.memory_lifecycle.process_interaction(request.message, final_answer, execution_id=execution_id, enable_heuristic_extraction=bool(config.get("automatic_memory_extraction_enabled", False)))
                except Exception as exc:
                    state.add_diagnostic("memory_processing_error", str(exc))
                    logger.warning("Memory lifecycle processing failed gracefully: %s", exc)
            state.transition_to(AgentExecutionStatus.COMPLETED)
            return AgentResponse(request_id=request.request_id, conversation_id=request.conversation_id, answer=final_answer, execution_id=execution_id, status=state.current_status, iterations=iteration, used_retrieval=used_retrieval, used_memory=used_memory, used_tools=used_tools, diagnostics=state.diagnostics)
        except Exception as exc:
            try:
                state.transition_to(AgentExecutionStatus.FAILED, {"error": str(exc)})
            except Exception:
                pass
            return AgentResponse(request_id=request.request_id, conversation_id=request.conversation_id, answer=f"Execution failed: {exc}", execution_id=execution_id, status=state.current_status, iterations=1, used_retrieval=False, used_memory=False, used_tools=False, diagnostics=state.diagnostics)

    def _build_tool_call(self, message: str) -> ToolCall:
        match = re.match(r"^([\w.-]+)\s*(.*)$", message.strip(), flags=re.DOTALL)
        if not match:
            raise ValueError("Unable to parse tool command")
        return ToolCall(tool_call_id=f"tool-{uuid.uuid4().hex[:8]}", name=match.group(1), arguments={"input": match.group(2).strip()})
