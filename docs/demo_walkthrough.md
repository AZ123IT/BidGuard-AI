# Demo Walkthrough

This walkthrough uses only synthetic documents from `data/sample_docs/demo_pack/`.

## Demo Documents

- `demo_tender_solar_microgrid.txt`: tender invitation with bid deadline, opening time, payment terms, acceptance criteria, liability, dispute resolution, and quantified scoring.
- `demo_contract_draft.txt`: contract draft with a supplier, fixed amount, 60-day payment term, detailed acceptance criteria, balanced liability, and arbitration.
- `demo_contract_revised.txt`: revised addendum with changed amount, changed deadline, 120-day payment term, removed acceptance criteria, narrower liability, and a different dispute forum.
- `demo_risky_terms.txt`: deliberately risky terms covering long payment period, vague acceptance, one-sided liability, unclear termination, inconsistent deadline/opening time, overly specific qualification, unquantified scoring, and missing dispute resolution.
- `demo_policy_notice.txt`: background policy notice used for insufficient-evidence questions.

## Start Locally

Backend:

```bash
cd "/Users/kaisa/Downloads/BidGuard AI/backend"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd "/Users/kaisa/Downloads/BidGuard AI/frontend"
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Final Demo Script

Use this sequence for a short interview demo:

1. Start the backend.
2. Start the frontend.
3. Open `http://localhost:3000/documents`.
4. Upload `data/sample_docs/sample_tender.pdf`.
5. Open `http://localhost:3000/qa`, select the uploaded tender, and ask:

```text
What is the bid deadline?
```

6. Show the answer, page number, evidence snippet, retrieval score, retrieval method, and synthesis status.
7. Ask an unsupported question:

```text
What bank guarantee number is required?
```

8. Show the exact insufficient-evidence response.
9. Run the demo eval to seed richer synthetic documents:

```bash
cd "/Users/kaisa/Downloads/BidGuard AI/backend"
.venv/bin/python -m app.evaluation.run_eval --dataset ../data/eval_cases/rag_demo.json
```

10. Open `http://localhost:3000/risk`, select `demo_risky_terms`, and run risk review.
11. Open `http://localhost:3000/compare`, compare `demo_contract_draft` with `demo_contract_revised`, and show changed amount, deadline, payment terms, and acceptance criteria.
12. Open `http://localhost:3000/agent-trace`, run a normal question, a risk review request, and a compare request, then show the tool calls.
13. Run local verification:

```bash
cd "/Users/kaisa/Downloads/BidGuard AI"
python3 scripts/verify_all.py
```

14. If Docker is available, run pgvector smoke:

```bash
docker compose up -d postgres
cd backend
DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard \
EMBEDDING_PROVIDER=local \
EMBEDDING_DIMENSION=64 \
LLM_PROVIDER=local_fake \
.venv/bin/python scripts/smoke_pgvector.py
cd ..
docker compose stop postgres
```

Good example questions from the demo dataset:

- `What is the bid deadline for the Harbor Solar Microgrid Upgrade?`
- `What payment period does the tender specify?`
- `What acceptance criteria are in the contract draft?`
- `What dispute resolution process does the contract draft use?`
- `What cyber coverage certificate ID is required?`

## Quick Local Demo Flow

This path uses SQLite, local deterministic embeddings, and local fake synthesis. It does not need Docker or API keys.

1. Start backend and frontend with the commands above.
2. Open `http://localhost:3000/documents`.
3. Upload `data/sample_docs/sample_tender.pdf`.
4. Open `http://localhost:3000/qa`, select the uploaded tender, and ask:

```text
What is the bid deadline?
```

5. Confirm the answer includes evidence with document title, page number, snippet, score, retrieval method, and synthesis status.
6. Ask an unsupported question:

```text
What bank guarantee number is required?
```

7. Confirm the app returns the exact insufficient-evidence fallback.
8. Open `http://localhost:3000/risk`, select the tender or `demo_risky_terms` if seeded, and run risk review.
9. Open `http://localhost:3000/compare` and compare `demo_contract_draft` with `demo_contract_revised` after running the demo eval seeding step.
10. Open `http://localhost:3000/agent-trace`, run a normal evidence question, a risk review request, and a compare request, then inspect tool calls.

## Run SQLite Eval

```bash
cd "/Users/kaisa/Downloads/BidGuard AI/backend"
.venv/bin/python -m app.evaluation.run_eval --dataset ../data/eval_cases/rag_demo.json
```

The output reports total cases, passed cases, pass rate, metric summary, retrieval methods, provider mode, and database mode.

## Run Full Local Verification

From the project root:

```bash
cd "/Users/kaisa/Downloads/BidGuard AI"
python3 scripts/verify_all.py
```

This runs backend tests, Ruff, provider smoke, smoke eval, demo eval, frontend typecheck, and frontend build.

## Validate Providers

Local mode is the default interview-safe mode:

```bash
cd "/Users/kaisa/Downloads/BidGuard AI/backend"
EMBEDDING_PROVIDER=local \
EMBEDDING_DIMENSION=64 \
LLM_PROVIDER=local_fake \
.venv/bin/python scripts/smoke_providers.py
```

It works without API keys, is deterministic, and is suitable for tests. It is not meant to prove semantic embedding quality.

Real-provider mode is optional. Export provider keys in the shell or an untracked `.env` file, then run:

```bash
cd "/Users/kaisa/Downloads/BidGuard AI/backend"
EMBEDDING_PROVIDER=openai_compatible \
EMBEDDING_API_KEY=your_embedding_key_here \
EMBEDDING_BASE_URL=https://your-openai-compatible-base-url \
EMBEDDING_MODEL=your_embedding_model \
EMBEDDING_DIMENSION=your_embedding_dimension \
LLM_PROVIDER=openai_compatible \
LLM_API_KEY=your_llm_key_here \
LLM_BASE_URL=https://your-openai-compatible-base-url \
LLM_MODEL=your_llm_model \
.venv/bin/python scripts/smoke_providers.py
```

If keys are missing, the smoke command prints `skipped` for real providers and exits successfully. If dimensions mismatch, it fails with the expected and actual vector lengths.

## Run PostgreSQL + pgvector Smoke

```bash
cd "/Users/kaisa/Downloads/BidGuard AI"
docker compose up -d postgres

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

The smoke script verifies pgvector extension availability, vector column dimension, JSON/vector embedding storage, answerable Q&A retrieval with `retrieval_method: "pgvector"`, and the exact insufficient-evidence fallback.

For the strongest real RAG demo, use PostgreSQL + pgvector with a real embedding provider. Set `EMBEDDING_DIMENSION` before running migrations so the `embedding_vector` column matches the provider output.

You can also run the aggregate pgvector check from the project root:

```bash
python3 scripts/verify_all.py --with-pgvector
```

## UI Demo Flow

1. Upload or seed demo documents through eval. The eval runner seeds text documents into the local database for repeatable demos.
2. Q&A page: select `demo_tender_solar_microgrid` and ask `What is the bid deadline?`.
3. Insufficient evidence: select `demo_policy_notice` and ask `What bank guarantee number is required?`.
4. Risk Review: select `demo_risky_terms` and run the risk checker.
5. Compare: compare `demo_contract_draft` with `demo_contract_revised`.
6. Agent Trace: run a normal evidence question, a risk review request, and a compare request; inspect tool calls.

## Interview Metrics To Mention

- Retrieval hit and evidence page hit for answerable Q&A.
- Exact insufficient-evidence correctness for unsupported questions.
- Risk category/keyword hit for deterministic rule checks.
- Diff field/keyword hit for changed contract fields.
- Tool-call correctness for agent routing.
- Average retrieval score and observed retrieval method.
- Provider mode and database mode, showing SQLite fallback and PostgreSQL pgvector verification.
- Provider smoke result, explaining that local deterministic providers are for repeatable tests and real provider mode is validated separately.

## Boundaries

This remains an evidence-first portfolio project. It does not provide legal advice, does not use confidential contracts, and does not call real providers unless explicitly configured through environment variables.
