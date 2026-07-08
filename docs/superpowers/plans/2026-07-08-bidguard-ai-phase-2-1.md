# BidGuard AI Phase 2.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add evidence-first RAG with embeddings, guarded synthesis, trace metadata, and a small evaluation runner.

**Architecture:** Backend providers generate embeddings and optional LLM synthesis behind environment-controlled abstractions. SQLite remains fully supported through JSON embedding fallback retrieval; PostgreSQL gets pgvector DDL/migration support.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, httpx, SQLite/PostgreSQL, pgvector, Next.js App Router, TypeScript, Tailwind CSS.

---

### Task 1: Backend RAG Services

- [x] Add failing tests for deterministic embedding fallback, embedding storage, hybrid retrieval metadata, guarded synthesis fallback, agent tool logging, and eval metrics.
- [x] Implement embedding provider abstraction.
- [x] Implement LLM provider abstraction and guarded synthesis.
- [x] Update ingestion to embed chunks and fail clearly on embedding errors.
- [x] Update retrieval to return similarity, method, and hybrid scores.
- [x] Update agent workflow to log synthesis as a tool call.

### Task 2: Storage And PostgreSQL Support

- [x] Add chunk embedding metadata columns.
- [x] Add PostgreSQL pgvector init/migration support without making SQLite depend on pgvector.
- [x] Keep startup `create_all` compatible with SQLite.

### Task 3: Evaluation

- [x] Add JSON sample eval cases.
- [x] Add `python -m app.evaluation.run_eval` command.
- [x] Add tests for eval metrics.

### Task 4: Frontend And Docs

- [x] Update Q&A evidence display with retrieval method, similarity score, and synthesis state.
- [x] Update agent trace summaries with evidence counts and success/failure metadata.
- [x] Update README and project docs.
- [x] Run backend tests, Ruff, frontend typecheck, and frontend build.
