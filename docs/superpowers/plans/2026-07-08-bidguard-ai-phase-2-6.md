# BidGuard AI Phase 2.6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare BidGuard AI for GitHub, resume, and interview presentation without adding product scope.

**Architecture:** Keep runtime code unchanged. Polish README and documentation around the already-implemented evidence-first RAG, provider, pgvector, eval, and demo workflows, then run the full verification suite.

**Tech Stack:** Markdown documentation, existing FastAPI/Next.js verification scripts, Docker Compose pgvector smoke.

---

### Task 1: Phase 2.5 Checkpoint

**Files:**
- Commit existing Phase 2.5 files.

- [x] **Step 1: Review status**

Run `git status --short --ignored` and confirm only intended docs/scripts/tests are uncommitted and runtime files are ignored.

- [x] **Step 2: Commit**

Run `git commit -m "Add portfolio verification and interview documentation"`.

### Task 2: Documentation Cleanup

**Files:**
- Modify: `README.md`
- Modify: `docs/demo_walkthrough.md`
- Modify: `docs/interview_brief.md`
- Modify: `docs/development_roadmap.md`
- Create: `docs/release_notes_v0_1.md`

- [ ] **Step 1: README final polish**

Make the README easy to scan for GitHub visitors: overview, project status, features, architecture, tech stack, quick start, verification, demo, eval, providers, pgvector, interview notes, limitations, and roadmap.

- [ ] **Step 2: Demo walkthrough final script**

Add a numbered demo path from backend/frontend startup through upload, answerable Q&A, insufficient evidence, risk review, diff, agent trace, eval, and pgvector smoke.

- [ ] **Step 3: Interview brief cleanup**

Add a 30-second explanation, 2-minute technical explanation, PostgreSQL/local fallback story, and possible interview Q&A.

- [ ] **Step 4: Release notes**

Add a concise `docs/release_notes_v0_1.md` with included features, verification, limitations, and next-phase candidates.

### Task 3: Final Verification

**Files:**
- No new runtime files.

- [ ] **Step 1: Run local verification**

Run `python3 scripts/verify_all.py`.

- [ ] **Step 2: Run individual backend checks**

Run backend tests, Ruff, provider smoke, smoke eval, and demo eval.

- [ ] **Step 3: Run frontend checks**

Run frontend typecheck and build sequentially.

- [ ] **Step 4: Run pgvector smoke if Docker is available**

Run Docker Compose PostgreSQL start, backend pgvector smoke, and Docker Compose PostgreSQL stop.

- [ ] **Step 5: Hygiene**

Run `git diff --check`, `git status --short --ignored`, and key-shaped secret scan before final reporting.
