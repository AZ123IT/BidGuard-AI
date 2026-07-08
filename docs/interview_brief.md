# BidGuard AI Interview Brief

## Positioning

BidGuard AI is an evidence-first tender and contract document review agent. It is a portfolio-level AI engineering project, not an enterprise SaaS product and not a legal-advice product.

It helps a user upload tender or contract documents, retrieve page-level evidence, answer document questions, run deterministic procurement risk checks, compare two document versions, and inspect the agent tool trace behind each review.

## 30-Second Explanation

BidGuard AI is an evidence-first RAG app for reviewing tender and contract documents. It parses uploaded PDFs, stores page-aware chunks, answers questions with citations, refuses unsupported questions, runs deterministic procurement risk checks, compares draft changes, and logs agent tool calls. The project demonstrates full-stack AI engineering rather than legal advice: FastAPI, Next.js, SQLAlchemy, SQLite fallback, PostgreSQL pgvector, provider abstractions, guarded LLM synthesis, and evaluation coverage.

## 2-Minute Technical Explanation

The system starts with document ingestion. A PDF is parsed with PyMuPDF, chunked with page metadata, embedded through either a local deterministic provider or an OpenAI-compatible provider, and stored in the database. SQLite is the default path and stores JSON embeddings for easy local demos. PostgreSQL adds a pgvector column for a more realistic vector retrieval path.

At query time, BidGuard AI retrieves relevant chunks and applies an evidence sufficiency gate. If evidence is weak or empty, it returns the fixed insufficient-evidence sentence and does not call the LLM. If evidence is sufficient, guarded synthesis answers only from the retrieved snippets and preserves citations. The agent layer stays intentionally lightweight: it routes to evidence search, risk rule checking, cross-document diff, or report generation, then stores traceable tool calls.

The project also includes an evaluation story. There is a smoke eval, an 18-case synthetic demo eval, provider smoke validation, pgvector smoke validation, and a root verification command. Metrics cover retrieval hit, evidence page hit, insufficient-evidence correctness, answer keywords, risk categories, diff fields, tool-call correctness, provider mode, database mode, and retrieval method.

## Problem

Tender and contract review often requires checking the same facts across long documents: payment terms, bid deadlines, acceptance criteria, liability wording, dispute resolution, and changed clauses between drafts. A generic PDF chatbot can answer some questions, but it often hides retrieval quality, misses deterministic checks, and can fabricate unsupported citations.

BidGuard AI is built around the opposite constraint: every answer should be grounded in retrieved document evidence, and unsupported questions should be refused with a clear fallback.

## Why It Is Not Just a PDF Chatbot

- It stores page-aware chunks and returns document title, page number, score, retrieval method, and snippets with answers.
- It has a guarded synthesis path that skips LLM generation when evidence is weak or missing.
- It includes deterministic risk tools for common procurement review issues.
- It compares extracted fields and clauses across two documents.
- It logs agent runs and tool calls for traceability.
- It includes smoke tests and eval datasets for retrieval, insufficient evidence, risk rules, diff, and routing behavior.

## Architecture

```mermaid
flowchart TD
  UI["Next.js frontend"] --> API["FastAPI API"]
  API --> Upload["Document upload"]
  Upload --> Parser["PDF/text parser"]
  Parser --> Chunker["Page-aware chunker"]
  Chunker --> Embed["Embedding provider"]
  Embed --> Store["document_chunks"]
  Store --> SQLite["SQLite JSON embedding fallback"]
  Store --> PG["PostgreSQL + pgvector"]
  SQLite --> Retrieval["Hybrid retrieval"]
  PG --> Retrieval
  Retrieval --> Guard["Evidence sufficiency gate"]
  Guard -->|sufficient| LLM["Guarded LLM synthesis"]
  Guard -->|insufficient| Refusal["Exact fallback response"]
  LLM --> Evidence["Answer with citations"]
  Refusal --> Evidence
  API --> Agent["Tool-calling agent"]
  Agent --> Tools["Evidence search / risk check / diff"]
  Tools --> Trace["Agent runs + tool calls"]
  Eval["Eval runner + smoke scripts"] --> API
  Eval --> Embed
```

## RAG Pipeline

1. Parse uploaded PDF or seeded text into page-level text.
2. Chunk text while preserving document id, title, page number, and chunk index.
3. Generate embeddings through either local deterministic embeddings or an OpenAI-compatible provider.
4. Store chunks and JSON embeddings in SQLite by default.
5. In PostgreSQL mode, also store `embedding_vector` for pgvector retrieval.
6. Retrieve evidence with hybrid scoring and return score metadata.
7. Run guarded synthesis only if retrieved evidence passes the sufficiency gate.
8. Return answer, evidence snippets, document title, page number, score, retrieval method, and synthesis metadata.

## Evidence-First Design

The system returns this exact sentence when evidence is weak or empty:

```text
The uploaded documents do not contain enough evidence to answer this question reliably.
```

The backend skips LLM synthesis in that case. This is the trust boundary: model output is allowed only after retrieval has produced enough cited evidence.

## Provider Abstraction

- Local mode: `EMBEDDING_PROVIDER=local`, `LLM_PROVIDER=local_fake`. This is deterministic, zero-key, and test-friendly.
- Real mode: `EMBEDDING_PROVIDER=openai_compatible`, `LLM_PROVIDER=openai_compatible`. This is optional and validated through `backend/scripts/smoke_providers.py`.
- Missing real-provider keys are reported as `skipped`, not as test failures.
- Embedding dimension mismatches fail clearly before a misleading pgvector demo.

## Storage Paths

SQLite is the default fallback. It stores embeddings as JSON and uses Python-side hybrid retrieval, which keeps the project easy to run locally.

PostgreSQL + pgvector is the realistic RAG path. It stores `embedding_vector`, verifies `vector(64)` in local deterministic mode, and reports `retrieval_method: "pgvector"` during smoke tests.

## Agent Workflow

The agent is intentionally lightweight:

- Normal document questions call `evidence_search_tool`.
- Risk review requests call `risk_rule_check_tool`.
- Compare requests call `cross_doc_diff_tool`.
- Report-style requests can use the report generator.
- Every run stores tool calls, status, latency, and output summaries for trace inspection.

## Evaluation Design

The eval runner covers:

- answerable evidence Q&A,
- insufficient-evidence refusal,
- deterministic risk rules,
- cross-document diff,
- agent routing/tool-call correctness.

Current metrics include retrieval hit, evidence page hit, answer keyword hit, insufficient-evidence correctness, risk category/keyword hit, diff field/keyword hit, tool-call correctness, average score, provider mode, database mode, and observed retrieval methods.

## PostgreSQL + pgvector Story

The pgvector path is there to show that the project can move beyond toy local search. In PostgreSQL mode, chunks keep their JSON embedding metadata and also populate `embedding_vector`. The smoke script verifies the extension, vector column type, stored vector count, answerable retrieval, `retrieval_method: "pgvector"`, and the exact insufficient-evidence fallback.

## Local Fallback Story

SQLite mode is intentionally retained because it makes the project easy to run on any laptop without Docker or API keys. It uses local deterministic embeddings and hybrid retrieval, which is stable for tests and demos. It is clearly documented as a fallback, not as a claim of production-grade semantic retrieval.

## Feature Matrix

| Feature | Status | Notes |
| --- | --- | --- |
| PDF upload | Implemented | FastAPI upload endpoint and frontend document page. |
| TXT/demo document seeding | Implemented | Used by eval runner for repeatable demo data. |
| Document parsing | Implemented | PyMuPDF for PDFs; seeded text path for eval/demo. |
| Page-aware chunking | Implemented | Chunks preserve document id and page number. |
| Local embeddings | Fallback/local | Deterministic hash vectors for tests and no-key demos. |
| OpenAI-compatible embeddings | Optional real provider | Validated by provider smoke when env vars are set. |
| SQLite retrieval | Fallback/local | JSON embeddings plus hybrid retrieval. |
| PostgreSQL pgvector retrieval | Implemented | Smoke script verifies pgvector path. |
| Guarded LLM synthesis | Implemented | Skipped when evidence is insufficient. |
| OpenAI-compatible LLM | Optional real provider | Validated by provider smoke when env vars are set. |
| Risk review | Implemented | Rule-based procurement checks. |
| Cross-document diff | Implemented | Regex field extraction plus structured diff rows. |
| Agent trace | Implemented | Tool calls and runs are logged. |
| Evaluation runner | Implemented | Smoke and demo eval datasets. |
| Provider smoke | Implemented | Local pass, real-provider skip/pass, dimension check. |
| OCR | Future | Intentionally not part of the current phase. |
| PDF evidence highlighting | Future | Evidence snippets exist; visual highlight anchors are future work. |
| Complex SaaS features | Out of scope | No payments, tenants, approvals, or complex roles. |

## Resume Bullets

- Built a full-stack evidence-first RAG application with FastAPI, Next.js, SQLAlchemy, SQLite fallback, and PostgreSQL pgvector retrieval.
- Implemented guarded LLM synthesis that only answers from retrieved page-level evidence and returns a deterministic insufficient-evidence fallback when support is weak.
- Designed a lightweight tool-calling agent workflow for evidence search, rule-based risk review, cross-document diff, report generation, and trace logging.
- Added provider abstractions and smoke validation for deterministic local providers and optional OpenAI-compatible embedding/LLM providers.
- Created an evaluation runner and synthetic tender/contract dataset covering retrieval, refusal behavior, risk findings, diff accuracy, and agent routing.

## Current Limitations

- Local embeddings are deterministic hash vectors, not semantic embeddings.
- SQLite retrieval is a local fallback, not production vector search.
- Field extraction is regex-based and intentionally simple.
- Risk rules are deterministic checks, not legal analysis.
- OCR and PDF visual highlighting are not implemented yet.
- Real provider validation requires user-supplied API credentials in environment variables.

## Possible Interview Q&A

**Why not just call an LLM over the whole PDF?**
The goal is traceability. BidGuard AI retrieves page-level evidence first, exposes snippets and scores, and refuses unsupported questions instead of relying on hidden prompt context.

**How do you prevent fabricated citations?**
The backend only returns citations from retrieved chunks. If evidence is weak or empty, it skips synthesis and returns the fixed fallback sentence.

**Why keep SQLite if pgvector exists?**
SQLite keeps the demo zero-config and test-friendly. PostgreSQL + pgvector remains available for the realistic vector path.

**What does the agent actually do?**
It is a lightweight router over real tools: evidence search, risk rule check, cross-document diff, and report generation. It is not an overbuilt multi-agent system.

**What would you improve next?**
I would validate a real provider, add public tender PDFs, add CI pgvector tests, improve field extraction with layout/table parsing, and add PDF evidence highlighting later.

## What I Would Improve Next

- Validate a real embedding model and real LLM provider with non-secret local env vars.
- Add public tender PDFs and more realistic eval cases.
- Add CI coverage for PostgreSQL + pgvector.
- Improve field extraction with layout-aware table parsing.
- Add PDF page preview and evidence highlight anchors.
- Add optional OCR as an isolated worker for scanned PDFs.
