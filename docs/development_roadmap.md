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

## Next Phase

- Add more realistic public-document eval cases.
- Add pgvector integration tests in a PostgreSQL CI service.
- Add layout-aware table extraction.
- Add PDF page preview with evidence highlight anchors.
- Improve field extraction with layout-aware parsing and table extraction.
- Add OCR as an isolated optional worker for scanned PDFs.

## Explicit No-Go Items

- Multi-tenant SaaS.
- Payment or subscription flows.
- Approval workflows.
- Notification systems.
- Complex role-based permissions.
- Legal advice claims.
