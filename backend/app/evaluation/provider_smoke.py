import json
import re
import sys
from typing import Any

from app.config import Settings
from app.services.embeddings import EmbeddingError, make_embedding_provider
from app.services.llm import LLMError, guarded_synthesize_answer, make_llm_provider
from app.services.retrieval import INSUFFICIENT_EVIDENCE_MESSAGE

OPENAI_COMPATIBLE_ALIASES = {"openai", "openai_compatible", "qwen", "bge"}
LOCAL_EMBEDDING_ALIASES = {"local", "fake", "deterministic"}
LOCAL_LLM_ALIASES = {"local", "local_fake", "fake", "deterministic"}
SMOKE_TEXT = "BidGuard AI provider smoke validation."
SMOKE_QUESTION = "What is the bid deadline?"
SMOKE_EVIDENCE = [
    {
        "document_title": "Provider Smoke Tender",
        "page_number": 1,
        "text": "Bid deadline: 30 July 2026 at 17:00.",
        "score": 0.9,
    }
]
CITATION_PATTERN = re.compile(r"\[(\d+)\]")


class SmokeFailure(RuntimeError):
    pass


def run_smoke(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings()
    return {
        "status": "PASS",
        "embedding_provider_validation": validate_embedding_provider(settings),
        "llm_provider_validation": validate_llm_provider(settings),
    }


def validate_embedding_provider(settings: Settings) -> dict[str, Any]:
    provider = settings.embedding_provider.lower()
    if provider in LOCAL_EMBEDDING_ALIASES:
        embedding_provider = make_embedding_provider(settings)
        embedding = embedding_provider.embed_texts([SMOKE_TEXT])[0]
        _assert_dimension(embedding, settings.embedding_dimension)
        return {
            "status": "passed",
            "mode": "local",
            "provider": settings.embedding_provider,
            "model": embedding_provider.model,
            "dimension": len(embedding),
            "usage": dict(embedding_provider.last_call),
        }

    if provider in OPENAI_COMPATIBLE_ALIASES:
        missing = _missing_embedding_config(settings)
        if missing:
            return {
                "status": "skipped",
                "mode": "openai_compatible",
                "provider": settings.embedding_provider,
                "reason": f"Missing configuration: {', '.join(missing)}",
                "missing": missing,
            }
        try:
            embedding_provider = make_embedding_provider(settings)
            embedding = embedding_provider.embed_texts([SMOKE_TEXT])[0]
        except EmbeddingError as exc:
            raise SmokeFailure(f"Embedding provider validation failed: {exc}") from exc
        _assert_dimension(embedding, settings.embedding_dimension)
        return {
            "status": "passed",
            "mode": "openai_compatible",
            "provider": settings.embedding_provider,
            "model": embedding_provider.model,
            "dimension": len(embedding),
            "usage": dict(embedding_provider.last_call),
        }

    raise SmokeFailure(f"Unsupported EMBEDDING_PROVIDER: {settings.embedding_provider}")


def validate_llm_provider(settings: Settings) -> dict[str, Any]:
    provider = settings.llm_provider.lower()
    if provider in LOCAL_LLM_ALIASES:
        llm_provider = make_llm_provider(settings)
        response = guarded_synthesize_answer(
            question=SMOKE_QUESTION,
            evidence=SMOKE_EVIDENCE,
            provider=llm_provider,
            min_score=settings.min_retrieval_score,
        )
        _assert_valid_synthesis(response, expected_provider_mode="local")
        return {
            "status": "passed",
            "mode": "local",
            "provider": settings.llm_provider,
            "model": llm_provider.model,
            "llm_synthesis_used": response["llm_synthesis_used"],
            "usage": response["provider_usage"],
        }

    if provider in OPENAI_COMPATIBLE_ALIASES:
        missing = _missing_llm_config(settings)
        if missing:
            return {
                "status": "skipped",
                "mode": "openai_compatible",
                "provider": settings.llm_provider,
                "reason": f"Missing configuration: {', '.join(missing)}",
                "missing": missing,
            }
        try:
            llm_provider = make_llm_provider(settings)
            response = guarded_synthesize_answer(
                question=SMOKE_QUESTION,
                evidence=SMOKE_EVIDENCE,
                provider=llm_provider,
                min_score=settings.min_retrieval_score,
                raise_on_provider_error=True,
            )
        except LLMError as exc:
            raise SmokeFailure(f"LLM provider validation failed: {exc}") from exc
        _assert_valid_synthesis(response, expected_provider_mode="openai_compatible")
        return {
            "status": "passed",
            "mode": "openai_compatible",
            "provider": settings.llm_provider,
            "model": llm_provider.model,
            "llm_synthesis_used": response["llm_synthesis_used"],
            "usage": response["provider_usage"],
        }

    raise SmokeFailure(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


def main() -> int:
    try:
        result = run_smoke()
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


def _missing_embedding_config(settings: Settings) -> list[str]:
    missing = []
    if not (settings.embedding_api_key or settings.openai_api_key):
        missing.append("EMBEDDING_API_KEY or OPENAI_API_KEY")
    if not (settings.embedding_base_url or settings.openai_base_url):
        missing.append("EMBEDDING_BASE_URL or OPENAI_BASE_URL")
    if not settings.embedding_model:
        missing.append("EMBEDDING_MODEL")
    return missing


def _missing_llm_config(settings: Settings) -> list[str]:
    missing = []
    if not (settings.llm_api_key or settings.openai_api_key):
        missing.append("LLM_API_KEY or OPENAI_API_KEY")
    if not (settings.llm_base_url or settings.openai_base_url):
        missing.append("LLM_BASE_URL or OPENAI_BASE_URL")
    if not settings.llm_model:
        missing.append("LLM_MODEL")
    return missing


def _assert_dimension(embedding: list[float], expected_dimension: int) -> None:
    if len(embedding) != expected_dimension:
        raise SmokeFailure(
            f"Embedding dimension mismatch: expected {expected_dimension}, got {len(embedding)}."
        )


def _assert_valid_synthesis(response: dict[str, Any], expected_provider_mode: str) -> None:
    if not response.get("answer"):
        raise SmokeFailure("LLM synthesis returned an empty answer.")
    if response.get("answer") == INSUFFICIENT_EVIDENCE_MESSAGE:
        raise SmokeFailure("LLM synthesis refused supplied sufficient evidence.")
    if response.get("evidence") != SMOKE_EVIDENCE:
        raise SmokeFailure("Guarded synthesis did not preserve the supplied evidence list.")
    if response.get("llm_synthesis_used") is not True:
        raise SmokeFailure("Configured LLM provider was not used for supplied sufficient evidence.")
    unsupported = _unsupported_citations(response["answer"], evidence_count=len(SMOKE_EVIDENCE))
    if unsupported:
        raise SmokeFailure(
            f"LLM answer referenced unsupported citation ids: {', '.join(unsupported)}."
        )
    if expected_provider_mode == "openai_compatible" and response.get("synthesis_provider") != "openai_compatible":
        raise SmokeFailure(
            f"Expected openai_compatible synthesis, got {response.get('synthesis_provider')}."
        )


def _unsupported_citations(answer: str, evidence_count: int) -> list[str]:
    unsupported = []
    for match in CITATION_PATTERN.finditer(answer):
        citation_id = int(match.group(1))
        if citation_id < 1 or citation_id > evidence_count:
            unsupported.append(match.group(0))
    return unsupported


if __name__ == "__main__":
    sys.exit(main())
