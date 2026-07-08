import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.config import Settings
from app.main import create_app
from app.services.embeddings import EmbeddingError, make_embedding_provider
from app.services.llm import guarded_synthesize_answer, make_llm_provider
from app.services.retrieval import INSUFFICIENT_EVIDENCE_MESSAGE

ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PDF = ROOT / "data" / "sample_docs" / "sample_tender.pdf"
ANSWERABLE_QUESTION = "What is the bid deadline?"
UNANSWERABLE_QUESTION = "What is the vendor tax identification number?"
OPENAI_COMPATIBLE_ALIASES = {"openai", "openai_compatible", "qwen", "bge"}
LOCAL_EMBEDDING_ALIASES = {"local", "fake", "deterministic"}
LOCAL_LLM_ALIASES = {"local", "local_fake", "fake", "deterministic"}


class SmokeFailure(RuntimeError):
    pass


def database_url_is_postgres(database_url: str) -> bool:
    return database_url.startswith(("postgresql://", "postgresql+"))


def embedding_validation_status(settings: Settings) -> dict[str, Any]:
    provider = settings.embedding_provider.lower()
    if provider in LOCAL_EMBEDDING_ALIASES:
        return {"status": "skipped", "provider": settings.embedding_provider, "reason": "local provider"}
    if provider in OPENAI_COMPATIBLE_ALIASES and not (
        settings.embedding_api_key or settings.openai_api_key
    ):
        return {
            "status": "skipped",
            "provider": settings.embedding_provider,
            "reason": "EMBEDDING_API_KEY or OPENAI_API_KEY is not set",
        }
    return {"status": "configured", "provider": settings.embedding_provider}


def llm_validation_status(settings: Settings) -> dict[str, Any]:
    provider = settings.llm_provider.lower()
    if provider in LOCAL_LLM_ALIASES:
        return {"status": "skipped", "provider": settings.llm_provider, "reason": "local provider"}
    if provider in OPENAI_COMPATIBLE_ALIASES and not (settings.llm_api_key or settings.openai_api_key):
        return {
            "status": "skipped",
            "provider": settings.llm_provider,
            "reason": "LLM_API_KEY or OPENAI_API_KEY is not set",
        }
    return {"status": "configured", "provider": settings.llm_provider}


def run_smoke() -> dict[str, Any]:
    settings = Settings()
    if not database_url_is_postgres(settings.database_url):
        raise SmokeFailure("DATABASE_URL must point to PostgreSQL for pgvector smoke verification.")

    from fastapi.testclient import TestClient

    app = create_app(settings)
    client = TestClient(app)
    _assert(app.state.engine.dialect.name == "postgresql", "SQLAlchemy dialect is not PostgreSQL.")
    _assert(_has_pgvector(app), "pgvector extension is not installed.")

    column_type = _pgvector_column_type(app)
    expected_type = f"vector({settings.embedding_dimension})"
    _assert(column_type == expected_type, f"embedding_vector type is {column_type}, expected {expected_type}.")

    embedding_validation = _run_embedding_validation(settings)
    upload_payload = _upload_sample_pdf(client)
    document_id = upload_payload["id"]
    chunk_stats = _chunk_stats(app, document_id)
    _assert(chunk_stats["chunk_count"] > 0, "No chunks were stored for the uploaded document.")
    _assert(chunk_stats["json_embedding_count"] == chunk_stats["chunk_count"], "JSON embeddings are missing.")
    _assert(chunk_stats["vector_embedding_count"] == chunk_stats["chunk_count"], "pgvector embeddings are missing.")

    answerable = _post_json(
        client,
        "/api/qa",
        {"question": ANSWERABLE_QUESTION, "document_ids": [document_id]},
    )
    _assert(answerable["answer"] != INSUFFICIENT_EVIDENCE_MESSAGE, "Answerable question was refused.")
    _assert(answerable["evidence"], "Answerable question did not return evidence.")
    first_evidence = answerable["evidence"][0]
    _assert(
        first_evidence.get("retrieval_method") == "pgvector",
        f"Expected pgvector retrieval, got {first_evidence.get('retrieval_method')}.",
    )
    _assert(first_evidence.get("document_title"), "Evidence is missing document title.")
    _assert(first_evidence.get("page_number") is not None, "Evidence is missing page number.")
    _assert(first_evidence.get("text"), "Evidence is missing text snippet.")
    _assert(first_evidence.get("score") is not None, "Evidence is missing score.")

    unanswerable = _post_json(
        client,
        "/api/qa",
        {"question": UNANSWERABLE_QUESTION, "document_ids": [document_id]},
    )
    _assert(
        unanswerable["answer"] == INSUFFICIENT_EVIDENCE_MESSAGE,
        "Unanswerable question did not return the exact insufficient-evidence fallback.",
    )
    _assert(unanswerable["evidence"] == [], "Unanswerable question returned evidence.")

    llm_validation = _run_llm_validation(settings, answerable["evidence"])

    return {
        "status": "PASS",
        "database_mode": "postgres_pgvector",
        "pgvector_extension": "available",
        "embedding_vector_type": column_type,
        "document_id": document_id,
        "chunk_stats": chunk_stats,
        "answerable_retrieval_method": first_evidence["retrieval_method"],
        "answerable_score": first_evidence["score"],
        "insufficient_evidence_fallback": unanswerable["answer"],
        "embedding_provider_validation": embedding_validation,
        "llm_provider_validation": llm_validation,
    }


def main() -> int:
    try:
        result = run_smoke()
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


def _run_embedding_validation(settings: Settings) -> dict[str, Any]:
    status = embedding_validation_status(settings)
    if status["status"] != "configured":
        return status
    try:
        embedding = make_embedding_provider(settings).embed_texts(["BidGuard AI pgvector smoke"])[0]
    except EmbeddingError as exc:
        raise SmokeFailure(str(exc)) from exc
    _assert(
        len(embedding) == settings.embedding_dimension,
        f"Embedding provider returned dimension {len(embedding)}, expected {settings.embedding_dimension}.",
    )
    return status | {"status": "passed", "dimension": len(embedding)}


def _run_llm_validation(settings: Settings, evidence: list[dict]) -> dict[str, Any]:
    status = llm_validation_status(settings)
    if status["status"] != "configured":
        return status
    response = guarded_synthesize_answer(
        question=ANSWERABLE_QUESTION,
        evidence=evidence,
        provider=make_llm_provider(settings),
        min_score=settings.min_retrieval_score,
    )
    _assert(response["llm_synthesis_used"] is True, "Configured LLM provider was not used.")
    _assert(response["evidence"] == evidence, "Guarded synthesis did not preserve evidence.")
    _assert(response["answer"] != INSUFFICIENT_EVIDENCE_MESSAGE, "Configured LLM refused sufficient evidence.")
    return status | {"status": "passed", "model": settings.llm_model}


def _upload_sample_pdf(client: Any) -> dict[str, Any]:
    with SAMPLE_PDF.open("rb") as file_obj:
        response = client.post(
            "/api/documents/upload",
            files={"file": ("sample_tender.pdf", file_obj, "application/pdf")},
        )
    _assert(response.status_code == 201, f"Sample upload failed: {response.text}")
    return response.json()


def _post_json(client: Any, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(path, json=payload)
    _assert(response.status_code == 200, f"{path} failed: {response.text}")
    return response.json()


def _has_pgvector(app) -> bool:
    with app.state.session_factory() as session:
        return bool(session.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")))


def _pgvector_column_type(app) -> str | None:
    with app.state.session_factory() as session:
        return session.scalar(
            text(
                """
                SELECT format_type(a.atttypid, a.atttypmod)
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname = 'document_chunks'
                  AND a.attname = 'embedding_vector'
                  AND NOT a.attisdropped
                """
            )
        )


def _chunk_stats(app, document_id: int) -> dict[str, int]:
    with app.state.session_factory() as session:
        row = session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS chunk_count,
                    COUNT(embedding) AS json_embedding_count,
                    COUNT(embedding_vector) AS vector_embedding_count
                FROM document_chunks
                WHERE document_id = :document_id
                """
            ),
            {"document_id": document_id},
        ).mappings().one()
    return {key: int(value) for key, value in row.items()}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


if __name__ == "__main__":
    sys.exit(main())
