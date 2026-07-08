import io

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_service_status(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'bidguard.db'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))

    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_agent_run_records_tool_calls_for_question(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'bidguard.db'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    client = TestClient(create_app())

    upload = client.post(
        "/api/documents/upload",
        files={"file": ("sample.pdf", io.BytesIO(b"%PDF-1.4\nnot a real pdf"), "application/pdf")},
    )

    assert upload.status_code == 400

    seed = client.post(
        "/api/dev/seed-text-document",
        json={
            "title": "Sample Tender",
            "pages": [
                {
                    "page_number": 1,
                    "text": "Project name: Solar Panel Installation. Bid deadline: 30 July 2026 at 17:00. Dispute resolution: arbitration in Sydney.",
                }
            ],
        },
    )
    assert seed.status_code == 201
    document_id = seed.json()["id"]

    response = client.post(
        "/api/agent/run",
        json={"objective": "What is the bid deadline?", "document_ids": [document_id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"]["evidence"][0]["page_number"] == 1
    assert body["tool_calls"][0]["tool_name"] == "evidence_search_tool"

    trace = client.get("/api/agent/runs")
    assert trace.status_code == 200
    assert trace.json()["items"][0]["tool_calls"][0]["tool_name"] == "evidence_search_tool"
