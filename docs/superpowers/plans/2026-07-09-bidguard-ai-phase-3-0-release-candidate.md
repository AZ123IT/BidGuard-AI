# BidGuard AI Phase 3.0 Release Candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make BidGuard AI GitHub-ready, resume-ready, and interview-demo-ready in one release-candidate pass.

**Architecture:** Keep the existing evidence-first RAG architecture intact. Add only lightweight backend contract data needed by the current UI, polish the existing Next.js pages, add a minimal no-secret CI workflow, and align documentation with verified behavior.

**Tech Stack:** FastAPI, SQLAlchemy, Next.js, TypeScript, Tailwind CSS, GitHub Actions, existing verification scripts.

---

### Task 1: Checkpoint And Hygiene

**Files:**
- Commit existing Phase 2 documentation.
- Inspect: `.gitignore`, env examples, `docker-compose.yml`, verification scripts, README, docs.

- [x] **Step 1: Review current status**

Run:

```bash
git status --short --ignored
git diff --check
```

- [x] **Step 2: Commit stable Phase 2 work**

Run:

```bash
git add README.md docs
git commit -m "Finalize Phase 2 portfolio readiness"
```

### Task 2: Document Detail Contract

**Files:**
- Modify: `backend/app/api/routes.py`
- Modify: `backend/tests/test_api.py`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/app/documents/[id]/page.tsx`

- [x] **Step 1: Write backend failing test**

Add a test proving `/api/documents/{id}` returns ordered chunks with `id`, `chunk_index`, `page_number`, `text`, `token_count`, and embedding metadata.

- [x] **Step 2: Run test and confirm failure**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_api.py::test_document_detail_returns_chunks_for_evidence_review -q
```

- [x] **Step 3: Implement chunk preview in document detail**

Add a `chunks` list to `_document_detail(document)` sorted by page and chunk index. Do not expose embedding vectors.

- [x] **Step 4: Run test and confirm pass**

Run the same test command.

### Task 3: Frontend Evidence And Trace Polish

**Files:**
- Modify: `frontend/components/EvidenceList.tsx`
- Modify: `frontend/app/qa/page.tsx`
- Modify: `frontend/app/documents/[id]/page.tsx`
- Modify: `frontend/app/agent-trace/page.tsx`

- [x] **Step 1: Improve evidence cards**

Show document title, page number, chunk id, score, similarity score, keyword score, retrieval method, and link to `/documents/{id}?page={page}&chunk={chunk_id}`.

- [x] **Step 2: Improve document detail**

Show filename, status, page count, chunk count, embedding status, extracted fields with confidence/evidence, and chunks grouped by page. Highlight selected chunk from query params.

- [x] **Step 3: Improve agent trace readability**

Show final answer summary, run status, latency, tool calls in order, status, evidence count, retrieval method, and compact input/output summaries.

### Task 4: CI And Documentation Polish

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `docs/demo_walkthrough.md`
- Modify: `docs/interview_brief.md`
- Modify: `docs/architecture.md`
- Modify: `docs/evaluation_plan.md`
- Modify: `docs/development_roadmap.md`
- Modify: `docs/database_design.md`
- Modify: `docs/agent_workflow.md`
- Modify: `docs/release_notes_v0_1.md`

- [x] **Step 1: Add no-secret CI workflow**

Run backend tests, backend Ruff, frontend typecheck, and frontend build with local deterministic defaults. Keep pgvector CI documented as future work.

- [x] **Step 2: README final polish**

Make the README concise and GitHub-ready: overview, features, tech stack, RAG pipeline, agent workflow, local fallback, pgvector, provider modes, eval coverage, quick start, verification, demo, safe push, limitations, roadmap.

- [x] **Step 3: Demo and interview docs**

Add copy-paste demo flow, specific questions, interview pitch, technical explanation, evaluation story, limitations, and resume bullets.

- [x] **Step 4: Align architecture/eval/database/agent docs**

Remove stale phase language, avoid overclaims, and clearly separate implemented, local fallback, optional real-provider, and future work.

### Task 5: Final Verification

**Files:**
- No source changes after this task unless a verified blocker is found.

- [x] **Step 1: Run aggregate verification**

```bash
python3 scripts/verify_all.py
```

- [x] **Step 2: Run individual backend and frontend checks**

```bash
cd backend
.venv/bin/python -m pytest tests -q
.venv/bin/ruff check .
.venv/bin/python scripts/smoke_providers.py
.venv/bin/python -m app.evaluation.run_eval
.venv/bin/python -m app.evaluation.run_eval --dataset ../data/eval_cases/rag_demo.json

cd ../frontend
npm run typecheck
npm run build
```

- [x] **Step 3: Run pgvector smoke if Docker daemon is available**

```bash
docker compose up -d postgres

cd backend
DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard EMBEDDING_PROVIDER=local EMBEDDING_DIMENSION=64 LLM_PROVIDER=local_fake .venv/bin/python scripts/smoke_pgvector.py

cd ..
docker compose stop postgres
```

- [x] **Step 4: Run release hygiene**

```bash
git diff --check
git status --short --ignored
rg -n "(sk-[A-Za-z0-9_-]{20,}|api[_-]?key\\s*=\\s*['\\\"][^'\\\"]{12,}|Bearer\\s+[A-Za-z0-9._-]{20,}|-----BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY-----)" README.md backend docs frontend scripts data/eval_cases data/sample_docs || true
```
