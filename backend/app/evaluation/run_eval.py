import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.evaluation.metrics import score_eval_case
from app.main import create_app

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CASES = ROOT / "data" / "eval_cases" / "rag_smoke.json"
SAMPLE_TEXT = ROOT / "data" / "sample_docs" / "sample_tender.txt"


def main() -> None:
    cases = json.loads(DEFAULT_CASES.read_text())
    client = TestClient(create_app())
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
        results.append({"name": case["name"], "metrics": metrics})

    passed = sum(all(item["metrics"].values()) for item in results)
    print(json.dumps({"passed": passed, "total": len(results), "results": results}, indent=2))


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


if __name__ == "__main__":
    main()
