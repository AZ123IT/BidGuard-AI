# BidGuard AI v0.1 Release Notes

## Included

- FastAPI backend and Next.js frontend.
- PDF upload, document list/detail, page-aware parsing, and chunking.
- Evidence-first Q&A with cited snippets, page numbers, scores, retrieval method, and synthesis metadata.
- Exact insufficient-evidence fallback when retrieved evidence is weak or empty.
- Deterministic local embeddings and local fake synthesis for no-key demos and tests.
- Optional OpenAI-compatible embedding and LLM provider abstractions.
- SQLite fallback retrieval and PostgreSQL + pgvector retrieval.
- Rule-based procurement risk review.
- Cross-document field and clause comparison.
- Lightweight agent tool workflow and trace logging.
- Synthetic tender/contract demo pack and expanded 18-case eval dataset.
- Provider smoke, pgvector smoke, eval runner, and root verification script.
- Interview brief, demo walkthrough, architecture docs, and roadmap.

## Verification Snapshot

The current release is verified with:

- `python3 scripts/verify_all.py`
- backend tests
- backend Ruff
- provider smoke in local mode
- smoke eval
- demo eval
- frontend typecheck
- frontend build
- PostgreSQL + pgvector smoke when Docker is available

## Known Limitations

- Local embeddings are deterministic hash vectors, not semantic embeddings.
- SQLite retrieval is a fallback path, not production vector search.
- Field extraction is regex-based and intentionally simple.
- Risk rules are deterministic review signals, not legal analysis.
- Real provider validation requires user-supplied API credentials.
- OCR is not implemented.
- PDF evidence highlighting is not implemented.

## Next Phase Candidates

- Validate a real embedding model and real LLM provider.
- Add public tender PDFs and more realistic eval cases.
- Add PostgreSQL + pgvector CI integration tests.
- Improve field extraction with layout-aware parsing and table handling.
- Add optional OCR as an isolated worker.
- Add PDF page preview and evidence highlight anchors.
