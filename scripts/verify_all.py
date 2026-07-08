#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


@dataclass(frozen=True)
class Step:
    label: str
    command: list[str]
    cwd: Path
    env: dict[str, str] = field(default_factory=dict)


def build_plan(with_pgvector: bool = False) -> list[Step]:
    backend_python = str(BACKEND / ".venv" / "bin" / "python")
    backend_ruff = str(BACKEND / ".venv" / "bin" / "ruff")
    plan = [
        Step("backend tests", [backend_python, "-m", "pytest", "tests", "-q"], BACKEND),
        Step("backend Ruff", [backend_ruff, "check", "."], BACKEND),
        Step("provider smoke", [backend_python, "scripts/smoke_providers.py"], BACKEND),
        Step("smoke eval", [backend_python, "-m", "app.evaluation.run_eval"], BACKEND),
        Step(
            "demo eval",
            [backend_python, "-m", "app.evaluation.run_eval", "--dataset", "../data/eval_cases/rag_demo.json"],
            BACKEND,
        ),
        Step("frontend typecheck", ["npm", "run", "typecheck"], FRONTEND),
        Step("frontend build", ["npm", "run", "build"], FRONTEND),
    ]
    if with_pgvector:
        pgvector_env = {
            "DATABASE_URL": "postgresql+psycopg://bidguard:bidguard@localhost:5432/bidguard",
            "EMBEDDING_PROVIDER": "local",
            "EMBEDDING_DIMENSION": "64",
            "LLM_PROVIDER": "local_fake",
        }
        plan.extend(
            [
                Step("pgvector postgres start", ["docker", "compose", "up", "-d", "postgres"], ROOT),
                Step(
                    "pgvector smoke",
                    [backend_python, "scripts/smoke_pgvector.py"],
                    BACKEND,
                    env=pgvector_env,
                ),
                Step("pgvector postgres stop", ["docker", "compose", "stop", "postgres"], ROOT),
            ]
        )
    return plan


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results = []
    for step in build_plan(with_pgvector=args.with_pgvector):
        result = run_step(step)
        results.append(result)
        if result != 0:
            print_summary(results)
            return result
    print_summary(results)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BidGuard AI verification checks.")
    parser.add_argument(
        "--with-pgvector",
        action="store_true",
        help="Also start PostgreSQL and run the pgvector smoke check.",
    )
    return parser.parse_args(argv)


def run_step(step: Step) -> int:
    print(f"\n==> {step.label}")
    print(f"$ {' '.join(step.command)}")
    env = os.environ.copy()
    env.update(step.env)
    completed = subprocess.run(step.command, cwd=step.cwd, env=env, check=False)
    status = "PASS" if completed.returncode == 0 else "FAIL"
    print(f"<== {step.label}: {status}")
    return completed.returncode


def print_summary(results: list[int]) -> None:
    passed = sum(1 for result in results if result == 0)
    total = len(results)
    failed = total - passed
    print(f"\nVerification summary: {passed}/{total} passed, {failed} failed.")


if __name__ == "__main__":
    sys.exit(main())
