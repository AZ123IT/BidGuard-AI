import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFY_SCRIPT = ROOT / "scripts" / "verify_all.py"


def load_verify_all_module():
    spec = importlib.util.spec_from_file_location("verify_all", VERIFY_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verify_all_default_plan_lists_required_checks():
    module = load_verify_all_module()

    plan = module.build_plan(with_pgvector=False)

    assert [step.label for step in plan] == [
        "backend tests",
        "backend Ruff",
        "provider smoke",
        "smoke eval",
        "demo eval",
        "frontend typecheck",
        "frontend build",
    ]
    assert all("docker" not in step.command[0] for step in plan)


def test_verify_all_pgvector_plan_stops_container_after_smoke():
    module = load_verify_all_module()

    plan = module.build_plan(with_pgvector=True)

    labels = [step.label for step in plan]
    assert "pgvector postgres start" in labels
    assert "pgvector smoke" in labels
    assert labels[-1] == "pgvector postgres stop"
    pgvector = next(step for step in plan if step.label == "pgvector smoke")
    assert pgvector.env["DATABASE_URL"].startswith("postgresql+psycopg://")
    assert pgvector.env["EMBEDDING_PROVIDER"] == "local"
