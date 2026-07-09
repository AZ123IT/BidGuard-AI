# BidGuard AI

BidGuard AI is an evidence-first tender and contract document review agent built as a personal AI engineering portfolio project.

It demonstrates document parsing, RAG retrieval, page-level evidence citation, guarded LLM synthesis, rule-based risk checks, cross-document comparison, lightweight agent tool-calling, evaluation, and full-stack engineering.

BidGuard AI is not an enterprise SaaS platform and does not provide professional legal advice.

## Project Status

| Category | Status | Notes |
| --- | --- | --- |
| Core app | Implemented | FastAPI backend and Next.js frontend. |
| Evidence Q&A | Implemented | Answers include cited snippets, page numbers, chunk ids, scores, and retrieval method. |
| Risk review | Implemented | Deterministic procurement risk rules. |
| Cross-document diff | Implemented | Regex field extraction and structured comparison rows. |
| Agent trace | Implemented | Tool calls and run traces are logged. |
| SQLite mode | Local/fallback | Default zero-config mode with JSON embeddings and hybrid retrieval. |
| PostgreSQL + pgvector | Implemented | Verified by smoke script when Docker is available. |
| Real providers | Optional | OpenAI-compatible embedding and LLM providers are validated only when env vars are set. |
| GitHub Actions CI | Implemented | Runs backend tests/Ruff and frontend typecheck/build without secrets. |
| OCR | Future | Not implemented. |
| DOCX upload | Implemented | Lightweight text extraction from Word document XML; page reference is document-level. |
| Review report export | Implemented | Document detail can export a Markdown evidence/risk report. |
| PDF highlighting | Future | Chunk links exist; pixel-perfect PDF highlights are future work. |

## Key Features

- Upload public tender or contract PDF, DOCX, or TXT files.
- Parse PDFs with PyMuPDF, extract DOCX text, and store page-aware or document-level chunks.
- Ask questions and receive answers grounded in cited evidence.
- Open cited evidence chunks from Q&A on the document detail page.
- Export a Markdown review report from document detail.
- Return a deterministic insufficient-evidence fallback when support is weak.
- Run built-in risk checks for common procurement review issues.
- Compare extracted fields across two document versions.
- Inspect agent runs and tool calls.
- Run smoke evals, demo evals, provider smoke, and pgvector smoke.
- Use deterministic local providers by default; optionally validate real OpenAI-compatible providers.
- Use GitHub Actions CI for no-secret backend/frontend checks.

## Architecture

```mermaid
flowchart TD
  UI["Next.js frontend"] --> API["FastAPI API"]
  API --> Upload["Document upload"]
  Upload --> Parser["PDF/text parser"]
  Parser --> Chunker["Page-aware chunker"]
  Chunker --> Embed["Embedding provider"]
  Embed --> Store["document_chunks"]
  Store --> SQLite["SQLite JSON fallback"]
  Store --> PG["PostgreSQL + pgvector"]
  SQLite --> Retrieval["Hybrid/vector retrieval"]
  PG --> Retrieval
  Retrieval --> Gate["Evidence sufficiency gate"]
  Gate -->|sufficient| LLM["Guarded LLM synthesis"]
  Gate -->|weak or empty| Refusal["Exact fallback response"]
  LLM --> Answer["Answer with citations"]
  Refusal --> Answer
  API --> Agent["Tool-calling agent"]
  Agent --> Tools["Evidence / risk / diff / report tools"]
  Tools --> Trace["Agent trace"]
```

## Tech Stack

- Frontend: Next.js, TypeScript, Tailwind CSS.
- Backend: FastAPI, Python, SQLAlchemy, Alembic.
- Storage: SQLite by default, optional PostgreSQL with pgvector.
- Parsing: PyMuPDF.
- AI/RAG: local deterministic embeddings, OpenAI-compatible provider abstraction, guarded synthesis.
- Evaluation: JSON eval cases, smoke scripts, verification script.

## RAG Pipeline

1. Parse uploaded PDF, DOCX, TXT, or seeded demo text into source text.
2. Chunk text while preserving document id, title, page number, and chunk index.
3. Generate embeddings through local deterministic or OpenAI-compatible providers.
4. Store embeddings as JSON in SQLite; store `embedding_vector` in PostgreSQL when pgvector is enabled.
5. Retrieve evidence with hybrid scoring and return score metadata.
6. Run LLM synthesis only after retrieved evidence passes the sufficiency gate.
7. Return answer, evidence snippets, document title, page number, chunk id, score, retrieval method, and synthesis metadata.

If evidence is weak or missing, the backend returns exactly:

```text
The uploaded documents do not contain enough evidence to answer this question reliably.
```

## Agent Workflow

The agent is intentionally lightweight:

- Normal document questions use `evidence_search_tool`.
- Risk/review requests use `risk_rule_check_tool`.
- Compare requests use `cross_doc_diff_tool`.
- Report requests can use `report_generator_tool`.
- Tool calls are logged with status, latency, and output summaries.

## Quick Start

Backend terminal:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend terminal, from the repository root:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

Default local mode needs no API keys:

```text
DATABASE_URL=sqlite:///./bidguard.db
EMBEDDING_PROVIDER=local
LLM_PROVIDER=local_fake
```

## Verification

Run the default verification suite from the project root:

```bash
python3 scripts/verify_all.py
```

It runs:

- backend tests,
- backend Ruff,
- provider smoke,
- smoke eval,
- demo eval,
- frontend typecheck,
- frontend build.

Equivalent individual commands:

```bash
cd backend
.venv/bin/python -m pytest tests -q
.venv/bin/ruff check .
.venv/bin/python scripts/smoke_providers.py
.venv/bin/python -m app.evaluation.run_eval
.venv/bin/python -m app.evaluation.run_eval --dataset ../data/eval_cases/rag_demo.json

cd ../frontend
npm run typecheck
npm run build
```

GitHub Actions runs the backend tests, backend Ruff, frontend typecheck, and frontend build on pushes and pull requests to `main` or `master`. The default CI path uses local deterministic providers and does not require API keys.

## Demo Workflow

See `docs/demo_walkthrough.md` for the full step-by-step demo.

Fast local path:

1. Start backend and frontend.
2. Upload `data/sample_docs/sample_tender.pdf`.
3. Ask `What is the bid deadline?`.
4. Open a cited evidence chunk from the Q&A evidence card.
5. Ask `What is the vendor tax ID?` to trigger insufficient evidence.
6. Run the demo eval to seed the richer synthetic demo documents.
7. Run risk review.
8. Compare demo contract draft vs revised addendum.
9. Inspect agent trace.
10. Run `python3 scripts/verify_all.py`.

Good demo questions:

- `What is the bid deadline for the solar microgrid project?`
- `What are the payment terms in the contract draft?`
- `Are the acceptance criteria clearly defined?`
- `Compare the contract draft and revised contract for amount and payment changes.`
- `What is the vendor tax ID?`

## Evaluation

Datasets:

- `data/eval_cases/rag_smoke.json`: 2-case smoke set.
- `data/eval_cases/rag_demo.json`: 18-case demo set covering evidence Q&A, insufficient evidence, risk rules, cross-document diff, and agent routing.

Metrics include retrieval hit, evidence page hit, answer keyword hit, insufficient-evidence correctness, risk category/keyword hit, diff field/keyword hit, tool-call correctness, average score, provider mode, database mode, and retrieval method.

## Provider Modes

Local mode:

```bash
cd backend
EMBEDDING_PROVIDER=local \
EMBEDDING_DIMENSION=64 \
LLM_PROVIDER=local_fake \
.venv/bin/python scripts/smoke_providers.py
```

Real provider mode is optional. Use placeholders only in docs and set real keys in an untracked `.env` or shell environment:

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

If keys are missing, provider smoke reports `skipped` for real providers and exits successfully.

Run the repeatable real-provider demo wrapper from the project root:

```bash
python3 scripts/real_provider_demo.py
```

It runs provider smoke first. If both real providers pass, it runs the 18-case demo eval and writes an ignored JSON report to `data/eval_reports/latest_real_provider_eval.json`. If real keys are not configured, it exits successfully with `SKIPPED`. See `docs/real_provider_demo.md`.

## PostgreSQL + pgvector

Start PostgreSQL:

```bash
docker compose up -d postgres
```

Run pgvector smoke:

```bash
cd backend
DATABASE_URL=postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard \
EMBEDDING_PROVIDER=local \
EMBEDDING_DIMENSION=64 \
LLM_PROVIDER=local_fake \
.venv/bin/python scripts/smoke_pgvector.py
```

Or include it in aggregate verification:

```bash
python3 scripts/verify_all.py --with-pgvector
```

The vector column dimension must match `EMBEDDING_DIMENSION`. If you change embedding dimensions after creating the PostgreSQL volume, recreate the local volume or migrate the column intentionally.

## Interview Notes

Use `docs/interview_brief.md` for:

- 30-second and 2-minute explanations,
- architecture summary,
- RAG pipeline narrative,
- agent workflow explanation,
- evaluation story,
- resume-ready bullets,
- likely interview Q&A.

See `docs/release_notes_v0_1.md` for the current packaged release summary.

## Safe GitHub Push Checklist

Before pushing a public repo:

```bash
git status
git log --oneline --max-count=5
git diff --check
git remote add origin <YOUR_REPO_URL>
git branch -M main
git push -u origin main
```

Check that `.env` files, local databases, uploaded documents, generated eval reports, `.next/`, `node_modules/`, and API keys are not staged. Keep real provider credentials only in your shell or an untracked `.env`.

## Limitations

- Local embeddings are deterministic hash vectors, not semantic embeddings.
- SQLite retrieval is a fallback path, not production vector search.
- Field extraction is regex-based.
- Risk checks are deterministic signals, not legal analysis.
- Real provider validation requires user-supplied API credentials.
- OCR and pixel-perfect PDF evidence highlighting are intentionally future work.

## Roadmap

Next useful steps:

- validate a real embedding and LLM provider with local env vars,
- add public tender PDFs and richer eval cases,
- add CI coverage for PostgreSQL + pgvector,
- improve field extraction with layout-aware parsing,
- add optional OCR as an isolated worker,
- add PDF page preview and evidence highlight anchors.

## Project Boundaries

BidGuard AI intentionally excludes multi-tenancy, payments, approvals, notifications, complex role permissions, and legal-advice claims. It favors transparent evidence and deterministic evaluation over broad automation.
