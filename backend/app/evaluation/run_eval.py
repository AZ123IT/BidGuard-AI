import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.evaluation.metrics import score_eval_case
from app.evaluation.observability import database_mode_label, summarize_answer_observability
from app.main import create_app

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CASES = ROOT / "data" / "eval_cases" / "rag_smoke.json"
SAMPLE_TEXT = ROOT / "data" / "sample_docs" / "sample_tender.txt"


def main() -> None:
    cases = json.loads(DEFAULT_CASES.read_text())
    app = create_app()
    client = TestClient(app)
    document_ids = _ensure_sample_documents(client)
    results = []

    for case in cases:
        title = case.get("document_title", "sample_tender")
        document_id = document_ids[title]
        if case.get("expected_tools"):
            response = client.post(
                "/api/agent/run",
                json={"objective": case["question"], "document_ids": [document_id]},
            )
            payload = response.json()
            answer = payload["answer"]
            tool_calls = payload["tool_calls"]
        else:
            response = client.post(
                "/api/qa",
                json={"question": case["question"], "document_ids": [document_id]},
            )
            answer = response.json()
            tool_calls = []
        metrics = score_eval_case(case, answer, tool_calls)
        results.append(
            {
                "name": case["name"],
                "metrics": metrics,
                "observability": summarize_answer_observability(answer),
            }
        )

    passed = sum(all(item["metrics"].values()) for item in results)
    print(
        json.dumps(
            {
                "passed": passed,
                "total": len(results),
                "provider_mode": {
                    "embedding_provider": app.state.settings.embedding_provider,
                    "embedding_model": app.state.settings.embedding_model,
                    "llm_provider": app.state.settings.llm_provider,
                    "llm_model": app.state.settings.llm_model,
                },
                "database_mode": database_mode_label(
                    app.state.engine.dialect.name,
                    has_pgvector=_has_pgvector(app),
                ),
                "average_score": _average_score(results),
                "retrieval_methods": sorted(
                    {
                        method
                        for result in results
                        for method in result["observability"]["retrieval_methods"]
                    }
                ),
                "results": results,
            },
            indent=2,
        )
    )


def _ensure_sample_documents(client: TestClient) -> dict[str, int]:
    existing = client.get("/api/documents").json()["items"]
    by_title = {document["title"]: document["id"] for document in existing}
    if "sample_tender" not in by_title:
        response = client.post(
            "/api/dev/seed-text-document",
            json={
                "title": "sample_tender",
                "pages": [{"page_number": 1, "text": SAMPLE_TEXT.read_text()}],
            },
        )
        by_title["sample_tender"] = response.json()["id"]
    return by_title


def _has_pgvector(app) -> bool:
    if app.state.engine.dialect.name != "postgresql":
        return False
    with app.state.session_factory() as session:
        return bool(session.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")))


def _average_score(results: list[dict]) -> float:
    scores = [
        result["observability"]["average_score"]
        for result in results
        if result["observability"]["evidence_count"]
    ]
    return round(sum(scores) / len(scores), 4) if scores else 0.0


if __name__ == "__main__":
    main()
