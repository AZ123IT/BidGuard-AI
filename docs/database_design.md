# Database Design

## Tables

- `documents`: uploaded file metadata, parse status, page count, source path, and errors.
- `document_chunks`: searchable page-level text chunks. The `embedding` JSON field stores SQLite-compatible vectors, with `embedding_provider`, `embedding_model`, and `embedding_dimension` metadata.
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

The app creates tables on startup for MVP convenience. Alembic metadata is included under `backend/alembic` so schema changes can move to migration-first workflow later.

## PostgreSQL

PostgreSQL can be started with:

```bash
docker compose up -d postgres
```

Use:

```text
DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard
```

The compose service uses the `pgvector/pgvector:pg16` image and runs `backend/sql/001_pgvector_extension.sql`. Phase 2.1 also includes Alembic/runtime DDL for an optional `embedding_vector` column and `ivfflat` vector index. SQLite does not require this column.
