# BidGuard AI MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working full-stack BidGuard AI MVP.

**Architecture:** FastAPI owns parsing, persistence, retrieval, risk checks, diffing, and agent traces. Next.js owns the portfolio UI and calls the backend through `NEXT_PUBLIC_API_URL`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, PyMuPDF, SQLite/PostgreSQL, Next.js App Router, TypeScript, Tailwind CSS.

---

### Task 1: Backend Core

**Files:** `backend/app`, `backend/tests`

- [x] Write failing tests for chunking, retrieval, risk rules, field diff, health, upload error, seed endpoint, and agent trace logging.
- [x] Implement SQLAlchemy models and FastAPI app factory.
- [x] Implement PDF parsing, chunking, retrieval, risk rules, field extraction, diff, and agent services.
- [x] Run `backend/.venv/bin/python -m pytest tests -q`.

### Task 2: Frontend MVP

**Files:** `frontend/app`, `frontend/components`, `frontend/lib`

- [x] Create Next.js App Router project files.
- [x] Implement dashboard, documents, Q&A, risk review, compare, and trace pages.
- [x] Add a typed API wrapper and shared UI components.
- [x] Run `npm run typecheck`.

### Task 3: Documentation and Setup

**Files:** `README.md`, `docs`, `docker-compose.yml`, `backend/alembic`

- [x] Add environment examples, PostgreSQL compose service, pgvector init script, and Alembic metadata.
- [x] Document architecture, database design, agent workflow, evaluation plan, and roadmap.
- [ ] Run final backend and frontend verification commands.
