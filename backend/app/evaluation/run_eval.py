import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.evaluation.metrics import score_eval_case
from app.evaluation.observability import database_mode_label, summarize_answer_observability
from app.main import create_app

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CASES = ROOT / "data" / "eval_cases" / "rag_smoke.json"
DEMO_CASES = ROOT / "data" / "eval_cases" / "rag_demo.json"
SAMPLE_DOC_DIRS = [
    ROOT / "data" / "sample_docs",
    ROOT / "data" / "sample_docs" / "demo_pack",
]
PAGE_MARKER = re.compile(r"^=== Page (\d+) ===$")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = run_eval(args.dataset)
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(rendered + "\n")
    return 0 if report["failed"] == 0 else 1


def run_eval(dataset: Path = DEFAULT_CASES) -> dict[str, Any]:
    cases = load_eval_cases(dataset)
    app = create_app()
    client = TestClient(app)
    document_ids = ensure_eval_documents(client, cases)
    results = [_run_case(client, case, document_ids) for case in cases]

    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    return {
        "passed": passed,
        "failed": total - passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
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
        "metric_summary": _metric_summary(results),
        "failed_cases": [result["id"] for result in results if not result["passed"]],
        "results": results,
    }


def load_eval_cases(dataset: Path) -> list[dict[str, Any]]:
    cases = json.loads(dataset.read_text())
    if not isinstance(cases, list):
        raise ValueError(f"Eval dataset must be a list: {dataset}")
    for index, case in enumerate(cases, start=1):
        if "eval_type" not in case:
            raise ValueError(f"Eval case {index} is missing eval_type.")
        case.setdefault("id", case.get("name", f"case_{index}"))
        case.setdefault("name", case["id"])
    return cases


def ensure_eval_documents(client: TestClient, cases: list[dict[str, Any]]) -> dict[str, int]:
    existing = client.get("/api/documents").json()["items"]
    by_title: dict[str, int] = {}
    for document in existing:
        by_title.setdefault(document["title"], document["id"])

    for title in sorted(_required_document_titles(cases)):
        pages = _load_document_pages(title)
        response = client.post(
            "/api/dev/seed-text-document",
            json={"title": title, "pages": pages},
        )
        if response.status_code != 201:
            raise RuntimeError(f"Could not seed eval document {title}: {response.text}")
        by_title[title] = response.json()["id"]
    return by_title


def _run_case(client: TestClient, case: dict[str, Any], document_ids: dict[str, int]) -> dict[str, Any]:
    eval_type = case.get("eval_type", "qa")
    if eval_type in {"qa", "insufficient"}:
        answer = _run_qa_case(client, case, document_ids)
        tool_calls: list[dict] = []
        risk_findings: list[dict] = []
        diff_rows: list[dict] = []
    elif eval_type == "agent":
        answer, tool_calls = _run_agent_case(client, case, document_ids)
        risk_findings = []
        diff_rows = []
    elif eval_type == "risk":
        risk_findings = _run_risk_case(client, case, document_ids)
        answer = _risk_answer(risk_findings)
        tool_calls = []
        diff_rows = []
    elif eval_type == "diff":
        diff_rows = _run_diff_case(client, case, document_ids)
        answer = _diff_answer(diff_rows)
        tool_calls = []
        risk_findings = []
    else:
        raise ValueError(f"Unsupported eval_type: {eval_type}")

    metrics = score_eval_case(
        case,
        answer,
        tool_calls=tool_calls,
        risk_findings=risk_findings,
        diff_rows=diff_rows,
    )
    return {
        "id": case["id"],
        "name": case["name"],
        "eval_type": eval_type,
        "passed": all(metrics.values()),
        "metrics": metrics,
        "observability": summarize_answer_observability(answer),
        "tool_calls": [call.get("tool_name") for call in tool_calls],
    }


def _run_qa_case(client: TestClient, case: dict[str, Any], document_ids: dict[str, int]) -> dict[str, Any]:
    response = client.post(
        "/api/qa",
        json={
            "question": case["question"],
            "document_ids": _case_document_ids(case, document_ids),
        },
    )
    _assert_response_ok(response, case)
    return response.json()


def _run_agent_case(
    client: TestClient,
    case: dict[str, Any],
    document_ids: dict[str, int],
) -> tuple[dict[str, Any], list[dict]]:
    payload: dict[str, Any] = {
        "objective": case["question"],
        "document_ids": _case_document_ids(case, document_ids),
    }
    if case.get("document_a_title") and case.get("document_b_title"):
        payload["document_a_id"] = document_ids[case["document_a_title"]]
        payload["document_b_id"] = document_ids[case["document_b_title"]]
    response = client.post("/api/agent/run", json=payload)
    _assert_response_ok(response, case)
    body = response.json()
    return body["answer"], body["tool_calls"]


def _run_risk_case(client: TestClient, case: dict[str, Any], document_ids: dict[str, int]) -> list[dict]:
    response = client.post(
        "/api/risk-check",
        json={"document_id": document_ids[case["document_title"]]},
    )
    _assert_response_ok(response, case)
    return response.json()["findings"]


def _run_diff_case(client: TestClient, case: dict[str, Any], document_ids: dict[str, int]) -> list[dict]:
    response = client.post(
        "/api/diff",
        json={
            "document_a_id": document_ids[case["document_a_title"]],
            "document_b_id": document_ids[case["document_b_title"]],
        },
    )
    _assert_response_ok(response, case)
    return response.json()["differences"]


def _risk_answer(findings: list[dict]) -> dict[str, Any]:
    lines = [
        " | ".join(
            str(part)
            for part in [
                finding.get("category"),
                finding.get("rule_name"),
                finding.get("severity"),
                finding.get("explanation"),
                finding.get("evidence_text"),
            ]
            if part
        )
        for finding in findings
    ]
    return {
        "answer": "\n".join(lines),
        "evidence": [],
        "confidence": 1.0 if findings else 0.0,
        "llm_synthesis_used": False,
        "synthesis_provider": None,
    }


def _diff_answer(rows: list[dict]) -> dict[str, Any]:
    lines = [
        " | ".join(
            str(part)
            for part in [
                row.get("field"),
                row.get("status"),
                row.get("document_a_value"),
                row.get("document_b_value"),
            ]
            if part
        )
        for row in rows
    ]
    return {
        "answer": "\n".join(lines),
        "evidence": [],
        "confidence": 1.0 if rows else 0.0,
        "llm_synthesis_used": False,
        "synthesis_provider": None,
    }


def _case_document_ids(case: dict[str, Any], document_ids: dict[str, int]) -> list[int]:
    titles = []
    if case.get("document_title"):
        titles.append(case["document_title"])
    titles.extend(case.get("document_titles", []))
    return [document_ids[title] for title in titles]


def _required_document_titles(cases: list[dict[str, Any]]) -> set[str]:
    titles: set[str] = set()
    for case in cases:
        if case.get("document_title"):
            titles.add(case["document_title"])
        titles.update(case.get("document_titles", []))
        if case.get("document_a_title"):
            titles.add(case["document_a_title"])
        if case.get("document_b_title"):
            titles.add(case["document_b_title"])
    return titles or {"sample_tender"}


def _load_document_pages(title: str) -> list[dict[str, Any]]:
    for directory in SAMPLE_DOC_DIRS:
        path = directory / f"{title}.txt"
        if path.exists():
            return _parse_pages(path.read_text())
    raise FileNotFoundError(f"No sample document text found for title: {title}")


def _parse_pages(text_body: str) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    current_page = 1
    current_lines: list[str] = []
    marker_seen = False
    for line in text_body.splitlines():
        marker = PAGE_MARKER.match(line.strip())
        if marker:
            if marker_seen or current_lines:
                pages.append({"page_number": current_page, "text": "\n".join(current_lines).strip()})
            current_page = int(marker.group(1))
            current_lines = []
            marker_seen = True
        else:
            current_lines.append(line)
    if current_lines or not pages:
        pages.append({"page_number": current_page, "text": "\n".join(current_lines).strip()})
    return [page for page in pages if page["text"]]


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


def _metric_summary(results: list[dict]) -> dict[str, dict[str, float | int]]:
    metric_names = sorted({name for result in results for name in result["metrics"]})
    summary = {}
    for name in metric_names:
        total = sum(1 for result in results if name in result["metrics"])
        passed = sum(1 for result in results if result["metrics"].get(name) is True)
        summary[name] = {
            "passed": passed,
            "total": total,
            "rate": round(passed / total, 4) if total else 0.0,
        }
    return summary


def _assert_response_ok(response, case: dict[str, Any]) -> None:
    if response.status_code >= 400:
        raise RuntimeError(f"Eval case {case['id']} failed API call: {response.text}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BidGuard AI RAG evaluation cases.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_CASES,
        help="Path to eval dataset JSON.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional path for writing the full JSON eval report.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
