# BidGuard AI MVP Design

## Purpose

BidGuard AI is a personal portfolio-level application for evidence-first tender and contract document review. It demonstrates document parsing, searchable chunks, page-level citations, deterministic risk rules, cross-document field comparison, agent tool tracing, and evaluation-ready logging.

## Scope

The MVP is intentionally not a multi-tenant SaaS product, legal-advice product, payment system, approval workflow, or notification platform. Uploaded documents are local project data. AI-facing abstractions exist, but the default answer path is deterministic and evidence-retrieval based.

## Architecture

The backend is FastAPI with SQLAlchemy 2.0 models. SQLite is the default local database, while `DATABASE_URL` can point to PostgreSQL. The schema includes document chunks and an `embedding` placeholder so pgvector can be added later without changing the API shape.

The frontend is Next.js App Router with TypeScript and Tailwind CSS. It uses a simple `fetch` wrapper and client pages for dashboard, documents, Q&A, risk review, comparison, and agent trace.

## Evidence Behavior

Question answering retrieves chunks from uploaded documents. If no positive-scoring evidence exists, the answer is exactly: "The uploaded documents do not contain enough evidence to answer this question reliably." Returned evidence includes document title, page number, snippet text, and retrieval score.

## Agent Workflow

The agent is a lightweight tool router. It can call `evidence_search_tool`, `risk_rule_check_tool`, `cross_doc_diff_tool`, and `report_generator_tool`, then records each tool call with input, output, and latency.
