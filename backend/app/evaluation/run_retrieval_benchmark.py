import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from app.config import Settings
from app.evaluation.metrics import score_eval_case, score_retrieval_ranking
from app.evaluation.run_eval import (
    _case_document_ids,
    _load_document_pages,
    ensure_eval_documents,
    load_eval_cases,
)
from app.services.chunking import chunk_pages
from app.services.embeddings import LocalEmbeddingProvider, make_embedding_provider
from app.services.retrieval import (
    build_evidence_answer,
    filter_usable_evidence,
    retrieve_document_evidence,
    retrieve_relevant_chunks,
)

REAL_PROVIDER_ALIASES = {"openai", "openai_compatible", "qwen", "bge"}
RETRIEVAL_BENCHMARK_CASES = Path(__file__).resolve().parents[3] / "data/eval_cases/retrieval_benchmark.json"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    settings = Settings()
    report = run_benchmark(args.dataset, settings=settings)
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(rendered + "\n")
    if args.output_markdown:
        args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.output_markdown.write_text(render_benchmark_markdown(report))
    return benchmark_exit_code(
        report,
        require_real=args.require_real,
        require_pgvector=args.require_pgvector,
    )


def benchmark_exit_code(
    report: dict[str, Any],
    *,
    require_real: bool,
    require_pgvector: bool,
) -> int:
    modes = report["modes"]
    if require_real and modes["configured_real_embedding"].get("status") != "passed":
        return 2
    if require_pgvector and modes["postgres_pgvector"].get("status") != "passed":
        return 2
    return 0


def run_benchmark(
    dataset: Path = RETRIEVAL_BENCHMARK_CASES,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings()
    cases = [case for case in load_eval_cases(dataset) if _is_retrieval_case(case)]
    corpus = _load_corpus(cases)
    modes: dict[str, dict[str, Any]] = {
        "keyword": _run_in_memory_mode(
            cases,
            corpus,
            provider=None,
            method="keyword",
            min_score=settings.min_retrieval_score,
        ),
        "local_deterministic": _run_in_memory_mode(
            cases,
            corpus,
            provider=LocalEmbeddingProvider(
                dimension=settings.embedding_dimension,
                model="local-hash-v1",
            ),
            method="local_hybrid",
            min_score=settings.min_retrieval_score,
        ),
    }

    real_status = _real_provider_status(settings)
    if real_status["status"] == "configured":
        modes["configured_real_embedding"] = _run_in_memory_mode(
            cases,
            corpus,
            provider=make_embedding_provider(settings),
            method="configured_real_hybrid",
            min_score=settings.min_retrieval_score,
        )
    else:
        modes["configured_real_embedding"] = real_status

    modes["postgres_pgvector"] = _run_pgvector_mode(cases, settings)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": str(dataset),
        "case_count": len(cases),
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "embedding_dimension": settings.embedding_dimension,
        "modes": modes,
    }


def _run_in_memory_mode(
    cases: list[dict[str, Any]],
    corpus: list[dict[str, Any]],
    provider,
    method: str,
    min_score: float,
) -> dict[str, Any]:
    prepared_corpus = [dict(chunk) for chunk in corpus]
    usage_records: list[dict[str, Any]] = []
    if provider is not None:
        embeddings = provider.embed_texts([chunk["text"] for chunk in prepared_corpus])
        for chunk, embedding in zip(prepared_corpus, embeddings, strict=True):
            chunk["embedding"] = embedding
            chunk["embedding_provider"] = provider.provider_name
            chunk["embedding_model"] = provider.model
            chunk["embedding_dimension"] = provider.dimension
        usage_records.append(dict(provider.last_call) | {"phase": "corpus_ingestion"})

    results = []
    for case in cases:
        candidates = _candidate_chunks(case, prepared_corpus)
        query_embedding = None
        started = perf_counter()
        if provider is not None:
            query_embedding = provider.embed_texts([case["question"]])[0]
            usage_records.append(dict(provider.last_call) | {"phase": "query", "case_id": case["id"]})
        evidence = filter_usable_evidence(
            retrieve_relevant_chunks(
                case["question"],
                candidates,
                limit=5,
                query_embedding=query_embedding,
                retrieval_method=method,
            ),
            min_score=min_score,
        )
        latency_ms = round((perf_counter() - started) * 1000, 3)
        ranking = score_retrieval_ranking(case, evidence)
        answer = build_evidence_answer(case["question"], evidence)
        answer_metrics = score_eval_case(case, answer)
        results.append(
            {
                "id": case["id"],
                "case_category": case.get("case_category", "qa"),
                "latency_ms": latency_ms,
                "ranking": ranking,
                "answer_correct": _answer_is_correct(answer_metrics),
                "answer": answer["answer"],
                "top_evidence": [
                    {
                        "document_title": item.get("document_title"),
                        "page_number": item.get("page_number"),
                        "score": item.get("score"),
                    }
                    for item in evidence[:5]
                ],
            }
        )
    return _mode_summary(
        results,
        usage_records,
        provider_name=getattr(provider, "provider_name", "none"),
        model=getattr(provider, "model", None),
        dimension=getattr(provider, "dimension", None),
        includes_corpus_ingestion=provider is not None,
    )


def _run_pgvector_mode(cases: list[dict[str, Any]], settings: Settings) -> dict[str, Any]:
    if not settings.database_url.startswith(("postgresql://", "postgresql+")):
        return {
            "status": "skipped",
            "reason": "DATABASE_URL is not PostgreSQL; pgvector comparison requires PostgreSQL.",
        }
    real_status = _real_provider_status(settings)
    if real_status["status"] != "configured":
        return {
            "status": "skipped",
            "reason": "pgvector real mode requires a configured OpenAI-compatible embedding provider.",
        }

    try:
        from fastapi.testclient import TestClient

        from app.main import create_app

        app = create_app(settings)
        client = TestClient(app)
        if app.state.engine.dialect.name != "postgresql":
            return {"status": "skipped", "reason": "SQLAlchemy is not using PostgreSQL."}
        usage_records = []
        document_ids = ensure_eval_documents(client, cases, usage_records)
        results = []
        with app.state.session_factory() as session:
            for case in cases:
                started = perf_counter()
                raw_evidence = retrieve_document_evidence(
                    session,
                    settings,
                    case["question"],
                    _case_document_ids(case, document_ids),
                    5,
                )
                observed_methods = {
                    item.get("retrieval_method") for item in raw_evidence if item.get("retrieval_method")
                }
                if raw_evidence and observed_methods != {"pgvector"}:
                    return {
                        "status": "failed",
                        "reason": (
                            f"Case {case['id']} used {sorted(observed_methods)} instead of pgvector; "
                            "the provider or vector query may have fallen back."
                        ),
                    }
                evidence = filter_usable_evidence(
                    raw_evidence,
                    min_score=settings.min_retrieval_score,
                )
                latency_ms = round((perf_counter() - started) * 1000, 3)
                answer = build_evidence_answer(case["question"], evidence)
                answer_metrics = score_eval_case(case, answer)
                if evidence and isinstance(evidence[0].get("embedding_usage"), dict):
                    usage_records.append(
                        dict(evidence[0]["embedding_usage"])
                        | {"phase": "query", "case_id": case["id"]}
                    )
                results.append(
                    {
                        "id": case["id"],
                        "case_category": case.get("case_category", "qa"),
                        "latency_ms": latency_ms,
                        "ranking": score_retrieval_ranking(case, evidence),
                        "answer_correct": _answer_is_correct(answer_metrics),
                        "answer": answer["answer"],
                        "top_evidence": [
                            {
                                "document_title": item.get("document_title"),
                                "page_number": item.get("page_number"),
                                "score": item.get("score"),
                            }
                            for item in evidence[:5]
                        ],
                    }
                )
        return _mode_summary(
            results,
            usage_records,
            provider_name=settings.embedding_provider,
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
            includes_corpus_ingestion=True,
        )
    except Exception as exc:
        return {"status": "failed", "reason": f"PostgreSQL/pgvector mode failed: {exc}"}


def _mode_summary(
    results: list[dict[str, Any]],
    usage: list[dict[str, Any]],
    *,
    provider_name: str,
    model: str | None,
    dimension: int | None,
    includes_corpus_ingestion: bool,
) -> dict[str, Any]:
    rankings = [result["ranking"] for result in results if result["ranking"].get("applicable")]
    summary = {
        "status": "passed",
        "evaluated_cases": len(rankings),
        "recall_at_1": _mean(rankings, "recall_at_1"),
        "recall_at_3": _mean(rankings, "recall_at_3"),
        "recall_at_5": _mean(rankings, "recall_at_5"),
        "mrr": _mean(rankings, "reciprocal_rank"),
        "ndcg_at_5": _mean(rankings, "ndcg_at_5"),
        "evidence_page_hit": _mean_boolean(
            result["ranking"].get("recall_at_5") == 1.0 for result in results
        ),
        "answer_correctness": _mean_boolean(result["answer_correct"] for result in results),
        "average_query_latency_ms": round(
            sum(float(result["latency_ms"]) for result in results) / len(results),
            3,
        )
        if results
        else 0.0,
        "failed_case_ids": [
            result["id"] for result in results if float(result["ranking"].get("recall_at_5") or 0.0) < 1.0
        ],
        "failed_answer_case_ids": [
            result["id"] for result in results if not result["answer_correct"]
        ],
        "provider": {
            "name": provider_name,
            "model": model,
            "dimension": dimension,
        },
        "usage": {
            "input_tokens": sum(int(item.get("input_tokens", 0)) for item in usage),
            "total_tokens": sum(int(item.get("total_tokens", 0)) for item in usage),
            "latency_ms": round(sum(float(item.get("latency_ms", 0.0)) for item in usage), 3),
            "estimated_cost_usd": round(
                sum(float(item.get("estimated_cost_usd", 0.0)) for item in usage),
                8,
            ),
            "includes_corpus_ingestion": includes_corpus_ingestion,
        },
        "results": results,
    }
    return summary


def _load_corpus(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    titles = sorted({title for case in cases for title in _case_titles(case)})
    corpus = []
    chunk_id = 1
    for document_id, title in enumerate(titles, start=1):
        pages = _load_document_pages(title)
        for chunk in chunk_pages(document_id, pages):
            corpus.append(
                {
                    **chunk,
                    "id": chunk_id,
                    "document_title": title,
                }
            )
            chunk_id += 1
    return corpus


def _candidate_chunks(case: dict[str, Any], corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    titles = set(_case_titles(case))
    return [chunk for chunk in corpus if chunk["document_title"] in titles]


def _case_titles(case: dict[str, Any]) -> list[str]:
    titles = []
    if case.get("document_title"):
        titles.append(case["document_title"])
    titles.extend(case.get("document_titles", []))
    return titles


def _is_retrieval_case(case: dict[str, Any]) -> bool:
    return case.get("eval_type") == "qa" and bool(
        case.get("expected_evidence") or case.get("expected_evidence_page") is not None
    )


def _real_provider_status(settings: Settings) -> dict[str, Any]:
    if settings.embedding_provider.lower() not in REAL_PROVIDER_ALIASES:
        return {
            "status": "skipped",
            "reason": "EMBEDDING_PROVIDER is local; set it to openai_compatible for real mode.",
        }
    if not (settings.embedding_api_key or settings.openai_api_key):
        return {
            "status": "skipped",
            "reason": "EMBEDDING_API_KEY or OPENAI_API_KEY is not configured.",
        }
    return {"status": "configured"}


def _mean(items: list[dict[str, Any]], key: str) -> float:
    values = [float(item[key]) for item in items if item.get(key) is not None]
    return round(sum(values) / len(values), 4) if values else 0.0


def _mean_boolean(values) -> float:
    values = list(values)
    return round(sum(1 for value in values if value) / len(values), 4) if values else 0.0


def _answer_is_correct(metrics: dict[str, bool | None]) -> bool:
    return bool(
        metrics.get("answer_keyword_hit") is True
        and metrics.get("retrieval_hit") is True
        and metrics.get("forbidden_answer_hit") is not False
    )


def render_benchmark_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Retrieval Benchmark",
        "",
        f"Generated: {report['generated_at']}",
        f"Dataset: `{report['dataset']}`",
        f"Cases: {report['case_count']}",
        "",
        "| Mode | Status | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | Page hit | Answer correct | Avg query latency | Est. cost |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, mode in report["modes"].items():
        if mode.get("status") != "passed":
            lines.append(
                f"| {name} | {mode.get('status')}: {mode.get('reason')} | - | - | - | - | - | - | - | - | - |"
            )
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    name,
                    "passed",
                    f"{mode['recall_at_1']:.4f}",
                    f"{mode['recall_at_3']:.4f}",
                    f"{mode['recall_at_5']:.4f}",
                    f"{mode['mrr']:.4f}",
                    f"{mode['ndcg_at_5']:.4f}",
                    f"{mode['evidence_page_hit']:.4f}",
                    f"{mode['answer_correctness']:.4f}",
                    f"{mode['average_query_latency_ms']:.3f} ms",
                    f"${mode['usage']['estimated_cost_usd']:.8f}",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Failed Retrieval Cases", ""])
    for name, mode in report["modes"].items():
        if mode.get("status") == "passed":
            failed = mode.get("failed_case_ids", [])
            lines.append(f"- `{name}`: {', '.join(failed) if failed else 'none'}")
    real_rows_executed = all(
        report["modes"].get(name, {}).get("status") == "passed"
        for name in ("configured_real_embedding", "postgres_pgvector")
    )
    real_mode_summary = (
        "- Real-provider and pgvector rows executed; compare their measured quality, latency, and cost."
        if real_rows_executed
        else "- Real-provider or pgvector rows are explicitly skipped or failed when prerequisites are unavailable."
    )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Keyword and local deterministic modes are reproducible baselines, not semantic-quality claims.",
            real_mode_summary,
            "- A reranker should only be added when the measured real-provider baseline leaves meaningful retrieval failures.",
            "",
        ]
    )
    return "\n".join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare BidGuard AI retrieval baselines.")
    parser.add_argument("--dataset", type=Path, default=RETRIEVAL_BENCHMARK_CASES)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-markdown", type=Path, default=None)
    parser.add_argument(
        "--require-real",
        action="store_true",
        help="Exit with code 2 when a real embedding provider is not configured.",
    )
    parser.add_argument(
        "--require-pgvector",
        action="store_true",
        help="Exit with code 2 unless PostgreSQL pgvector real-provider mode passes.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
