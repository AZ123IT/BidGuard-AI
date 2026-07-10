import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.evaluation.metrics import score_eval_case, score_retrieval_ranking
from app.evaluation.observability import (
    database_mode_label,
    summarize_answer_observability,
)
from app.evaluation.pgvector_smoke import (
    SmokeFailure,
    database_url_is_postgres,
    embedding_validation_status,
    llm_validation_status,
    prepare_pgvector_app,
)
from app.evaluation.run_eval import DEMO_CASES, load_eval_cases, render_failure_analysis
from app.evaluation.run_retrieval_benchmark import (
    RETRIEVAL_BENCHMARK_CASES,
    benchmark_exit_code,
    render_benchmark_markdown,
    run_benchmark,
)
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


def test_retrieval_prefers_acceptance_criteria_clause_match():
    provider = LocalEmbeddingProvider(dimension=16, model="local-test")
    question = "What acceptance criteria are in the contract draft?"
    chunks = [
        {
            "id": 1,
            "document_id": 2,
            "document_title": "Contract Draft",
            "page_number": 1,
            "text": "Document type: Contract draft. Project name: Harbor Solar Microgrid Upgrade. Contract amount: AUD 1,250,000.",
            "embedding": provider.embed_texts(["Document type: Contract draft. Project name: Harbor Solar Microgrid Upgrade. Contract amount: AUD 1,250,000."])[0],
        },
        {
            "id": 2,
            "document_id": 2,
            "document_title": "Contract Draft",
            "page_number": 2,
            "text": "Acceptance criteria: Site acceptance requires successful commissioning and safety certificate delivery.",
            "embedding": provider.embed_texts(["Acceptance criteria: Site acceptance requires successful commissioning and safety certificate delivery."])[0],
        },
    ]

    results = retrieve_relevant_chunks(
        question,
        chunks,
        limit=2,
        query_embedding=provider.embed_texts([question])[0],
        retrieval_method="hybrid_fallback",
    )

    assert results[0]["page_number"] == 2


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


def test_guarded_synthesis_skips_llm_when_identifier_value_is_missing():
    class FailingProvider:
        provider_name = "openai_compatible"
        last_call = {}

        def synthesize(self, question, evidence):
            raise AssertionError("LLM must not be called without identifier evidence")

    response = guarded_synthesize_answer(
        question="What is SunPeak Energy's vendor tax identification number?",
        evidence=[
            {
                "document_title": "Contract Draft",
                "page_number": 1,
                "text": "Supplier: SunPeak Energy Pty Ltd. Contract amount: AUD 1,250,000.",
                "score": 0.82,
                "similarity_score": 0.61,
                "keyword_score": 0.3,
                "keyword_coverage": 0.3,
                "has_keyword_match": True,
                "embedding_provider": "openai_compatible",
                "retrieval_method": "pgvector",
            }
        ],
        provider=FailingProvider(),
        min_score=0.05,
    )

    assert response["answer"] == INSUFFICIENT_EVIDENCE_MESSAGE
    assert response["llm_synthesis_used"] is False
    assert response["evidence"] == []


def test_insufficient_answer_preserves_embedding_usage_for_cost_accounting():
    provider = DeterministicLLMProvider(model="fake")
    response = guarded_synthesize_answer(
        question="What is the missing identifier?",
        evidence=[
            {
                "document_title": "Tender A",
                "page_number": 1,
                "text": "Payment terms: 45 days.",
                "score": 0.01,
                "embedding_usage": {
                    "provider": "openai_compatible",
                    "model": "embedding-model",
                    "total_tokens": 7,
                    "estimated_cost_usd": 0.000001,
                },
            }
        ],
        provider=provider,
        min_score=0.05,
    )

    observability = summarize_answer_observability(response)

    assert response["answer"] == INSUFFICIENT_EVIDENCE_MESSAGE
    assert response["llm_synthesis_used"] is False
    assert observability["embedding_usage"]["total_tokens"] == 7
    assert observability["total_tokens"] == 7


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
    assert seed.json()["embedding_usage"]["provider"] == "local"
    assert seed.json()["embedding_usage"]["total_tokens"] > 0
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


def test_answer_keyword_metric_allows_filler_words_but_rejects_swapped_values():
    case = {
        "eval_type": "qa",
        "expected_answer_keywords": ["Price 40%", "technical compliance 35%"],
    }
    correct = score_eval_case(
        case,
        {
            "answer": "Price is weighted at 40% and technical compliance is weighted at 35%.",
            "evidence": [{"page_number": 1}],
        },
    )
    swapped = score_eval_case(
        case,
        {
            "answer": "Price is weighted at 35% and technical compliance is weighted at 40%.",
            "evidence": [{"page_number": 1}],
        },
    )

    assert correct["answer_keyword_hit"] is True
    assert swapped["answer_keyword_hit"] is False


def test_eval_observability_reports_retrieval_scores_and_modes():
    observability = summarize_answer_observability(
        {
            "answer": "Based on Tender A page 1, the bid deadline is 30 July 2026.",
            "evidence": [
                {"page_number": 1, "score": 0.8, "retrieval_method": "pgvector"},
                {"page_number": 2, "score": 0.4, "retrieval_method": "pgvector"},
            ],
            "llm_synthesis_used": True,
            "synthesis_provider": "local_fake",
        }
    )

    assert observability["retrieval_methods"] == ["pgvector"]
    assert observability["average_score"] == 0.6
    assert observability["evidence_count"] == 2
    assert observability["llm_synthesis_used"] is True
    assert observability["synthesis_provider"] == "local_fake"
    assert database_mode_label("postgresql", has_pgvector=True) == "postgres_pgvector"
    assert database_mode_label("postgresql", has_pgvector=False) == "postgres"
    assert database_mode_label("sqlite", has_pgvector=False) == "sqlite"


def test_pgvector_smoke_helpers_detect_postgres_and_skip_local_providers():
    settings = Settings(
        database_url="sqlite:///./bidguard.db",
        embedding_provider="local",
        llm_provider="local_fake",
    )

    assert database_url_is_postgres("postgresql+psycopg://bidguard:bidguard@localhost/bidguard")
    assert not database_url_is_postgres(settings.database_url)
    assert embedding_validation_status(settings)["status"] == "skipped"
    assert llm_validation_status(settings)["status"] == "skipped"


def test_pgvector_preflight_rejects_sqlite_before_app_start():
    settings = Settings(database_url="sqlite:///./bidguard.db")

    with pytest.raises(SmokeFailure, match="must point to PostgreSQL"):
        prepare_pgvector_app(settings)


def test_demo_eval_dataset_loads_required_case_types():
    cases = load_eval_cases(DEMO_CASES)
    eval_types = {case["eval_type"] for case in cases}

    assert 30 <= len(cases) <= 50
    assert {"qa", "insufficient", "risk", "diff", "agent"}.issubset(eval_types)
    assert all(case.get("id") for case in cases)
    assert any(case.get("expected_risk_categories") for case in cases)
    assert any(case.get("expected_diff_fields") for case in cases)
    assert any(case.get("expected_tools") for case in cases)
    assert any(case.get("case_category") == "hard_negative" for case in cases)
    assert any(case.get("case_category") == "prompt_injection" for case in cases)


def test_retrieval_ranking_metrics_report_recall_mrr_and_ndcg():
    ranking = score_retrieval_ranking(
        {
            "expected_evidence": [
                {"document_title": "Contract Draft", "page_number": 2},
            ]
        },
        [
            {"document_title": "Contract Draft", "page_number": 1},
            {"document_title": "Contract Draft", "page_number": 2},
        ],
    )

    assert ranking["applicable"] is True
    assert ranking["recall_at_1"] == 0.0
    assert ranking["recall_at_3"] == 1.0
    assert ranking["recall_at_5"] == 1.0
    assert ranking["reciprocal_rank"] == 0.5
    assert ranking["ndcg_at_5"] == 0.6309


def test_failure_analysis_lists_failed_metrics_and_residual_risks():
    report = {
        "total": 2,
        "passed": 1,
        "failed": 1,
        "pass_rate": 0.5,
        "provider_mode": {"embedding_provider": "local", "llm_provider": "local_fake"},
        "database_mode": "sqlite",
        "retrieval_metrics": {"mrr": 0.5, "recall_at_5": 0.5, "ndcg_at_5": 0.4},
        "results": [
            {
                "id": "hard_negative_deadline",
                "name": "Hard negative deadline",
                "eval_type": "qa",
                "case_category": "hard_negative",
                "question": "What is the Harbor project deadline?",
                "answer": "The response omitted the closing time.",
                "passed": False,
                "metrics": {"retrieval_hit": False, "answer_keyword_hit": False},
                "ranking": {"reciprocal_rank": 0.0},
            }
        ],
    }

    rendered = render_failure_analysis(report)

    assert "hard_negative_deadline" in rendered
    assert "retrieval_hit" in rendered
    assert "The response omitted the closing time." in rendered
    assert "Real-provider semantic quality is not proven" in rendered


def test_retrieval_benchmark_reports_answer_correctness_without_real_keys():
    report = run_benchmark(
        DEMO_CASES,
        settings=Settings(
            database_url="sqlite:///./bidguard.db",
            embedding_provider="local",
            embedding_dimension=16,
            llm_provider="local_fake",
        ),
    )

    assert report["modes"]["keyword"]["status"] == "passed"
    assert report["modes"]["keyword"]["answer_correctness"] >= 0.0
    assert report["modes"]["local_deterministic"]["answer_correctness"] >= 0.0
    assert report["modes"]["configured_real_embedding"]["status"] == "skipped"
    assert report["modes"]["postgres_pgvector"]["status"] == "skipped"


def test_retrieval_benchmark_dataset_contains_challenging_case_categories():
    cases = load_eval_cases(RETRIEVAL_BENCHMARK_CASES)
    categories = {case.get("case_category") for case in cases}

    assert 12 <= len(cases) <= 20
    assert {"direct", "paraphrase", "hard_negative", "prompt_injection"}.issubset(categories)
    assert all(case.get("expected_evidence") for case in cases)
    assert all(case.get("document_titles") for case in cases)


def test_retrieval_benchmark_scores_only_production_usable_evidence():
    report = run_benchmark(
        RETRIEVAL_BENCHMARK_CASES,
        settings=Settings(
            database_url="sqlite:///./bidguard.db",
            embedding_provider="local",
            embedding_dimension=16,
            llm_provider="local_fake",
        ),
    )
    keyword = report["modes"]["keyword"]

    assert keyword["recall_at_1"] < 1.0
    assert keyword["evidence_page_hit"] < 1.0
    assert keyword["answer_correctness"] < 1.0


def test_retrieval_benchmark_required_modes_fail_when_real_rows_are_skipped():
    report = {
        "modes": {
            "configured_real_embedding": {"status": "skipped"},
            "postgres_pgvector": {"status": "skipped"},
        }
    }

    assert benchmark_exit_code(report, require_real=False, require_pgvector=False) == 0
    assert benchmark_exit_code(report, require_real=True, require_pgvector=False) == 2
    assert benchmark_exit_code(report, require_real=False, require_pgvector=True) == 2


def test_retrieval_benchmark_markdown_reports_executed_real_rows():
    passed_mode = {
        "status": "passed",
        "recall_at_1": 0.5,
        "recall_at_3": 0.75,
        "recall_at_5": 0.75,
        "mrr": 0.6,
        "ndcg_at_5": 0.65,
        "evidence_page_hit": 0.75,
        "answer_correctness": 0.5,
        "average_query_latency_ms": 10.0,
        "failed_case_ids": ["hard_case"],
        "usage": {"estimated_cost_usd": 0.001},
    }
    report = {
        "generated_at": "2026-07-10T00:00:00+00:00",
        "dataset": "retrieval_benchmark.json",
        "case_count": 1,
        "modes": {
            "configured_real_embedding": passed_mode,
            "postgres_pgvector": passed_mode,
        },
    }

    rendered = render_benchmark_markdown(report)

    assert "real-provider and pgvector rows executed" in rendered.lower()
    assert "remain explicitly skipped" not in rendered.lower()


def test_eval_metrics_cover_insufficient_tools_risk_and_diff():
    insufficient = score_eval_case(
        {"eval_type": "insufficient", "expected_insufficient_evidence": True},
        {"answer": INSUFFICIENT_EVIDENCE_MESSAGE, "evidence": []},
    )
    legacy_qa = score_eval_case(
        {"eval_type": "qa", "expected_tools": ["evidence_search_tool"]},
        {"answer": "Found evidence.", "evidence": [{"page_number": 1, "score": 0.9}]},
    )
    tool = score_eval_case(
        {"eval_type": "agent", "expected_tools": ["evidence_search_tool"]},
        {"answer": "Found evidence.", "evidence": [{"page_number": 1, "score": 0.9}]},
        tool_calls=[{"tool_name": "evidence_search_tool"}],
    )
    risk = score_eval_case(
        {
            "eval_type": "risk",
            "expected_risk_categories": ["payment_terms"],
            "expected_risk_keywords": ["120 days"],
        },
        {"answer": "", "evidence": []},
        risk_findings=[
            {
                "category": "payment_terms",
                "rule_name": "Payment period longer than 90 days",
                "evidence_text": "Payment within 120 days after invoice.",
            }
        ],
    )
    diff = score_eval_case(
        {
            "eval_type": "diff",
            "expected_diff_fields": [{"field": "contract_amount", "status": "changed"}],
            "expected_diff_keywords": ["AUD 1,250,000", "AUD 1,350,000"],
        },
        {"answer": "", "evidence": []},
        diff_rows=[
            {
                "field": "contract_amount",
                "status": "changed",
                "document_a_value": "AUD 1,250,000",
                "document_b_value": "AUD 1,350,000",
            }
        ],
    )

    assert insufficient["insufficient_evidence_hit"] is True
    assert insufficient["retrieval_hit"] is True
    assert legacy_qa["tool_call_hit"] is None
    assert tool["tool_call_hit"] is True
    assert risk["risk_category_hit"] is True
    assert risk["risk_keyword_hit"] is True
    assert diff["diff_field_hit"] is True
    assert diff["diff_keyword_hit"] is True


def test_eval_metrics_mark_unrelated_checks_as_not_applicable():
    metrics = score_eval_case(
        {
            "eval_type": "risk",
            "expected_risk_categories": ["payment_terms"],
        },
        {"answer": "", "evidence": []},
        risk_findings=[{"category": "payment_terms"}],
    )

    assert metrics["risk_category_hit"] is True
    assert metrics["retrieval_hit"] is None
    assert metrics["answer_keyword_hit"] is None
    assert metrics["tool_call_hit"] is None
    assert metrics["diff_field_hit"] is None
