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
    answer_embedding_usage = answer.get("embedding_usage")
    embedding_usage = (
        dict(answer_embedding_usage) if isinstance(answer_embedding_usage, dict) else {}
    )
    if not embedding_usage and evidence and isinstance(evidence[0].get("embedding_usage"), dict):
        embedding_usage = dict(evidence[0]["embedding_usage"])
    llm_usage = answer.get("provider_usage")
    llm_usage = dict(llm_usage) if isinstance(llm_usage, dict) else {}
    estimated_cost = float(embedding_usage.get("estimated_cost_usd", 0.0)) + float(
        llm_usage.get("estimated_cost_usd", 0.0)
    )
    return {
        "retrieval_methods": methods,
        "average_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
        "evidence_count": len(evidence),
        "llm_synthesis_used": bool(answer.get("llm_synthesis_used", False)),
        "synthesis_provider": answer.get("synthesis_provider"),
        "embedding_usage": embedding_usage,
        "llm_usage": llm_usage,
        "total_tokens": int(embedding_usage.get("total_tokens", 0))
        + int(llm_usage.get("total_tokens", 0)),
        "estimated_cost_usd": round(estimated_cost, 8),
    }


def database_mode_label(dialect_name: str, has_pgvector: bool) -> str:
    if dialect_name == "postgresql":
        return "postgres_pgvector" if has_pgvector else "postgres"
    return dialect_name
