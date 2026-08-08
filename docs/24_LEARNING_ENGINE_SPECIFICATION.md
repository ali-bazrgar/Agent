# Phase 10 — Learning Intelligence, Spaced Repetition & Knowledge Graph Foundation Specification

## Overview
Phase 10 introduces the **Learning Intelligence Engine** to SuperAgent, transforming it from a retrieval and research assistant into an active learning system. It incorporates spaced repetition scheduling (FSRS/SM-2 compatible), flashcard generation with rigorous provenance tracking, knowledge relationship graphing, and learning-aware context integration.

## Architecture
- **Domain Separation**: Learning items and flashcards are maintained strictly separate from short/long-term memory records, connected via domain ports and well-defined repositories.
- **Spaced Repetition Scheduler (`SpacedRepetitionScheduler`)**: Deterministic scheduling algorithm supporting `AGAIN`, `HARD`, `GOOD`, and `EASY` reviews, calculating stability, difficulty, interval days, and due dates.
- **Extraction & Generation (`FlashcardExtractor`)**: Automatically extracts atomic knowledge from ingested documents and chunks with preserved provenance.
- **Knowledge Relationships**: Lightweight relationship mapping (`RELATED_TO`, `PREREQUISITE_OF`, `PART_OF`, `CONTRASTS_WITH`, `EXAMPLE_OF`, `DERIVED_FROM`) stored in SQLite.
- **API & Persistence**: RESTful endpoints for reviewing due cards (`GET /api/v1/learning/review`, `POST /api/v1/learning/review`), statistics (`GET /api/v1/learning/stats`), and card creation.
