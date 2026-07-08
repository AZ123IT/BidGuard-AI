# Database Design

## Tables

- `documents`: uploaded file metadata, parse status, page count, source path, and errors.
- `document_chunks`: searchable page-level text chunks. The `embedding` JSON field stores SQLite-compatible vectors, with `embedding_provider`, `embedding_model`, and `embedding_dimension` metadata. PostgreSQL also uses an optional `embedding_vector vector(n)` column for pgvector search.
- `document_tables`: reserved structure for parsed tables.
- `extracted_fields`: regex-extracted procurement fields and clause snippets.
- `risk_rules`: built-in demonstration rule metadata.
- `risk_findings`: persisted rule matches for a document, including rule category, severity, explanation, evidence text, and page number where available.
- `agent_runs`: one record per agent objective.
- `tool_calls`: tool name, input payload, output payload, and latency for each agent tool call.
- `eval_cases`: future evaluation dataset rows.
- `eval_results`: future metric outputs.

## Local Database

SQLite is the default for quick portfolio setup:

```text
DATABASE_URL=sqlite:///./bidguard.db
```

The app creates tables on startup for MVP convenience. Alembic metadata is included under `backend/alembic` so schema changes can move to migration-first workflow later. SQLite does not require pgvector and should continue to work without PostgreSQL installed.

## PostgreSQL

PostgreSQL can be started with:

```bash
docker compose up -d postgres
```

Use:

```text
DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard
```

The compose service uses the `pgvector/pgvector:pg16` image and runs safe init SQL from `backend/sql`. `001_pgvector_extension.sql` enables the extension. `002_pgvector_chunks.sql` is safe during Docker bootstrap and only modifies `document_chunks` if the table already exists.

Alembic/runtime DDL creates `embedding_vector vector(EMBEDDING_DIMENSION)` and an `ivfflat` vector index. Local deterministic embeddings use dimension `64`. Real hosted embedding models often use a larger dimension such as `1536`; set `EMBEDDING_DIMENSION` before running migrations or starting the app against a fresh PostgreSQL database.

Run the smoke script after migrations:

```bash
cd backend
DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard \
EMBEDDING_PROVIDER=local \
EMBEDDING_DIMENSION=64 \
LLM_PROVIDER=local_fake \
.venv/bin/python scripts/smoke_pgvector.py
```
