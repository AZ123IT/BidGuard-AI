# BidGuard AI v0.1 Release Notes

## Included

- FastAPI backend and Next.js frontend.
- PDF, DOCX, and TXT upload, document list/detail, parsing, and chunking.
- Evidence-first Q&A with cited snippets, page numbers, scores, retrieval method, and synthesis metadata.
- Lightweight document detail evidence viewer with page-grouped chunks and extracted fields.
- Q&A evidence cards that link back to source chunks.
- Markdown review report export from document detail.
- Exact insufficient-evidence fallback when retrieved evidence is weak or empty.
- Deterministic local embeddings and local fake synthesis for no-key demos and tests.
- Optional OpenAI-compatible embedding and LLM provider abstractions.
- SQLite fallback retrieval and PostgreSQL + pgvector retrieval.
- Rule-based procurement risk review.
- Cross-document field and clause comparison.
- Lightweight agent tool workflow and trace logging.
- Synthetic tender/contract demo pack, 36-case workflow eval, and 16-case retrieval challenge dataset.
- Provider smoke, pgvector smoke, eval runner, retrieval benchmark, failure analysis, and root verification script.
- Real-provider demo wrapper that records an ignored eval report when real providers are configured.
- Verified Ollama `embeddinggemma` + DeepSeek `deepseek-v4-flash` + PostgreSQL pgvector execution with cache-aware cost metrics.
- GitHub Actions CI for backend tests/Ruff and frontend typecheck/build.
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
- GitHub Actions local equivalent checks through `scripts/verify_all.py`

## Known Limitations

- The default test embedding is deterministic; verified Ollama semantic retrieval remains local and model-dependent.
- SQLite retrieval is a fallback path, not production vector search.
- Field extraction is regex-based and intentionally simple.
- DOCX parsing extracts text but not Word layout, comments, tracked changes, or page numbers.
- Risk rules are deterministic review signals, not legal analysis.
- DeepSeek validation requires a user-supplied key; local Ollama embedding does not.
- The 16-case semantic retrieval challenge remains imperfect; the best measured Recall@5 is `0.6875`.
- OCR is not implemented.
- Pixel-perfect PDF evidence highlighting is not implemented; current evidence navigation is chunk-level.

## Next Phase Candidates

- Add public Chinese tender documents and human-reviewed eval labels.
- Test query/document encoding and optional reranking against the measured retrieval failures.
- Add PostgreSQL + pgvector CI integration tests.
- Improve field extraction with layout-aware parsing and table handling.
- Add optional OCR as an isolated worker.
- Add PDF page preview and evidence highlight anchors.
