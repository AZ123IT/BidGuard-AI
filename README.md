# BidGuard AI

BidGuard AI is an evidence-first tender and contract document review agent built as a personal AI engineering portfolio project. It demonstrates RAG-style document retrieval, PDF parsing, page-level citations, deterministic risk rules, cross-document comparison, agent tool calls, evaluation planning, and full-stack engineering.

It is not an enterprise SaaS system and does not provide professional legal advice.

## Features

- Upload public tender or contract PDFs.
- Parse text with PyMuPDF and store page-aware chunks.
- Ask questions and receive answers with cited document evidence.
- Refuse unsupported answers when retrieved evidence is insufficient.
- Run built-in procurement risk rules.
- Compare extracted fields across two documents.
- Inspect agent runs and tool-call traces.
- Use SQLite locally or PostgreSQL through `DATABASE_URL`.
- Generate real chunk embeddings through a provider abstraction.
- Use deterministic local embeddings and local fake synthesis for tests.
- Use guarded OpenAI-compatible embedding/LLM providers when configured.
- Run a small RAG evaluation command.

## Project Structure

```text
backend/          FastAPI API, SQLAlchemy models, services, tests, Alembic
frontend/         Next.js App Router UI
docs/             Architecture, database, agent, evaluation, roadmap docs
data/sample_docs/ Sample tender text/PDF
data/sample_docs/demo_pack/ Synthetic tender/contract demo pack
data/uploads/     Local uploaded document storage
docker-compose.yml
```

## Backend Setup

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Default local database:

```text
DATABASE_URL=sqlite:///./bidguard.db
EMBEDDING_PROVIDER=local
LLM_PROVIDER=local_fake
```

Optional PostgreSQL:

```bash
# from the project root
docker compose up -d postgres
```

For local pgvector verification without external API keys:

```bash
cd backend
DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard \
EMBEDDING_PROVIDER=local \
EMBEDDING_DIMENSION=64 \
LLM_PROVIDER=local_fake \
.venv/bin/alembic upgrade head

DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard \
EMBEDDING_PROVIDER=local \
EMBEDDING_DIMENSION=64 \
LLM_PROVIDER=local_fake \
.venv/bin/python scripts/smoke_pgvector.py
```

For a real OpenAI-compatible embedding provider, set these before the first PostgreSQL migration or before the app creates the `embedding_vector` column:

```text
DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_API_KEY=...
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

Optional guarded LLM synthesis uses:

```text
LLM_PROVIDER=openai_compatible
LLM_API_KEY=...
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
```

For PostgreSQL, pgvector is enabled by `docker-compose.yml` and the Alembic/runtime DDL adds an optional `embedding_vector` column. The vector dimension must match `EMBEDDING_DIMENSION`; if you change dimensions after creating the column, recreate the local Postgres volume or migrate the column intentionally. SQLite remains the default and stores embeddings in JSON.

## Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`. The backend should be running at `http://localhost:8000`.

## Environment Variables

Backend:

- `DATABASE_URL`: SQLite or PostgreSQL connection string.
- `UPLOAD_DIR`: uploaded file storage directory.
- `CORS_ORIGINS`: comma-separated frontend origins.
- `EMBEDDING_PROVIDER`: `local` or `openai_compatible`.
- `EMBEDDING_MODEL`: embedding model name.
- `EMBEDDING_API_KEY`: embedding provider API key for real mode.
- `EMBEDDING_BASE_URL`: OpenAI-compatible embedding API base URL.
- `EMBEDDING_DIMENSION`: embedding vector dimension.
- `LLM_PROVIDER`: `local_fake` or `openai_compatible`.
- `LLM_MODEL`: chat model name.
- `LLM_API_KEY`: LLM API key for real synthesis.
- `LLM_BASE_URL`: OpenAI-compatible chat API base URL.
- `LLM_TEMPERATURE`: synthesis temperature, default `0`.
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`: compatibility fallbacks.

Frontend:

- `NEXT_PUBLIC_API_URL`: FastAPI base URL.

## Verification

```bash
cd backend && .venv/bin/python -m pytest tests -q
cd backend && .venv/bin/ruff check .
cd frontend && npm run typecheck
cd frontend && npm run build
```

Run the RAG smoke eval:

```bash
cd backend
.venv/bin/python -m app.evaluation.run_eval
```

Run the interview demo eval:

```bash
cd backend
.venv/bin/python -m app.evaluation.run_eval --dataset ../data/eval_cases/rag_demo.json
```

Optionally write a local JSON report. Generated reports are ignored by Git:

```bash
.venv/bin/python -m app.evaluation.run_eval \
  --dataset ../data/eval_cases/rag_demo.json \
  --output-json ../data/eval_reports/latest_eval.json
```

Run the pgvector smoke verification after starting PostgreSQL:

```bash
cd backend
DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard \
EMBEDDING_PROVIDER=local \
EMBEDDING_DIMENSION=64 \
LLM_PROVIDER=local_fake \
.venv/bin/python scripts/smoke_pgvector.py
```

## Evidence-First RAG Behavior

During ingestion, BidGuard AI chunks parsed text and stores an embedding for each chunk. SQLite stores JSON embeddings and uses `hybrid_fallback` retrieval. PostgreSQL stores JSON embeddings plus `embedding_vector` and uses `pgvector` retrieval when the vector column is available. If evidence is weak or missing, the backend skips synthesis and returns:

```text
The uploaded documents do not contain enough evidence to answer this question reliably.
```

When synthesis is enabled, the prompt instructs the LLM to answer only from retrieved evidence and never invent citations. Tests do not require real API keys.

## Demo Pack

The synthetic demo pack in `data/sample_docs/demo_pack/` includes a tender, contract draft, revised addendum, risky terms document, and policy notice. The expanded eval dataset at `data/eval_cases/rag_demo.json` covers evidence Q&A, insufficient evidence, risk rules, cross-document diff, and agent routing.

See `docs/demo_walkthrough.md` for a repeatable demo script.

## MVP Boundaries

This project intentionally excludes multi-tenancy, payments, approvals, notifications, complex role permissions, and claims of legal advice. The first version favors transparent evidence and deterministic behavior over broad automation.
