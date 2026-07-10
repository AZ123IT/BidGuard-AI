import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REAL_DEMO_SCRIPT = ROOT / "scripts" / "real_provider_demo.py"


def load_real_demo_module():
    spec = importlib.util.spec_from_file_location("real_provider_demo", REAL_DEMO_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_demo_report_validation_rejects_fallback_execution():
    module = load_real_demo_module()
    fallback_report = {
        "provider_mode": {
            "embedding_provider": "openai_compatible",
            "llm_provider": "openai_compatible",
        },
        "database_mode": "sqlite",
        "retrieval_methods": ["hybrid_fallback"],
        "provider_usage": {"total_tokens": 0},
        "results": [
            {
                "eval_type": "qa",
                "observability": {
                    "evidence_count": 1,
                    "llm_synthesis_used": False,
                },
            }
        ],
    }

    errors = module.validate_real_eval_report(fallback_report)

    assert any("postgres_pgvector" in error for error in errors)
    assert any("pgvector retrieval" in error for error in errors)
    assert any("real LLM" in error for error in errors)
    assert any("token usage" in error for error in errors)


def test_real_demo_report_validation_accepts_real_pgvector_execution():
    module = load_real_demo_module()
    real_report = {
        "provider_mode": {
            "embedding_provider": "openai_compatible",
            "llm_provider": "openai_compatible",
        },
        "database_mode": "postgres_pgvector",
        "retrieval_methods": ["pgvector", "risk_rule_check_tool"],
        "provider_usage": {"total_tokens": 100},
        "results": [
            {
                "eval_type": "qa",
                "observability": {
                    "evidence_count": 1,
                    "llm_synthesis_used": True,
                },
            },
            {
                "eval_type": "insufficient",
                "observability": {
                    "evidence_count": 0,
                    "llm_synthesis_used": False,
                },
            },
        ],
    }

    assert module.validate_real_eval_report(real_report) == []


def test_real_demo_accepts_completed_eval_report_with_failed_cases():
    module = load_real_demo_module()
    result = module.CommandResult(
        1,
        json.dumps({"passed": 31, "failed": 5, "total": 36}),
    )

    report = module.parse_completed_eval_report(result)

    assert report["failed"] == 5


def test_real_demo_help_does_not_run_provider_commands(monkeypatch, capsys):
    module = load_real_demo_module()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("--help must not run provider or database commands")

    monkeypatch.setattr(module, "run_json_command", fail_if_called)

    with pytest.raises(SystemExit) as exc_info:
        module.main(["--help"])

    assert exc_info.value.code == 0
    assert "real provider" in capsys.readouterr().out.lower()


def test_real_demo_preflights_pgvector_before_provider_calls(monkeypatch, capsys):
    module = load_real_demo_module()
    commands = []

    def fake_run(command, cwd):
        commands.append((command, cwd))
        return module.CommandResult(
            1,
            json.dumps(
                {
                    "status": "FAIL",
                    "error": "DATABASE_URL must point to PostgreSQL",
                }
            ),
        )

    monkeypatch.setattr(module, "run_json_command", fake_run)

    assert module.main([]) == 1
    assert len(commands) == 1
    assert commands[0][0][-1] == "--preflight-only"
    assert "database_preflight" in capsys.readouterr().out
