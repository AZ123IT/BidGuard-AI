# Evaluation Plan

Phase 2.1 ships a small deterministic runner:

```bash
cd backend
.venv/bin/python -m app.evaluation.run_eval
```

The runner loads `data/eval_cases/rag_smoke.json`, ensures the sample tender is available, runs Q&A or agent calls, and prints JSON metrics plus observability fields.

The output includes:

- provider mode: embedding provider/model and LLM provider/model,
- database mode: `sqlite`, `postgres`, or `postgres_pgvector`,
- retrieval methods observed, such as `hybrid_fallback` or `pgvector`,
- average evidence score across answerable cases,
- per-case evidence count, average score, synthesis provider, and whether LLM synthesis was used.

For local PostgreSQL verification, run:

```bash
cd backend
DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard \
EMBEDDING_PROVIDER=local \
EMBEDDING_DIMENSION=64 \
LLM_PROVIDER=local_fake \
.venv/bin/python scripts/smoke_pgvector.py
```

The pgvector smoke script checks connection mode, pgvector extension availability, vector column type, upload/ingestion, JSON and vector embedding storage, answerable retrieval, exact insufficient-evidence fallback, and optional real provider validation when provider env vars are configured.

## Metrics

- Retrieval hit rate: whether expected evidence appears in the top-k retrieved chunks.
- Context recall: whether enough supporting context is retrieved for the answer.
- Faithfulness: whether generated answers are fully supported by cited evidence.
- Answer relevance: whether the answer addresses the user question.
- Tool call accuracy: whether the agent selected the right tool sequence.
- Retrieval method: whether evidence came from `hybrid_fallback` or `pgvector`.
- Provider/database mode: whether the run used local providers, OpenAI-compatible providers, SQLite, or PostgreSQL pgvector.
- Latency: endpoint and tool-call execution time.
- Token cost: future LLM and embedding provider usage cost.

## Test Sets

1. Direct lookup questions where the answer is present on one page.
2. Missing-evidence questions where refusal is expected.
3. Risk-rule cases with known payment, acceptance, dispute, and scoring findings.
4. Cross-document comparisons with one controlled field changed.
5. Agent objectives that should trigger retrieval only, risk plus retrieval, or diff plus retrieval.

## Scoring Approach

Start with deterministic checks:

- expected page appears in top 3 evidence chunks,
- unsupported questions return the exact insufficient-evidence sentence,
- expected risk rule names appear,
- changed fields are marked changed,
- uncertain fields are not presented as certain.

Only after this baseline should LLM-judged faithfulness or Ragas integration be introduced.
