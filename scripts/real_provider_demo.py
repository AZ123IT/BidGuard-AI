#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
BACKEND_PYTHON = BACKEND / ".venv" / "bin" / "python"
REPORT_PATH = ROOT / "data" / "eval_reports" / "latest_real_provider_eval.json"


def main() -> int:
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
        ],
        cwd=BACKEND,
    )
    if eval_result.returncode != 0:
        print(json.dumps({"status": "FAIL", "step": "real_provider_eval", "output": eval_result.output}, indent=2))
        return eval_result.returncode

    eval_report = json.loads(eval_result.output)
    print(
        json.dumps(
            {
                "status": "PASS",
                "provider_smoke": smoke_report,
                "eval_summary": {
                    "passed": eval_report["passed"],
                    "failed": eval_report["failed"],
                    "total": eval_report["total"],
                    "pass_rate": eval_report["pass_rate"],
                    "provider_mode": eval_report["provider_mode"],
                    "database_mode": eval_report["database_mode"],
                    "retrieval_methods": eval_report["retrieval_methods"],
                },
                "eval_report_path": str(REPORT_PATH),
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


class CommandResult:
    def __init__(self, returncode: int, output: str) -> None:
        self.returncode = returncode
        self.output = output


def run_json_command(command: list[str], cwd: Path) -> CommandResult:
    completed = subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)
    output = completed.stdout.strip() or completed.stderr.strip()
    return CommandResult(completed.returncode, output)


if __name__ == "__main__":
    sys.exit(main())
