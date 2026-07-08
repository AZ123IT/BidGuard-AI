# BidGuard AI Phase 2.1 Design

## Goal

Upgrade the verified MVP into a real evidence-first RAG implementation without turning it into an enterprise SaaS or legal-advice product.

## Architecture

Embeddings are generated at ingestion time through a small provider interface. SQLite keeps embeddings in the existing `document_chunks.embedding` JSON column and uses deterministic local embeddings for tests and fallback mode. PostgreSQL can enable pgvector and maintain a vector column/index through migration/DDL while JSON remains the portable source of truth.

Retrieval becomes hybrid: vector similarity plus keyword overlap, with a simple weighted score and a `retrieval_method` label. If PostgreSQL vector search is available it can use pgvector; otherwise the same scoring runs in Python against stored JSON embeddings.

Answering remains evidence-first. The backend enforces minimum evidence before any LLM call. If evidence is weak or empty it returns the existing insufficient-evidence sentence. If an OpenAI-compatible LLM is configured, synthesis is prompted to use only retrieved evidence; otherwise a deterministic evidence summary is returned.

## Scope

Included:
- embedding provider abstraction,
- local deterministic embedding fallback,
- OpenAI-compatible embedding and LLM providers,
- embedding storage on chunks,
- SQLite fallback retrieval,
- PostgreSQL pgvector migration/DDL path,
- guarded synthesis metadata,
- agent tool trace metadata,
- simple JSON eval runner,
- focused frontend display updates,
- documentation updates.

Not included:
- heavy rerankers,
- background ingestion workers,
- OCR,
- multi-agent orchestration,
- multi-tenant permissions,
- legal advice workflows.
