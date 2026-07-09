import io
import zipfile

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_service_status(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'bidguard.db'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))

    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_document_detail_returns_chunks_for_evidence_review(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'bidguard.db'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    monkeypatch.setenv("EMBEDDING_MODEL", "local-hash-v1")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "16")
    client = TestClient(create_app())

    seed = client.post(
        "/api/dev/seed-text-document",
        json={
            "title": "Chunk Detail Tender",
            "pages": [
                {
                    "page_number": 1,
                    "text": "Project name: Harbor Solar Microgrid Upgrade. Bid deadline: 20 August 2026 at 17:00.",
                },
                {
                    "page_number": 2,
                    "text": "Payment terms: 45 days after valid invoice. Acceptance criteria: commissioning certificate.",
                },
            ],
        },
    )
    assert seed.status_code == 201

    response = client.get(f"/api/documents/{seed.json()['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["chunk_count"] == len(body["chunks"])
    assert body["chunks"][0] == {
        "id": body["chunks"][0]["id"],
        "chunk_index": 0,
        "page_number": 1,
        "text": "Project name: Harbor Solar Microgrid Upgrade. Bid deadline: 20 August 2026 at 17:00.",
        "token_count": 13,
        "embedding_provider": "local",
        "embedding_model": "local-hash-v1",
        "embedding_dimension": 16,
    }
    assert [chunk["page_number"] for chunk in body["chunks"]] == [1, 2]


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


def test_risk_check_returns_rule_categories(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'bidguard.db'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    client = TestClient(create_app())

    seed = client.post(
        "/api/dev/seed-text-document",
        json={
            "title": "Risk Category Tender",
            "pages": [
                {
                    "page_number": 1,
                    "text": "Payment terms require payment within 120 days after invoice. Acceptance criteria are subject to purchaser satisfaction.",
                }
            ],
        },
    )
    assert seed.status_code == 201

    response = client.post("/api/risk-check", json={"document_id": seed.json()["id"]})

    assert response.status_code == 200
    findings = response.json()["findings"]
    assert findings
    assert {finding["category"] for finding in findings}
    payment = next(finding for finding in findings if finding["rule_name"] == "Payment period longer than 90 days")
    assert payment["category"] == "payment_terms"


def test_agent_risk_review_uses_rule_findings_as_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'bidguard.db'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    client = TestClient(create_app())

    seed = client.post(
        "/api/dev/seed-text-document",
        json={
            "title": "Risk Agent Tender",
            "pages": [
                {
                    "page_number": 1,
                    "text": "Payment terms require payment within 120 days after invoice. Acceptance criteria are subject to purchaser satisfaction.",
                }
            ],
        },
    )
    assert seed.status_code == 201

    response = client.post(
        "/api/agent/run",
        json={"objective": "Run a risk review for this tender.", "document_ids": [seed.json()["id"]]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"]["evidence"]
    assert body["answer"]["evidence"][0]["retrieval_method"] == "risk_rule_check_tool"
    tool_names = [call["tool_name"] for call in body["tool_calls"]]
    assert "risk_rule_check_tool" in tool_names
    assert "evidence_search_tool" in tool_names


def test_docx_upload_extracts_text_chunks_and_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'bidguard.db'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    monkeypatch.setenv("EMBEDDING_MODEL", "local-hash-v1")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "16")
    client = TestClient(create_app())

    response = client.post(
        "/api/documents/upload",
        files={
            "file": (
                "demo_contract.docx",
                _minimal_docx(
                    [
                        "Project Title: Solar Microgrid Upgrade",
                        "Procuring Entity: City Energy Department",
                        "Vendor: BrightGrid Pty Ltd",
                        "Closing date: 20 August 2026 at 17:00",
                        "Net 45 days after invoice approval.",
                    ]
                ),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["content_type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert body["page_count"] == 1
    assert body["chunk_count"] >= 1
    assert body["embedding_status"] == "embedded"
    assert body["extracted_fields"]["project_name"]["value"] == "Solar Microgrid Upgrade"
    assert body["extracted_fields"]["buyer"]["value"] == "City Energy Department"
    assert "Net 45 days" in body["chunks"][0]["text"]


def test_document_report_endpoint_exports_markdown_review(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'bidguard.db'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    client = TestClient(create_app())

    seed = client.post(
        "/api/dev/seed-text-document",
        json={
            "title": "Report Tender",
            "pages": [
                {
                    "page_number": 1,
                    "text": "Project name: Report Solar. Payment terms require payment within 120 days after invoice. Acceptance criteria are subject to purchaser satisfaction.",
                }
            ],
        },
    )
    assert seed.status_code == 201
    document_id = seed.json()["id"]

    risk = client.post("/api/risk-check", json={"document_id": document_id})
    assert risk.status_code == 200

    response = client.get(f"/api/documents/{document_id}/report")

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["format"] == "markdown"
    assert "# BidGuard AI Review Report" in body["content"]
    assert "Report Tender" in body["content"]
    assert "Payment period longer than 90 days" in body["content"]
    assert "not professional legal advice" in body["content"]


def _minimal_docx(paragraphs: list[str]) -> io.BytesIO:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs)
        + "</w:body></w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<?xml version='1.0' encoding='UTF-8'?><Types/>")
        archive.writestr("word/document.xml", document_xml)
    buffer.seek(0)
    return buffer
