from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ChunkingResult:
    chunk_index: int
    content: str
    token_count: int
    character_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


class TextChunker:
    """Deterministic text chunker supporting configurable size and overlap."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        return normalized

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        words = text.split()
        if not words:
            return 0
        return max(1, len(words))

    def chunk_text(self, text: str, base_metadata: dict[str, Any] | None = None) -> list[ChunkingResult]:
        normalized = self.normalize_text(text)
        if not normalized:
            return []

        base_meta = base_metadata.copy() if base_metadata else {}
        total_len = len(normalized)

        if total_len <= self.chunk_size:
            return [
                ChunkingResult(
                    chunk_index=0,
                    content=normalized,
                    token_count=self.estimate_tokens(normalized),
                    character_count=total_len,
                    metadata={
                        **base_meta,
                        "start_char": 0,
                        "end_char": total_len,
                    },
                )
            ]

        results: list[ChunkingResult] = []
        step = self.chunk_size - self.chunk_overlap
        start = 0
        chunk_idx = 0

        while start < total_len:
            end = min(start + self.chunk_size, total_len)

            if end < total_len:
                window = int(self.chunk_size * 0.2)
                best_end = end
                for pos in range(end, max(start + step, end - window), -1):
                    if normalized[pos - 1] in {"\n", ".", " ", "?", "!"}:
                        best_end = pos
                        break
                end = best_end

            chunk_content = normalized[start:end].strip()
            if chunk_content:
                results.append(
                    ChunkingResult(
                        chunk_index=chunk_idx,
                        content=chunk_content,
                        token_count=self.estimate_tokens(chunk_content),
                        character_count=len(chunk_content),
                        metadata={
                            **base_meta,
                            "start_char": start,
                            "end_char": end,
                        },
                    )
                )
                chunk_idx += 1

            if end >= total_len:
                break

            next_start = end - self.chunk_overlap
            if next_start <= start:
                next_start = start + step
            start = next_start

        return results
