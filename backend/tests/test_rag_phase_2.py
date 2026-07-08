from fastapi.testclient import TestClient

from app.evaluation.metrics import score_eval_case
from app.main import create_app
from app.services.embeddings import LocalEmbeddingProvider, cosine_similarity
from app.services.llm import DeterministicLLMProvider, guarded_synthesize_answer
from app.services.retrieval import (
    INSUFFICIENT_EVIDENCE_MESSAGE,
    retrieve_relevant_chunks,
)


def test_local_embedding_provider_is_deterministic_and_normalized():
    provider = LocalEmbeddingProvider(dimension=16, model="local-test")

    first = provider.embed_texts(["bid deadline 30 July"])[0]
    second = provider.embed_texts(["bid deadline 30 July"])[0]
    unrelated = provider.embed_texts(["insurance policy number"])[0]

    assert first == second
    assert len(first) == 16
    assert cosine_similarity(first, second) == 1.0
    assert cosine_similarity(first, unrelated) < 0.9


def test_retrieval_returns_hybrid_metadata_with_similarity_scores():
    provider = LocalEmbeddingProvider(dimension=16, model="local-test")
    question = "What is the bid deadline?"
    chunks = [
        {
            "id": 1,
            "document_id": 2,
            "document_title": "Tender A",
            "page_number": 3,
            "text": "The bid deadline is 30 July 2026 at 17:00.",
            "embedding": provider.embed_texts(["The bid deadline is 30 July 2026 at 17:00."])[0],
        },
        {
            "id": 2,
            "document_id": 2,
            "document_title": "Tender A",
            "page_number": 4,
            "text": "Warranty service must be available for two years.",
            "embedding": provider.embed_texts(["Warranty service must be available for two years."])[0],
        },
    ]

    results = retrieve_relevant_chunks(
        question,
        chunks,
        limit=2,
        query_embedding=provider.embed_texts([question])[0],
        retrieval_method="hybrid_fallback",
    )

    assert results[0]["chunk_id"] == 1
    assert results[0]["retrieval_method"] == "hybrid_fallback"
    assert results[0]["similarity_score"] > 0
    assert results[0]["keyword_score"] > 0
    assert results[0]["score"] >= results[0]["similarity_score"] * 0.4


def test_guarded_synthesis_skips_llm_when_evidence_is_weak():
    provider = DeterministicLLMProvider(model="fake")

    response = guarded_synthesize_answer(
        question="What is the insurance policy number?",
        evidence=[],
        provider=provider,
        min_score=0.05,
    )

    assert response["answer"] == INSUFFICIENT_EVIDENCE_MESSAGE
    assert response["llm_synthesis_used"] is False
    assert response["evidence"] == []


def test_guarded_synthesis_uses_fake_provider_only_with_sufficient_evidence():
    provider = DeterministicLLMProvider(model="fake")
    evidence = [
        {
            "document_title": "Tender A",
            "page_number": 1,
            "text": "Bid deadline: 30 July 2026 at 17:00.",
            "score": 0.8,
        }
    ]

    response = guarded_synthesize_answer(
        question="What is the bid deadline?",
        evidence=evidence,
        provider=provider,
        min_score=0.05,
    )

    assert "30 July 2026" in response["answer"]
    assert response["llm_synthesis_used"] is True
    assert response["synthesis_provider"] == "local_fake"


def test_seed_document_stores_chunk_embeddings_and_agent_logs_synthesis(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'bidguard.db'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "16")
    monkeypatch.setenv("LLM_PROVIDER", "local_fake")
    client = TestClient(create_app())

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
    assert seed.json()["embedding_status"] == "embedded"
    document_id = seed.json()["id"]

    qa = client.post(
        "/api/qa",
        json={"question": "What is the bid deadline?", "document_ids": [document_id]},
    )
    assert qa.status_code == 200
    qa_body = qa.json()
    assert qa_body["evidence"][0]["retrieval_method"] == "hybrid_fallback"
    assert qa_body["llm_synthesis_used"] is True

    response = client.post(
        "/api/agent/run",
        json={"objective": "What is the bid deadline?", "document_ids": [document_id]},
    )
    assert response.status_code == 200
    tool_names = [call["tool_name"] for call in response.json()["tool_calls"]]
    assert tool_names == ["evidence_search_tool", "guarded_llm_synthesis"]
    synthesis_call = response.json()["tool_calls"][1]
    assert synthesis_call["status"] == "success"
    assert synthesis_call["evidence_count"] == 1


def test_eval_metrics_score_retrieval_answer_and_tool_calls():
    result = score_eval_case(
        case={
            "question": "What is the bid deadline?",
            "expected_evidence_page": 1,
            "expected_answer_keywords": ["30 July 2026"],
            "expected_tools": ["evidence_search_tool", "guarded_llm_synthesis"],
            "eval_type": "qa",
        },
        answer={
            "answer": "The bid deadline is 30 July 2026 at 17:00.",
            "evidence": [{"page_number": 1, "score": 0.9}],
        },
        tool_calls=[
            {"tool_name": "evidence_search_tool"},
            {"tool_name": "guarded_llm_synthesis"},
        ],
    )

    assert result["retrieval_hit"] is True
    assert result["evidence_page_hit"] is True
    assert result["answer_keyword_hit"] is True
    assert result["tool_call_hit"] is True
