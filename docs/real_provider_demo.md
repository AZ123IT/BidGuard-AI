# Real Provider Demo

This document records the repeatable real-provider validation path for BidGuard AI.

## Verified Result

Date: 2026-07-10

Status: `PASS`

The measured run used:

- embedding API: local Ollama `0.31.2`, exposed through the OpenAI-compatible API;
- embedding model: `embeddinggemma`, dimension `64`;
- LLM API: DeepSeek OpenAI-compatible API;
- LLM model: `deepseek-v4-flash`;
- database: PostgreSQL with pgvector `0.8.4` and `embedding_vector vector(64)`;
- retrieval method observed by the workflow eval: `pgvector`.

The final 36-case workflow eval passed `36/36`. It recorded 7,318 total provider tokens, about 29.6 seconds of aggregate LLM request latency, about 3.9 seconds of aggregate embedding request latency, and estimated DeepSeek API cost of `$0.00062828`. Ollama embedding API cost was `$0`; this does not attempt to price local electricity or hardware.

The separate 16-case retrieval challenge did not score 100%. PostgreSQL pgvector with `embeddinggemma` at 64 dimensions measured Recall@1 `0.5625`, Recall@5 `0.6875`, MRR `0.6250`, nDCG@5 `0.6414`, and evidence-page hit `0.6875`. See `evaluation_failure_analysis.md` for the baseline comparison and failed cases.

Generated reports remain local and ignored by Git:

- `data/eval_reports/latest_real_provider_eval.json`
- `data/eval_reports/latest_real_provider_failure_analysis.md`
- `data/eval_reports/latest_real_retrieval_benchmark.json`
- `data/eval_reports/latest_real_retrieval_benchmark.md`

## Provider Configuration

Keep the real DeepSeek key only in `backend/.env` or the shell. Do not commit it.

```bash
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_API_KEY=ollama
EMBEDDING_BASE_URL=http://localhost:11434/v1
EMBEDDING_MODEL=embeddinggemma
EMBEDDING_DIMENSION=64

LLM_PROVIDER=openai_compatible
LLM_API_KEY=your_deepseek_key_here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_TEMPERATURE=0
LLM_INPUT_COST_PER_MILLION_TOKENS=0.14
LLM_CACHED_INPUT_COST_PER_MILLION_TOKENS=0.0028
LLM_OUTPUT_COST_PER_MILLION_TOKENS=0.28
```

`EMBEDDING_API_KEY=ollama` is a non-secret compatibility value. Local Ollama does not authenticate it. The DeepSeek prices above are the USD rates used for the 2026-07-10 experiment; check the [current DeepSeek pricing page](https://api-docs.deepseek.com/quick_start/pricing) before repeating a cost claim.

## Repeat The Experiment

Start the local services:

```bash
open -a Ollama
ollama pull embeddinggemma
docker compose up -d postgres
```

Run migrations and the complete wrapper:

```bash
cd backend
DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard \
EMBEDDING_DIMENSION=64 \
.venv/bin/alembic upgrade head

cd ..
DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard \
LLM_INPUT_COST_PER_MILLION_TOKENS=0.14 \
LLM_CACHED_INPUT_COST_PER_MILLION_TOKENS=0.0028 \
LLM_OUTPUT_COST_PER_MILLION_TOKENS=0.28 \
python3 scripts/real_provider_demo.py
```

The wrapper first checks PostgreSQL, the pgvector extension, and the configured vector dimension without calling either AI provider. It then runs provider smoke, the 36-case workflow eval, and the 16-case retrieval benchmark. A completed eval with failed cases is retained and followed by the benchmark so failure analysis is not lost. Infrastructure fallback, invalid provider output, or missing required pgvector mode still fails the run.

## Dimension Experiment

`embeddinggemma` reports a native dimension of `768`. A separate, non-destructive PostgreSQL database was migrated with `vector(768)` and benchmarked. It measured Recall@5 `0.6250` and MRR `0.5938`, below the 64-dimensional run on this small challenge set. Larger dimension was therefore not adopted merely because it appears more advanced.

The result is dataset-specific. A future experiment should test model-specific query/document encoding and public, human-labelled tender data before selecting a dimension or adding a reranker.

## Evidence Guard Result

The first real eval exposed an identifier-sufficiency bug: semantically similar supplier text could reach the LLM for a missing tax-ID question. The evidence gate now requires an actual labelled identifier value for ID/number/serial-number questions. Direct Q&A and the Agent both return the exact fallback with zero evidence and skip LLM synthesis in that case.

## Completion Criteria

The real experiment counts as complete only when:

- provider smoke passes for Ollama embedding and DeepSeek synthesis;
- the eval reports `database_mode: postgres_pgvector`;
- evidence reports `retrieval_method: pgvector` rather than fallback;
- unsupported identifier questions skip the LLM and return the exact fallback;
- benchmark real and pgvector rows execute, even when quality metrics are imperfect;
- provider/model/dimension, latency, tokens, cache usage, and cost basis are recorded;
- credentials remain in ignored environment files or shell variables.
