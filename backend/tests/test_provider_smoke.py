import pytest

from app.config import Settings
from app.evaluation.provider_smoke import (
    SmokeFailure,
    run_smoke,
    validate_embedding_provider,
)


def test_provider_smoke_validates_local_embedding_and_local_fake_llm():
    settings = Settings(
        _env_file=None,
        embedding_provider="local",
        embedding_model="local-hash-v1",
        embedding_dimension=16,
        llm_provider="local_fake",
        llm_model="local-fake-v1",
    )

    report = run_smoke(settings)

    assert report["status"] == "PASS"
    assert report["embedding_provider_validation"]["status"] == "passed"
    assert report["embedding_provider_validation"]["dimension"] == 16
    assert report["llm_provider_validation"]["status"] == "passed"
    assert report["llm_provider_validation"]["llm_synthesis_used"] is True


def test_provider_smoke_skips_real_providers_when_keys_are_missing(monkeypatch):
    for name in ("EMBEDDING_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(
        _env_file=None,
        embedding_provider="openai_compatible",
        embedding_api_key=None,
        llm_provider="openai_compatible",
        llm_api_key=None,
        openai_api_key=None,
    )

    report = run_smoke(settings)

    assert report["status"] == "PASS"
    assert report["embedding_provider_validation"]["status"] == "skipped"
    assert "EMBEDDING_API_KEY" in report["embedding_provider_validation"]["reason"]
    assert report["llm_provider_validation"]["status"] == "skipped"
    assert "LLM_API_KEY" in report["llm_provider_validation"]["reason"]


def test_provider_smoke_fails_clearly_on_embedding_dimension_mismatch(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"index": 0, "embedding": [0.1, 0.2]}]}

    monkeypatch.setattr("app.services.embeddings.httpx.post", lambda *args, **kwargs: FakeResponse())
    settings = Settings(
        _env_file=None,
        embedding_provider="openai_compatible",
        embedding_api_key="test-key",
        embedding_model="test-embedding-model",
        embedding_dimension=8,
        llm_provider="local_fake",
    )

    with pytest.raises(SmokeFailure, match="Embedding dimension mismatch"):
        validate_embedding_provider(settings)
