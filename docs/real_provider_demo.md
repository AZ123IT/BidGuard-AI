# Real Provider Demo

This document records the repeatable path for validating BidGuard AI with real OpenAI-compatible embedding and LLM providers.

## Current Session Result

Date: 2026-07-09

Status: `SKIPPED`

Reason: the local environment is configured for the default deterministic mode:

- `EMBEDDING_PROVIDER=local`
- no embedding API key is configured
- `LLM_PROVIDER=local_fake`
- no LLM API key is configured

No real API call was made, no secrets were printed, and no eval report was committed.

## Local No-Key Baseline

Run this from the project root:

```bash
python3 scripts/verify_all.py
```

This validates local deterministic embeddings, local fake guarded synthesis, SQLite fallback retrieval, eval metrics, and frontend build.

## Real Provider Smoke And Eval

Set provider credentials in your shell or an untracked `backend/.env`. Do not commit keys.

```bash
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_API_KEY=your_embedding_key_here
EMBEDDING_BASE_URL=https://your-openai-compatible-base-url
EMBEDDING_MODEL=your_embedding_model
EMBEDDING_DIMENSION=your_embedding_dimension

LLM_PROVIDER=openai_compatible
LLM_API_KEY=your_llm_key_here
LLM_BASE_URL=https://your-openai-compatible-base-url
LLM_MODEL=your_llm_model
```

Then run:

```bash
python3 scripts/real_provider_demo.py
```

The script:

- runs provider smoke,
- verifies the embedding dimension,
- verifies guarded synthesis with supplied evidence,
- skips clearly if real providers are not configured,
- runs the 18-case demo eval only when both real providers pass,
- writes the generated eval JSON to `data/eval_reports/latest_real_provider_eval.json`.

`data/eval_reports/` is intentionally ignored by Git.

## Recommended Real RAG Demo

For the strongest demo, use real embeddings with PostgreSQL + pgvector:

```bash
docker compose up -d postgres

cd backend
DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard \
EMBEDDING_PROVIDER=openai_compatible \
EMBEDDING_API_KEY=your_embedding_key_here \
EMBEDDING_BASE_URL=https://your-openai-compatible-base-url \
EMBEDDING_MODEL=your_embedding_model \
EMBEDDING_DIMENSION=your_embedding_dimension \
LLM_PROVIDER=openai_compatible \
LLM_API_KEY=your_llm_key_here \
LLM_BASE_URL=https://your-openai-compatible-base-url \
LLM_MODEL=your_llm_model \
.venv/bin/python scripts/smoke_pgvector.py
```

If `EMBEDDING_DIMENSION` changes after the PostgreSQL volume has been initialized, recreate the local volume or migrate the vector column intentionally.
