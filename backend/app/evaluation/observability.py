from typing import Any


def summarize_answer_observability(answer: dict[str, Any]) -> dict[str, Any]:
    evidence = answer.get("evidence", [])
    scores = [float(item.get("score", 0.0)) for item in evidence]
    methods = sorted(
        {
            item.get("retrieval_method")
            for item in evidence
            if isinstance(item.get("retrieval_method"), str)
        }
    )
    return {
        "retrieval_methods": methods,
        "average_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
        "evidence_count": len(evidence),
        "llm_synthesis_used": bool(answer.get("llm_synthesis_used", False)),
        "synthesis_provider": answer.get("synthesis_provider"),
    }


def database_mode_label(dialect_name: str, has_pgvector: bool) -> str:
    if dialect_name == "postgresql":
        return "postgres_pgvector" if has_pgvector else "postgres"
    return dialect_name
