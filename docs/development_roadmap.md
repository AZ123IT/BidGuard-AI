# Development Roadmap

## MVP Included

- FastAPI backend with health, upload, list, detail, Q&A, risk check, diff, and agent trace endpoints.
- SQLAlchemy schema covering documents, chunks, fields, risk rules, findings, agent runs, tool calls, and eval tables.
- PyMuPDF PDF text extraction.
- Page-aware chunking and deterministic lexical retrieval.
- Built-in risk rules for common procurement review signals.
- Regex field extraction and cross-document comparison.
- Next.js frontend pages for every required workflow.
- Documentation and local setup files.

## Phase 2.1 Included

- Deterministic local embedding provider.
- OpenAI-compatible embedding provider abstraction.
- Chunk embedding storage and metadata.
- SQLite hybrid fallback retrieval.
- PostgreSQL pgvector DDL/migration support.
- Guarded LLM synthesis provider abstraction.
- Agent logging for retrieval and synthesis tools.
- Small JSON eval runner.
- Frontend evidence/trace metadata display.

## Phase 2.2 Included

- PostgreSQL pgvector smoke verification script.
- Safe pgvector init SQL for Docker bootstrap.
- Default pgvector dimension aligned with local deterministic embeddings.
- Eval output with retrieval method, average score, provider mode, and database mode.
- Documentation for SQLite fallback, PostgreSQL pgvector mode, and optional real provider validation.

## Phase 2.3 Included

- Synthetic tender/contract demo pack with five small text documents.
- Expanded `rag_demo.json` eval dataset covering Q&A, insufficient evidence, risk rules, diff, and agent routing.
- Eval runner CLI support for `--dataset` and optional `--output-json`.
- Metric summary for retrieval, evidence page, answer keyword, insufficient-evidence, tool-call, risk, and diff checks.
- Demo walkthrough documentation for interviews.

## Phase 2.4 Included

- Standalone provider smoke validation for local deterministic and OpenAI-compatible providers.
- Clear skip behavior when real provider keys are not configured.
- Clear embedding dimension mismatch, HTTP, timeout, and response-shape errors.
- Documentation for local mode, real provider mode, and PostgreSQL + pgvector real-embedding demos.

## Phase 2.5 Included

- Root verification script for backend tests, Ruff, provider smoke, evals, frontend checks, and optional pgvector smoke.
- Interview brief with architecture summary, feature matrix, limitations, and resume-ready project bullets.
- Demo walkthrough polish for local UI demo, SQLite eval, provider smoke, PostgreSQL pgvector smoke, and optional real-provider validation.
- README portfolio snapshot and recruiter-friendly verification instructions.

## Phase 2.6 Included

- GitHub-facing README structure with quick start, verification, demo workflow, provider modes, pgvector notes, limitations, and roadmap.
- Interview brief cleanup with 30-second explanation, 2-minute technical explanation, and likely interview Q&A.
- Final demo script with answerable Q&A, insufficient-evidence refusal, risk review, diff, agent trace, eval, and pgvector smoke.
- v0.1 release notes summarizing included features, verification, limitations, and next steps.

## Phase 3.0 Release Candidate Included

- Lightweight document detail evidence viewer with extracted fields and page-grouped chunk previews.
- Q&A evidence cards link back to source chunks with page/chunk query parameters.
- Agent trace page readability improvements for final answer, ordered tools, evidence counts, latency, timestamps, and retrieval methods.
- Minimal GitHub Actions CI for backend tests, backend Ruff, frontend typecheck, and frontend build without real API keys.
- README, demo walkthrough, interview brief, architecture, evaluation, database, agent, and release-note cleanup for GitHub/resume readiness.

## Phase 3.5 Real Provider Demo Status

- Added `scripts/real_provider_demo.py` to run provider smoke and then the 18-case demo eval when real OpenAI-compatible embedding and LLM providers are configured.
- Added `docs/real_provider_demo.md` with the current session result and repeatable commands.
- Current local status is skipped because no real provider API keys are configured.

## Phase 4 Product Polish Included

- DOCX upload with lightweight text extraction from `word/document.xml`.
- Markdown review report export from document detail.
- Better regex field extraction for common procurement synonyms such as `Project Title`, `Procuring Entity`, `Vendor`, `Closing date`, `Total contract value`, and `Net 45 days`.

## Next Phase

- Add more realistic public-document eval cases.
- Add pgvector integration tests in a PostgreSQL CI service.
- Add layout-aware table extraction.
- Add PDF page preview with evidence highlight anchors.
- Improve field extraction with layout-aware parsing, Word layout parsing, tracked-change handling, and table extraction.
- Add OCR as an isolated optional worker for scanned PDFs.

## Explicit No-Go Items

- Multi-tenant SaaS.
- Payment or subscription flows.
- Approval workflows.
- Notification systems.
- Complex role-based permissions.
- Legal advice claims.
