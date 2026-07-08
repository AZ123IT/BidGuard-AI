# BidGuard AI Phase 2.5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make BidGuard AI portfolio-ready with a repeatable verification command and interview-focused documentation.

**Architecture:** Add a root verification script that orchestrates existing backend, frontend, eval, provider, and optional pgvector checks without changing app runtime behavior. Add documentation that explains the already-implemented architecture, demo flow, feature matrix, and interview narrative without adding product features.

**Tech Stack:** Python 3.11+, FastAPI backend test commands, Next.js frontend npm commands, Docker Compose for optional PostgreSQL pgvector smoke.

---

### Task 1: Verification Script

**Files:**
- Create: `scripts/verify_all.py`
- Test: `backend/tests/test_verify_all_script.py`

- [ ] **Step 1: Write failing test**

```python
def test_verify_all_default_plan_lists_required_checks():
    module = load_verify_all_module()
    plan = module.build_plan(with_pgvector=False)
    labels = [step.label for step in plan]
    assert labels == [
        "backend tests",
        "backend Ruff",
        "provider smoke",
        "smoke eval",
        "demo eval",
        "frontend typecheck",
        "frontend build",
    ]
```

- [ ] **Step 2: Run failing test**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verify_all_script.py -q`

Expected: FAIL because `scripts/verify_all.py` does not exist yet.

- [ ] **Step 3: Implement script**

Create `scripts/verify_all.py` with `build_plan(with_pgvector: bool)`, `run_step`, and `main`. Default plan runs backend tests, Ruff, provider smoke, smoke eval, demo eval, frontend typecheck, and frontend build. `--with-pgvector` adds Docker Compose start, pgvector smoke, and Docker Compose stop.

- [ ] **Step 4: Verify script tests pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verify_all_script.py -q`

Expected: PASS.

### Task 2: Interview Documentation

**Files:**
- Create: `docs/interview_brief.md`
- Modify: `README.md`
- Modify: `docs/demo_walkthrough.md`
- Modify: `docs/architecture.md`

- [ ] **Step 1: Add interview brief**

Include positioning, problem, why it is not just a PDF chatbot, architecture, RAG pipeline, evidence-first design, provider abstraction, pgvector path, SQLite fallback, agent workflow, eval design, metrics, limitations, improvements, feature matrix, and resume bullets.

- [ ] **Step 2: Polish README**

Add recruiter-friendly overview, verification command, concise feature matrix, and links to the interview brief and demo walkthrough.

- [ ] **Step 3: Update demo and architecture docs**

Keep commands copy-pasteable and add a readable Mermaid diagram showing frontend, FastAPI, ingestion, retrieval, guarded synthesis, citations, agent trace, and eval runner.

### Task 3: Verification

**Files:**
- No new code files.

- [ ] **Step 1: Run backend checks**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests -q
.venv/bin/ruff check .
.venv/bin/python scripts/smoke_providers.py
.venv/bin/python -m app.evaluation.run_eval
.venv/bin/python -m app.evaluation.run_eval --dataset ../data/eval_cases/rag_demo.json
```

- [ ] **Step 2: Run frontend checks**

Run:

```bash
cd frontend
npm run typecheck
npm run build
```

- [ ] **Step 3: Run aggregate verification script**

Run: `python3 scripts/verify_all.py`

- [ ] **Step 4: Run pgvector smoke if Docker is available**

Run:

```bash
docker compose up -d postgres
cd backend
DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard EMBEDDING_PROVIDER=local EMBEDDING_DIMENSION=64 LLM_PROVIDER=local_fake .venv/bin/python scripts/smoke_pgvector.py
cd ..
docker compose stop postgres
```

- [ ] **Step 5: Hygiene**

Run `git diff --check`, `git status --short --ignored`, and a key-shaped secret scan before reporting.
