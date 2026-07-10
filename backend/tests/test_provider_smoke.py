from pathlib import Path

import pytest

from app.config import Settings
from app.evaluation.provider_smoke import (
    SmokeFailure,
    run_smoke,
    validate_embedding_provider,
)
from app.services.embeddings import OpenAICompatibleEmbeddingProvider
from app.services.llm import OpenAICompatibleLLMProvider

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_env_example_can_be_loaded_without_manual_cleanup():
    settings = Settings(_env_file=BACKEND_ROOT / ".env.example")

    assert settings.embedding_provider == "local"
    assert settings.llm_provider == "local_fake"


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
    assert report["embedding_provider_validation"]["usage"]["provider"] == "local"
    assert report["embedding_provider_validation"]["usage"]["latency_ms"] >= 0
    assert report["embedding_provider_validation"]["usage"]["estimated_cost_usd"] == 0
    assert report["llm_provider_validation"]["status"] == "passed"
    assert report["llm_provider_validation"]["llm_synthesis_used"] is True
    assert report["llm_provider_validation"]["usage"]["provider"] == "local_fake"
    assert report["llm_provider_validation"]["usage"]["total_tokens"] > 0


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


def test_local_provider_metrics_do_not_claim_configured_hosted_model_names():
    report = run_smoke(
        Settings(
            _env_file=None,
            embedding_provider="local",
            embedding_model="text-embedding-3-small",
            embedding_dimension=16,
            llm_provider="local_fake",
            llm_model="gpt-4.1-mini",
        )
    )

    assert report["embedding_provider_validation"]["model"] == "local-hash-v1"
    assert report["embedding_provider_validation"]["usage"]["model"] == "local-hash-v1"
    assert report["llm_provider_validation"]["model"] == "local-fake-v1"
    assert report["llm_provider_validation"]["usage"]["model"] == "local-fake-v1"


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


def test_real_provider_metrics_capture_tokens_latency_and_estimated_cost(monkeypatch):
    embedding_request = {}

    class FakeEmbeddingResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [{"index": 0, "embedding": [0.1, 0.2]}],
                "usage": {"prompt_tokens": 1000, "total_tokens": 1000},
            }

    class FakeLLMResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "The deadline is 20 August 2026 [1]."}}],
                "usage": {"prompt_tokens": 2000, "completion_tokens": 500, "total_tokens": 2500},
            }

    def fake_embedding_post(*args, **kwargs):
        embedding_request.update(kwargs["json"])
        return FakeEmbeddingResponse()

    monkeypatch.setattr("app.services.embeddings.httpx.post", fake_embedding_post)
    embedding_provider = OpenAICompatibleEmbeddingProvider(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="embedding-test",
        dimension=2,
        input_cost_per_million_tokens=0.1,
    )
    embedding_provider.embed_texts(["test"])

    assert embedding_request["dimensions"] == 2
    assert embedding_provider.last_call["input_tokens"] == 1000
    assert embedding_provider.last_call["estimated_cost_usd"] == 0.0001
    assert embedding_provider.last_call["input_cost_per_million_tokens"] == 0.1
    assert embedding_provider.last_call["latency_ms"] >= 0

    monkeypatch.setattr("app.services.llm.httpx.post", lambda *args, **kwargs: FakeLLMResponse())
    llm_provider = OpenAICompatibleLLMProvider(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="llm-test",
        input_cost_per_million_tokens=1.0,
        output_cost_per_million_tokens=2.0,
    )
    llm_provider.synthesize(
        "What is the deadline?",
        [{"document_title": "Tender", "page_number": 1, "text": "Deadline: 20 August 2026."}],
    )

    assert llm_provider.last_call["input_tokens"] == 2000
    assert llm_provider.last_call["output_tokens"] == 500
    assert llm_provider.last_call["estimated_cost_usd"] == 0.003
    assert llm_provider.last_call["input_cost_per_million_tokens"] == 1.0
    assert llm_provider.last_call["output_cost_per_million_tokens"] == 2.0
    assert llm_provider.last_call["latency_ms"] >= 0


def test_llm_cost_metrics_distinguish_cached_and_uncached_input_tokens(monkeypatch):
    class FakeLLMResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "The deadline is 20 August 2026 [1]."}}],
                "usage": {
                    "prompt_tokens": 2000,
                    "prompt_cache_hit_tokens": 800,
                    "prompt_cache_miss_tokens": 1200,
                    "completion_tokens": 500,
                    "total_tokens": 2500,
                },
            }

    monkeypatch.setattr("app.services.llm.httpx.post", lambda *args, **kwargs: FakeLLMResponse())
    provider = OpenAICompatibleLLMProvider(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="llm-test",
        input_cost_per_million_tokens=1.0,
        cached_input_cost_per_million_tokens=0.1,
        output_cost_per_million_tokens=2.0,
    )

    provider.synthesize(
        "What is the deadline?",
        [{"document_title": "Tender", "page_number": 1, "text": "Deadline: 20 August 2026."}],
    )

    assert provider.last_call["cache_hit_input_tokens"] == 800
    assert provider.last_call["cache_miss_input_tokens"] == 1200
    assert provider.last_call["cached_input_cost_per_million_tokens"] == 0.1
    assert provider.last_call["estimated_cost_usd"] == 0.00228
