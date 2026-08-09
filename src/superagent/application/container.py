from __future__ import annotations

import json
from dataclasses import dataclass, field

from superagent.agents import AgentCritic, AgentOrchestrator, AgentPlanner, AgentRouter, AgentVerifier
from superagent.config.settings import Settings, get_settings
from superagent.context import ContextEngine
from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.database.repositories.sqlite_chunk_repository import SqliteChunkRepository
from superagent.database.repositories.sqlite_document_repository import SqliteDocumentRepository
from superagent.database.repositories.sqlite_document_version_repository import SqliteDocumentVersionRepository
from superagent.database.repositories.sqlite_embedding_repository import SqliteEmbeddingRepository
from superagent.database.repositories.sqlite_execution_repository import SqliteExecutionRepository
from superagent.database.repositories.sqlite_flashcard_repository import SqliteFlashcardRepository
from superagent.database.repositories.sqlite_knowledge_repository import SqliteKnowledgeRepository
from superagent.database.repositories.sqlite_memory_repository import SqliteMemoryRepository
from superagent.database.repositories.sqlite_review_repository import SqliteReviewRepository
from superagent.database.repositories.sqlite_source_repository import SqliteSourceRepository
from superagent.database.repositories.sqlite_tag_repository import SqliteTagRepository
from superagent.embeddings.llama_cpp_provider import LlamaCppEmbeddingProvider
from superagent.knowledge.ingest.pipeline import DocumentIngestionPipeline
from superagent.llm.agentic_provider import AgenticLLMProvider
from superagent.llm.capabilities import EffectiveCapabilities, ModelCapabilityRegistry
from superagent.llm.capability_policy import CapabilityPolicy
from superagent.llm.llama_cpp_provider import LlamaCppLLMProvider
from superagent.llm.openai_compatible_provider import OpenAICompatibleLLMProvider
from superagent.llm.provider_registry import LLMProviderRegistry
from superagent.llm.runtime import ModelRuntimeConfig
from superagent.memory import DefaultMemoryRetriever, MemoryConsolidator, MemoryExtractor, MemoryLifecycle
from superagent.observability.logging import configure_logging
from superagent.providers.contracts import EmbeddingProvider, LLMProvider, RerankerProvider, WebResearchProvider
from superagent.reranking.llama_cpp_provider import LlamaCppRerankerProvider
from superagent.retrieval import CandidateFusion, DenseRetriever, HybridRetriever, LexicalRetriever, ReciprocalRankFusion, SqliteDenseRetriever, SqliteLexicalRetriever
from superagent.tools import CalculatorTool, DefaultWebSearchProvider, KnowledgeSearchTool, MemorySearchTool, MemoryWriteTool, ResearchPipeline, TimeTool, ToolExecutor, ToolRegistry, WebFetchTool, WebSearchTool


@dataclass
class AppContainer:
    """Composition root for wiring application components and repositories."""

    settings: Settings | None = None
    logger: object | None = None
    database_engine: DatabaseEngine | None = None
    llm_provider: LLMProvider | None = None
    embedding_provider: EmbeddingProvider | None = None
    reranker_provider: RerankerProvider | None = None
    web_provider: WebResearchProvider | None = None
    llm_provider_registry: LLMProviderRegistry | None = None
    runtime_config: ModelRuntimeConfig | None = None
    effective_capabilities: EffectiveCapabilities | None = None

    _source_repository: SqliteSourceRepository | None = field(default=None, init=False)
    _document_repository: SqliteDocumentRepository | None = field(default=None, init=False)
    _document_version_repository: SqliteDocumentVersionRepository | None = field(default=None, init=False)
    _chunk_repository: SqliteChunkRepository | None = field(default=None, init=False)
    _embedding_repository: SqliteEmbeddingRepository | None = field(default=None, init=False)
    _knowledge_repository: SqliteKnowledgeRepository | None = field(default=None, init=False)
    _tag_repository: SqliteTagRepository | None = field(default=None, init=False)
    _memory_repository: SqliteMemoryRepository | None = field(default=None, init=False)
    _execution_repository: SqliteExecutionRepository | None = field(default=None, init=False)
    _flashcard_repository: SqliteFlashcardRepository | None = field(default=None, init=False)
    _review_repository: SqliteReviewRepository | None = field(default=None, init=False)
    _ingestion_pipeline: DocumentIngestionPipeline | None = field(default=None, init=False)
    _dense_retriever: DenseRetriever | None = field(default=None, init=False)
    _lexical_retriever: LexicalRetriever | None = field(default=None, init=False)
    _candidate_fusion: CandidateFusion | None = field(default=None, init=False)
    _hybrid_retriever: HybridRetriever | None = field(default=None, init=False)
    _context_engine: ContextEngine | None = field(default=None, init=False)
    _agent_router: AgentRouter | None = field(default=None, init=False)
    _agent_planner: AgentPlanner | None = field(default=None, init=False)
    _agent_critic: AgentCritic | None = field(default=None, init=False)
    _agent_verifier: AgentVerifier | None = field(default=None, init=False)
    _memory_extractor: MemoryExtractor | None = field(default=None, init=False)
    _memory_consolidator: MemoryConsolidator | None = field(default=None, init=False)
    _memory_lifecycle: MemoryLifecycle | None = field(default=None, init=False)
    _memory_retriever: DefaultMemoryRetriever | None = field(default=None, init=False)
    _agent_orchestrator: AgentOrchestrator | None = field(default=None, init=False)
    _tool_registry: ToolRegistry | None = field(default=None, init=False)
    _tool_executor: ToolExecutor | None = field(default=None, init=False)
    _research_pipeline: ResearchPipeline | None = field(default=None, init=False)
    _agentic_llm_provider: LLMProvider | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()
        self._apply_saved_llama_profiles()
        self.logger = self.logger or configure_logging(self.settings)
        self.settings.storage_path_resolved.mkdir(parents=True, exist_ok=True)
        self.settings.database_path_resolved.parent.mkdir(parents=True, exist_ok=True)
        if self.database_engine is None:
            self.database_engine = DatabaseEngine(DatabaseConfig.from_settings(self.settings))
            self.database_engine.ensure_ready()
        if self.llm_provider_registry is None:
            registry = LLMProviderRegistry()
            registry.register("openai_compatible", OpenAICompatibleLLMProvider)
            registry.register("llama_cpp", LlamaCppLLMProvider)
            self.llm_provider_registry = registry
        if self.llm_provider is None:
            self.llm_provider = self.llm_provider_registry.create(self.settings.llm_provider, settings=self.settings)
        self._resolve_llm_runtime()
        if self.embedding_provider is None:
            self.embedding_provider = LlamaCppEmbeddingProvider(self.settings)
        if self.reranker_provider is None:
            self.reranker_provider = LlamaCppRerankerProvider(self.settings)
        if self.web_provider is None:
            self.web_provider = DefaultWebSearchProvider(api_key=self.settings.provider_api_key, search_url=self.settings.web_provider_base_url)

    def _apply_saved_llama_profiles(self) -> None:
        """Make API providers consume the same profiles used by EngineManager."""
        assert self.settings is not None
        path = self.settings.storage_path_resolved / "llama_profiles.json"
        if not path.exists():
            return
        try:
            profiles = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(profiles, dict):
            return

        for role, base_attr, model_attr, default_port in (
            ("llm", "llm_base_url", "llm_model_id", 8080),
            ("embedding", "embedding_base_url", "embedding_model_id", 8081),
            ("reranker", "reranker_base_url", "reranker_model_id", 8082),
        ):
            profile = profiles.get(role)
            if not isinstance(profile, dict):
                continue
            options = profile.get("options") if isinstance(profile.get("options"), dict) else {}
            host = str(options.get("host") or "127.0.0.1").strip()
            try:
                port = int(options.get("port") or default_port)
            except (TypeError, ValueError):
                port = default_port
            if not 1 <= port <= 65535:
                port = default_port
            if host in {"0.0.0.0", "::"}:
                host = "127.0.0.1"
            if host.startswith(("http://", "https://")):
                base_url = f"{host.rstrip('/')}:{port}"
            else:
                base_url = f"http://{host}:{port}"
            setattr(self.settings, base_attr, base_url)
            alias = str(options.get("alias") or "").strip()
            if alias:
                setattr(self.settings, model_attr, alias)

        llm_profile = profiles.get("llm")
        if isinstance(llm_profile, dict) and str(llm_profile.get("model_path") or "").strip():
            self.settings.llm_provider = "llama_cpp"

    def _resolve_llm_runtime(self) -> None:
        """Resolve model/provider/policy limits once and inject them into the LLM adapter."""
        assert self.settings is not None
        assert self.llm_provider is not None
        provider_capabilities = self.llm_provider.capabilities()
        model_id = self.settings.llm_model_id
        if model_id:
            registry = ModelCapabilityRegistry()
            policy = CapabilityPolicy(registry, require_verified=self.settings.require_verified_capabilities, tools_enabled=self.settings.tools_enabled, structured_output_enabled=self.settings.structured_output_enabled)
            policy.register_model(model_id, provider_capabilities, overrides=self.settings.model_capability_overrides.get(model_id, {}))
            effective = policy.effective(model_id, provider_capabilities)
            runtime = ModelRuntimeConfig.from_effective_capabilities(effective, temperature=self.settings.llm_temperature, top_p=self.settings.llm_top_p, timeout_seconds=self.settings.provider_total_timeout_seconds, fallback_context_window_tokens=self.settings.context_window_tokens, fallback_max_output_tokens=self.settings.llm_max_output_tokens)
            self.effective_capabilities = effective
        else:
            runtime = self.settings.model_runtime_config()
            self.effective_capabilities = EffectiveCapabilities(model_id=runtime.model_id or "unidentified", **provider_capabilities.model_dump(exclude={"context_window_tokens", "max_output_tokens"}), context_window_tokens=runtime.context_window_tokens, max_output_tokens=runtime.max_output_tokens)
        self.runtime_config = runtime
        configure_runtime = getattr(self.llm_provider, "configure_runtime", None)
        if callable(configure_runtime):
            configure_runtime(runtime)

    @property
    def source_repository(self) -> SqliteSourceRepository:
        if self._source_repository is None: self._source_repository = SqliteSourceRepository(self.database_engine)
        return self._source_repository

    @property
    def document_repository(self) -> SqliteDocumentRepository:
        if self._document_repository is None: self._document_repository = SqliteDocumentRepository(self.database_engine)
        return self._document_repository

    @property
    def document_version_repository(self) -> SqliteDocumentVersionRepository:
        if self._document_version_repository is None: self._document_version_repository = SqliteDocumentVersionRepository(self.database_engine)
        return self._document_version_repository

    @property
    def chunk_repository(self) -> SqliteChunkRepository:
        if self._chunk_repository is None: self._chunk_repository = SqliteChunkRepository(self.database_engine)
        return self._chunk_repository

    @property
    def embedding_repository(self) -> SqliteEmbeddingRepository:
        if self._embedding_repository is None: self._embedding_repository = SqliteEmbeddingRepository(self.database_engine)
        return self._embedding_repository

    @property
    def knowledge_repository(self) -> SqliteKnowledgeRepository:
        if self._knowledge_repository is None: self._knowledge_repository = SqliteKnowledgeRepository(self.database_engine)
        return self._knowledge_repository

    @property
    def tag_repository(self) -> SqliteTagRepository:
        if self._tag_repository is None: self._tag_repository = SqliteTagRepository(self.database_engine)
        return self._tag_repository

    @property
    def memory_repository(self) -> SqliteMemoryRepository:
        if self._memory_repository is None: self._memory_repository = SqliteMemoryRepository(self.database_engine)
        return self._memory_repository

    @property
    def execution_repository(self) -> SqliteExecutionRepository:
        if self._execution_repository is None: self._execution_repository = SqliteExecutionRepository(self.database_engine)
        return self._execution_repository

    @property
    def flashcard_repository(self) -> SqliteFlashcardRepository:
        if self._flashcard_repository is None: self._flashcard_repository = SqliteFlashcardRepository(self.database_engine)
        return self._flashcard_repository

    @property
    def review_repository(self) -> SqliteReviewRepository:
        if self._review_repository is None: self._review_repository = SqliteReviewRepository(self.database_engine)
        return self._review_repository

    @property
    def ingestion_pipeline(self) -> DocumentIngestionPipeline:
        if self._ingestion_pipeline is None: self._ingestion_pipeline = DocumentIngestionPipeline(source_repository=self.source_repository, document_repository=self.document_repository, document_version_repository=self.document_version_repository, chunk_repository=self.chunk_repository, embedding_repository=self.embedding_repository, knowledge_repository=self.knowledge_repository, tag_repository=self.tag_repository, embedding_provider=self.embedding_provider, database_engine=self.database_engine)
        return self._ingestion_pipeline

    @property
    def dense_retriever(self) -> DenseRetriever:
        if self._dense_retriever is None: self._dense_retriever = SqliteDenseRetriever(self.database_engine)
        return self._dense_retriever

    @property
    def lexical_retriever(self) -> LexicalRetriever:
        if self._lexical_retriever is None: self._lexical_retriever = SqliteLexicalRetriever(self.database_engine)
        return self._lexical_retriever

    @property
    def candidate_fusion(self) -> CandidateFusion:
        if self._candidate_fusion is None: self._candidate_fusion = ReciprocalRankFusion()
        return self._candidate_fusion

    @property
    def hybrid_retriever(self) -> HybridRetriever:
        if self._hybrid_retriever is None: self._hybrid_retriever = HybridRetriever(embedding_provider=self.embedding_provider, dense_retriever=self.dense_retriever, lexical_retriever=self.lexical_retriever, fusion=self.candidate_fusion, reranker_provider=self.reranker_provider)
        return self._hybrid_retriever

    @property
    def context_engine(self) -> ContextEngine:
        if self._context_engine is None: self._context_engine = ContextEngine()
        return self._context_engine

    @property
    def agent_router(self) -> AgentRouter:
        if self._agent_router is None: self._agent_router = AgentRouter()
        return self._agent_router

    @property
    def agent_planner(self) -> AgentPlanner:
        if self._agent_planner is None: self._agent_planner = AgentPlanner()
        return self._agent_planner

    @property
    def agent_critic(self) -> AgentCritic:
        if self._agent_critic is None: self._agent_critic = AgentCritic(llm_provider=self.llm_provider)
        return self._agent_critic

    @property
    def agent_verifier(self) -> AgentVerifier:
        if self._agent_verifier is None: self._agent_verifier = AgentVerifier()
        return self._agent_verifier

    @property
    def memory_extractor(self) -> MemoryExtractor:
        if self._memory_extractor is None: self._memory_extractor = MemoryExtractor()
        return self._memory_extractor

    @property
    def memory_consolidator(self) -> MemoryConsolidator:
        if self._memory_consolidator is None: self._memory_consolidator = MemoryConsolidator()
        return self._memory_consolidator

    @property
    def memory_lifecycle(self) -> MemoryLifecycle:
        if self._memory_lifecycle is None: self._memory_lifecycle = MemoryLifecycle(memory_repository=self.memory_repository, extractor=self.memory_extractor, consolidator=self.memory_consolidator)
        return self._memory_lifecycle

    @property
    def memory_retriever(self) -> DefaultMemoryRetriever:
        if self._memory_retriever is None: self._memory_retriever = DefaultMemoryRetriever(self.memory_repository)
        return self._memory_retriever

    @property
    def tool_registry(self) -> ToolRegistry:
        if self._tool_registry is None:
            registry = ToolRegistry()
            registry.register(CalculatorTool())
            registry.register(TimeTool())
            registry.register(WebSearchTool(provider=self.web_provider))
            registry.register(WebFetchTool())
            registry.register(KnowledgeSearchTool(self.hybrid_retriever))
            registry.register(MemoryWriteTool(self.memory_repository))
            registry.register(MemorySearchTool(self.memory_repository))
            self._tool_registry = registry
        return self._tool_registry

    @property
    def tool_executor(self) -> ToolExecutor:
        if self._tool_executor is None: self._tool_executor = ToolExecutor(registry=self.tool_registry)
        return self._tool_executor

    @property
    def agentic_llm_provider(self) -> LLMProvider:
        if self._agentic_llm_provider is None: self._agentic_llm_provider = AgenticLLMProvider(inner=self.llm_provider, registry=self.tool_registry, executor=self.tool_executor, settings=self.settings, runtime_config=self.runtime_config)
        return self._agentic_llm_provider

    @property
    def research_pipeline(self) -> ResearchPipeline:
        if self._research_pipeline is None: self._research_pipeline = ResearchPipeline(executor=self.tool_executor)
        return self._research_pipeline

    @property
    def agent_orchestrator(self) -> AgentOrchestrator:
        if self._agent_orchestrator is None: self._agent_orchestrator = AgentOrchestrator(llm_provider=self.agentic_llm_provider, router=self.agent_router, planner=self.agent_planner, hybrid_retriever=self.hybrid_retriever, memory_retriever=self.memory_retriever, tool_executor=self.tool_executor, research_pipeline=self.research_pipeline, context_engine=self.context_engine, critic=self.agent_critic, verifier=self.agent_verifier, memory_lifecycle=self.memory_lifecycle, execution_repository=self.execution_repository, memory_repository=self.memory_repository, runtime_config=self.runtime_config)
        return self._agent_orchestrator
