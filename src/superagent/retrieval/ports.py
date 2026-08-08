from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from superagent.retrieval.models import RetrievalCandidate, RetrievalFilter


class DenseRetriever(ABC):
    """Abstraction for vector similarity retrieval."""

    @abstractmethod
    def retrieve_dense(
        self,
        query_vector: list[float],
        top_k: int,
        filters: RetrievalFilter | None = None,
    ) -> list[RetrievalCandidate]: ...


class LexicalRetriever(ABC):
    """Abstraction for full-text (FTS5) lexical retrieval."""

    @abstractmethod
    def retrieve_lexical(
        self,
        query_text: str,
        top_k: int,
        filters: RetrievalFilter | None = None,
    ) -> list[RetrievalCandidate]: ...


class CandidateFusion(ABC):
    """Abstraction for combining multiple retrieval candidate streams."""

    @abstractmethod
    def fuse_candidates(
        self,
        dense_candidates: Sequence[RetrievalCandidate],
        lexical_candidates: Sequence[RetrievalCandidate],
        top_k: int,
    ) -> list[RetrievalCandidate]: ...
