from __future__ import annotations

import logging
import uuid
from typing import Any

from superagent.agents.critic import AgentCritic
from superagent.agents.models import (
    AgentExecutionStatus,
    AgentRequest,
    AgentResponse,
    AgentRoute,
    CritiqueResult,
    VerificationResult,
)
from superagent.agents.planner import AgentPlanner
from superagent.agents.ports import (
    AgentCriticPort,
    AgentOrchestratorPort,
    AgentPlannerPort,
    AgentRouterPort,
    AgentVerifierPort,
)
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
from superagent.tools import ResearchPipeline, ToolCall, ToolExecutionContext, ToolExecutorPort

logger = logging.getLogger(__name__)


class AgentOrchestrator(AgentOrchestratorPort):
    """Central Orchestrator coordinating routing, retrieval, tools, research, generation, critique, and memory."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        router: AgentRouterPort | None = None,
        planner: AgentPlannerPort | None = None,
        hybrid_retriever: HybridRetriever | None = None,
        memory_retriever: MemoryRetrieverPort | None = None,
        tool_executor: ToolExecutorPort | None = None,
        research_pipeline: ResearchPipeline | None = None,
        context_engine: ContextEngine | None = None,
        critic: AgentCriticPort | None = None,
        verifier: AgentVerifierPort | None = None,
        memory_lifecycle: MemoryLifecyclePort | None = None,
        execution_repository: ExecutionRepository | None = None,
        memory_repository: MemoryRepository | None = None,
        context_window_tokens: int = 8192,
    ) -> None:
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
        self.context_window_tokens = max(1, context_window_tokens)
        if memory_lifecycle:
            self.memory_lifecycle = memory_lifecycle
        elif memory_repository:
            self.memory_lifecycle = MemoryLifecycle(memory_repository=memory_repository)
        else:
            self.memory_lifecycle = None
        self.execution_repository = execution_repository

    def execute(self, request: AgentRequest) -> AgentResponse:
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        state = AgentStateMachine(
            execution_id=execution_id,
            request_id=request.request_id,
            execution_repository=self.execution_repository,
        )

        try:
            state.transition_to(AgentExecutionStatus.ROUTING)
            route = self.router.route_request(request)
            state.add_diagnostic("route", route.value)

            state.transition_to(AgentExecutionStatus.PLANNING)
            plan = self.planner.create_plan(request, route)
            state.add_diagnostic("plan", plan.model_dump(mode="json"))

            used_tools = False
            tool_ctx_items: list[ContextItem] = []

            if plan.tool_required:
                state.transition_to(AgentExecutionStatus.TOOL_EXECUTION)
                tool_exec_context = ToolExecutionContext(execution_id=execution_id)

                if route == AgentRoute.TOOL and self.tool_executor is not None:
                    msg_lower = request.message.lower()
                    if "time" in msg_lower:
                        tz = "UTC"
                        if "in " in msg_lower:
                            parts = msg_lower.split("in ")
                            if len(parts) > 1:
                                tz = parts[1].strip().split()[0].upper()
                        tool_call = ToolCall(
                            tool_call_id=f"call-time-{uuid.uuid4().hex[:6]}",
                            tool_name="current_time",
                            arguments={"timezone": tz},
                        )
                    else:
                        tool_call = ToolCall(
                            tool_call_id=f"call-calc-{uuid.uuid4().hex[:6]}",
                            tool_name="calculator",
                            arguments={"expression": request.message},
                        )

                    tool_res = self.tool_executor.execute_tool(tool_call, tool_exec_context)
                    used_tools = True
                    out_str = str(tool_res.output) if tool_res.output is not None else (tool_res.error or "No output")
                    tool_ctx_items.append(
                        ContextItem(
                            item_id="tool-res-1",
                            kind=ContextItemKind.TOOL_RESULT,
                            content=f"Tool '{tool_res.tool_name}' result: {out_str}",
                            priority=20,
                            score=1.0,
                            estimated_tokens=len(out_str.split()),
                            metadata={"tool_call_id": tool_res.tool_call_id, "status": tool_res.status.value},
                        )
                    )

                elif route == AgentRoute.RESEARCH and self.research_pipeline is not None:
                    evidences = self.research_pipeline.conduct_research(request.message, tool_exec_context)
                    if evidences:
                        used_tools = True
                        for idx, evid in enumerate(evidences):
                            tool_ctx_items.append(
                                ContextItem(
                                    item_id=f"research-evid-{idx+1}",
                                    kind=ContextItemKind.RESEARCH_EVIDENCE,
                                    content=f"Research Evidence [{evid.title}] ({evid.source_url}): {evid.content}",
                                    priority=30,
                                    score=0.9,
                                    estimated_tokens=len(evid.content.split()),
                                    metadata={"source_url": evid.source_url, "title": evid.title, "snippet": evid.snippet},
                                    provenance={"source_url": evid.source_url, "title": evid.title},
                                )
                            )

            state.transition_to(AgentExecutionStatus.RETRIEVING)
            retrieved_chunks: list[dict[str, Any]] = []
            retrieved_memories: list[MemoryRecord] = []

            if plan.memory_required and self.memory_retriever is not None:
                try:
                    retrieved_memories = self.memory_retriever.retrieve_memories(query_text=request.message, top_k=5)
                except Exception as exc:
                    logger.warning(f"Memory retrieval failed gracefully: {exc}")
                    state.add_diagnostic("memory_error", str(exc))

            if plan.retrieval_required and self.hybrid_retriever is not None:
                try:
                    retrieved_chunks = self.hybrid_retriever.retrieve(query=request.message, top_k=5)
                except Exception as exc:
                    logger.warning(f"Knowledge retrieval failed gracefully: {exc}")
                    state.add_diagnostic("retrieval_error", str(exc))

            used_retrieval = len(retrieved_chunks) > 0
            used_memory = len(retrieved_memories) > 0

            state.transition_to(AgentExecutionStatus.CONTEXT_BUILDING)
            ctx_items: list[ContextItem] = list(tool_ctx_items)
            for idx, chunk in enumerate(retrieved_chunks):
                content = chunk.get("content", "")
                if content:
                    ctx_items.append(
                        ContextItem(
                            item_id=f"chunk-{idx}",
                            kind=ContextItemKind.KNOWLEDGE_CHUNK,
                            content=content,
                            priority=40,
                            score=chunk.get("score", 0.5),
                            estimated_tokens=len(content.split()),
                            metadata=chunk.get("metadata", {}),
                        )
                    )

            ctx_request = ContextRequest(
                query=request.message,
                retrieval_candidates=ctx_items,
                memories=retrieved_memories,
                conversation_history=request.conversation_history,
                system_instructions=request.system_instructions,
                budget=ContextBudget(total_context_window=self.context_window_tokens),
            )

            build_result = self.context_engine.build_context(ctx_request)
            provenance = build_result.provenance

            iteration = 1
            final_answer = ""
            critique_res: CritiqueResult | None = None
            verifier_res: VerificationResult | None = None
            used_critic = False
            used_verifier = False

            system_prompt_str: str | None = None
            user_prompt_str: str = request.message
            for msg in build_result.prompt_messages:
                if msg.role == "system":
                    system_prompt_str = msg.content
                elif msg.role == "user":
                    user_prompt_str = msg.content
            current_user_prompt = user_prompt_str

            while iteration <= plan.max_iterations:
                state.transition_to(AgentExecutionStatus.GENERATING, details={"iteration": iteration})
                llm_req = LLMRequest(
                    prompt=current_user_prompt,
                    system_prompt=system_prompt_str,
                    max_tokens=request.execution_config.get("max_tokens", 1024),
                    temperature=request.execution_config.get("temperature", 0.7),
                )
                try:
                    llm_res = self.llm_provider.complete(llm_req)
                    state.increment_model_calls()
                    final_answer = llm_res.text.strip()
                except Exception as exc:
                    logger.error(f"LLM generation failed: {exc}")
                    state.transition_to(AgentExecutionStatus.FAILED, details={"error": str(exc)})
                    return AgentResponse(
                        request_id=request.request_id,
                        conversation_id=request.conversation_id,
                        answer=f"Execution failed during generation: {exc}",
                        execution_id=execution_id,
                        status=AgentExecutionStatus.FAILED,
                        iterations=iteration,
                        used_retrieval=used_retrieval,
                        used_memory=used_memory,
                        diagnostics=state.diagnostics,
                    )

                if plan.critic_required:
                    state.transition_to(AgentExecutionStatus.CRITIQUING)
                    used_critic = True
                    context_str = "\n".join(item.content for item in build_result.selection.selected_items)
                    critique_res = self.critic.critique(query=request.message, context_str=context_str, response_text=final_answer)

                if plan.verifier_required and used_retrieval:
                    state.transition_to(AgentExecutionStatus.VERIFYING)
                    used_verifier = True
                    verifier_res = self.verifier.verify(
                        query=request.message,
                        candidate_answer=final_answer,
                        context_provenance=provenance,
                    )

                critic_passed = critique_res.passed if critique_res else True
                verifier_passed = verifier_res.verified if verifier_res else True
                if (critic_passed and verifier_passed) or iteration >= plan.max_iterations:
                    break

                state.transition_to(AgentExecutionStatus.REVISING, details={"iteration": iteration})
                state.increment_retries()
                iteration += 1
                feedback_parts: list[str] = []
                if critique_res and critique_res.required_revision:
                    feedback_parts.append(f"Critic Feedback: {critique_res.required_revision}")
                if verifier_res and verifier_res.unsupported_claims:
                    feedback_parts.append(f"Unsupported claims: {'; '.join(verifier_res.unsupported_claims)}")
                current_user_prompt = (
                    f"{user_prompt_str}\n\nPrevious Answer Attempt:\n{final_answer}\n\n"
                    f"Revision Requirements:\n" + "\n".join(feedback_parts) + "\n\n"
                    "Please provide an updated, corrected response addressing the requirements."
                )

            state.transition_to(AgentExecutionStatus.MEMORY_PROCESSING)
            if self.memory_lifecycle is not None:
                try:
                    self.memory_lifecycle.process_interaction(
                        user_message=request.message,
                        assistant_message=final_answer,
                        execution_id=execution_id,
                    )
                except Exception as exc:
                    logger.warning(f"Memory lifecycle processing failed gracefully: {exc}")
                    state.add_diagnostic("memory_lifecycle_error", str(exc))

            state.transition_to(AgentExecutionStatus.COMPLETED)
            return AgentResponse(
                request_id=request.request_id,
                conversation_id=request.conversation_id,
                answer=final_answer,
                execution_id=execution_id,
                status=AgentExecutionStatus.COMPLETED,
                iterations=iteration,
                used_retrieval=used_retrieval,
                used_memory=used_memory,
                used_tools=used_tools,
                used_critic=used_critic,
                used_verifier=used_verifier,
                provenance=provenance,
                diagnostics={
                    **state.diagnostics,
                    "critique": critique_res.model_dump(mode="json") if critique_res else None,
                    "verification": verifier_res.model_dump(mode="json") if verifier_res else None,
                },
            )

        except Exception as exc:
            logger.exception(f"Unhandled orchestrator exception: {exc}")
            state.transition_to(AgentExecutionStatus.FAILED, details={"error": str(exc)})
            return AgentResponse(
                request_id=request.request_id,
                conversation_id=request.conversation_id,
                answer=f"Execution error: {exc}",
                execution_id=execution_id,
                status=AgentExecutionStatus.FAILED,
                iterations=1,
                diagnostics={"error": str(exc)},
            )
