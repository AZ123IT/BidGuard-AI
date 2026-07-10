#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
BACKEND_PYTHON = BACKEND / ".venv" / "bin" / "python"
REPORT_PATH = ROOT / "data" / "eval_reports" / "latest_real_provider_eval.json"
FAILURE_REPORT_PATH = ROOT / "data" / "eval_reports" / "latest_real_provider_failure_analysis.md"
BENCHMARK_PATH = ROOT / "data" / "eval_reports" / "latest_real_retrieval_benchmark.json"
BENCHMARK_MARKDOWN_PATH = ROOT / "data" / "eval_reports" / "latest_real_retrieval_benchmark.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the BidGuard AI real provider eval and retrieval benchmark. "
            "Requires PostgreSQL + pgvector before provider calls begin."
        )
    )
    parser.parse_args(argv)

    database_preflight = run_json_command(
        [str(BACKEND_PYTHON), "scripts/smoke_pgvector.py", "--preflight-only"],
        cwd=BACKEND,
    )
    if database_preflight.returncode != 0:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "step": "database_preflight",
                    "reason": (
                        "The real provider demo requires PostgreSQL + pgvector. "
                        "No provider API calls were made."
                    ),
                    "output": database_preflight.output,
                },
                indent=2,
            )
        )
        return database_preflight.returncode
    try:
        database_preflight_report = json.loads(database_preflight.output)
    except json.JSONDecodeError:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "step": "database_preflight",
                    "reason": "Database preflight did not return valid JSON.",
                },
                indent=2,
            )
        )
        return 2

    smoke = run_json_command([str(BACKEND_PYTHON), "scripts/smoke_providers.py"], cwd=BACKEND)
    if smoke.returncode != 0:
        print(json.dumps({"status": "FAIL", "step": "provider_smoke", "output": smoke.output}, indent=2))
        return smoke.returncode

    smoke_report = json.loads(smoke.output)
    embedding = smoke_report["embedding_provider_validation"]
    llm = smoke_report["llm_provider_validation"]
    if not _real_provider_passed(embedding, llm):
        print(
            json.dumps(
                {
                    "status": "SKIPPED",
                    "reason": "Real OpenAI-compatible embedding and LLM providers are not both configured and passing.",
                    "provider_smoke": smoke_report,
                    "how_to_run": [
                        "Set EMBEDDING_PROVIDER=openai_compatible with embedding key/base URL/model/dimension.",
                        "Set LLM_PROVIDER=openai_compatible with LLM key/base URL/model.",
                        "Run: python3 scripts/real_provider_demo.py",
                    ],
                },
                indent=2,
            )
        )
        return 0

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    eval_result = run_json_command(
        [
            str(BACKEND_PYTHON),
            "-m",
            "app.evaluation.run_eval",
            "--dataset",
            "../data/eval_cases/rag_demo.json",
            "--output-json",
            "../data/eval_reports/latest_real_provider_eval.json",
            "--failure-report",
            "../data/eval_reports/latest_real_provider_failure_analysis.md",
        ],
        cwd=BACKEND,
    )
    try:
        eval_report = parse_completed_eval_report(eval_result)
    except ValueError as exc:
        print(
            json.dumps(
                {"status": "FAIL", "step": "real_provider_eval", "error": str(exc)},
                indent=2,
            )
        )
        return eval_result.returncode or 2
    eval_validation_errors = validate_real_eval_report(eval_report)
    if eval_validation_errors:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "step": "real_provider_eval_validation",
                    "errors": eval_validation_errors,
                    "eval_report_path": str(REPORT_PATH),
                },
                indent=2,
            )
        )
        return 2

    benchmark_result = run_json_command(
        [
            str(BACKEND_PYTHON),
            "scripts/run_retrieval_benchmark.py",
            "--output-json",
            "../data/eval_reports/latest_real_retrieval_benchmark.json",
            "--output-markdown",
            "../data/eval_reports/latest_real_retrieval_benchmark.md",
            "--require-real",
            "--require-pgvector",
        ],
        cwd=BACKEND,
    )
    if benchmark_result.returncode != 0:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "step": "real_pgvector_retrieval_benchmark",
                    "reason": (
                        "The full experiment requires both real embeddings and "
                        "PostgreSQL pgvector mode."
                    ),
                    "output": benchmark_result.output,
                },
                indent=2,
            )
        )
        return benchmark_result.returncode

    benchmark_report = json.loads(benchmark_result.output)
    pgvector_summary = benchmark_report["modes"]["postgres_pgvector"]
    print(
        json.dumps(
            {
                "status": (
                    "PASS" if eval_report["failed"] == 0 else "COMPLETED_WITH_EVAL_FAILURES"
                ),
                "database_preflight": database_preflight_report,
                "provider_smoke": smoke_report,
                "eval_summary": {
                    "passed": eval_report["passed"],
                    "failed": eval_report["failed"],
                    "total": eval_report["total"],
                    "pass_rate": eval_report["pass_rate"],
                    "provider_mode": eval_report["provider_mode"],
                    "database_mode": eval_report["database_mode"],
                    "retrieval_methods": eval_report["retrieval_methods"],
                    "provider_usage": eval_report["provider_usage"],
                },
                "pgvector_benchmark_summary": {
                    key: pgvector_summary[key]
                    for key in [
                        "recall_at_1",
                        "recall_at_3",
                        "recall_at_5",
                        "mrr",
                        "ndcg_at_5",
                        "evidence_page_hit",
                        "answer_correctness",
                        "average_query_latency_ms",
                        "provider",
                        "usage",
                    ]
                },
                "eval_report_path": str(REPORT_PATH),
                "failure_report_path": str(FAILURE_REPORT_PATH),
                "benchmark_report_path": str(BENCHMARK_PATH),
                "benchmark_markdown_path": str(BENCHMARK_MARKDOWN_PATH),
            },
            indent=2,
        )
    )
    return 0


def _real_provider_passed(embedding: dict, llm: dict) -> bool:
    return (
        embedding.get("status") == "passed"
        and embedding.get("mode") == "openai_compatible"
        and llm.get("status") == "passed"
        and llm.get("mode") == "openai_compatible"
    )


def validate_real_eval_report(report: dict) -> list[str]:
    errors = []
    provider_mode = report.get("provider_mode", {})
    if provider_mode.get("embedding_provider") != "openai_compatible":
        errors.append("Eval did not use the openai_compatible embedding provider.")
    if provider_mode.get("llm_provider") != "openai_compatible":
        errors.append("Eval did not use the openai_compatible LLM provider.")
    if report.get("database_mode") != "postgres_pgvector":
        errors.append("Eval database_mode must be postgres_pgvector.")
    if "pgvector" not in report.get("retrieval_methods", []):
        errors.append("Eval did not observe pgvector retrieval; a fallback path may have run.")

    qa_with_evidence = [
        result
        for result in report.get("results", [])
        if result.get("eval_type") == "qa"
        and result.get("observability", {}).get("evidence_count", 0) > 0
    ]
    if any(
        not result.get("observability", {}).get("llm_synthesis_used")
        for result in qa_with_evidence
    ):
        errors.append("At least one answerable QA case fell back instead of using the real LLM.")
    if int(report.get("provider_usage", {}).get("total_tokens", 0)) <= 0:
        errors.append("Real provider token usage was not recorded.")
    return errors


class CommandResult:
    def __init__(self, returncode: int, output: str) -> None:
        self.returncode = returncode
        self.output = output


def parse_completed_eval_report(result: CommandResult) -> dict:
    if result.returncode not in {0, 1}:
        raise ValueError(
            f"Eval command failed with exit code {result.returncode}: {result.output[:1000]}"
        )
    try:
        report = json.loads(result.output)
    except json.JSONDecodeError as exc:
        raise ValueError("Eval command did not return a valid JSON report.") from exc
    if not isinstance(report, dict) or not {"passed", "failed", "total"}.issubset(report):
        raise ValueError("Eval command returned an incomplete JSON report.")
    return report


def run_json_command(command: list[str], cwd: Path) -> CommandResult:
    completed = subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)
    output = completed.stdout.strip() or completed.stderr.strip()
    return CommandResult(completed.returncode, output)


if __name__ == "__main__":
    sys.exit(main())
