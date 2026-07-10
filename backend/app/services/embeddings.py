import hashlib
import math
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

import httpx

from app.config import Settings
from app.services.retrieval import tokenize


class EmbeddingError(RuntimeError):
    pass


class EmbeddingProvider(Protocol):
    provider_name: str
    model: str
    dimension: int
    last_call: dict[str, Any]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        pass


@dataclass
class LocalEmbeddingProvider:
    dimension: int
    model: str = "local-hash-v1"
    provider_name: str = "local"
    last_call: dict[str, Any] = field(default_factory=dict, init=False)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        started = perf_counter()
        embeddings = [_normalize(_hash_tokens(text, self.dimension)) for text in texts]
        input_tokens = sum(len(tokenize(text)) for text in texts)
        self.last_call = _embedding_call_metrics(
            provider=self.provider_name,
            model=self.model,
            input_tokens=input_tokens,
            latency_ms=(perf_counter() - started) * 1000,
            estimated_cost_usd=0.0,
            input_cost_per_million_tokens=0.0,
        )
        return embeddings


@dataclass
class OpenAICompatibleEmbeddingProvider:
    api_key: str
    base_url: str
    model: str
    dimension: int
    provider_name: str = "openai_compatible"
    timeout_seconds: float = 30.0
    input_cost_per_million_tokens: float = 0.0
    last_call: dict[str, Any] = field(default_factory=dict, init=False)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        started = perf_counter()
        try:
            response = httpx.post(
                f"{self.base_url.rstrip('/')}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "input": texts,
                    "encoding_format": "float",
                    "dimensions": self.dimension,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise EmbeddingError(
                f"Embedding provider returned HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise EmbeddingError(
                f"Embedding provider request timed out after {self.timeout_seconds} seconds."
            ) from exc
        except httpx.RequestError as exc:
            raise EmbeddingError(f"Embedding provider request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise EmbeddingError("Embedding provider returned non-JSON response.") from exc
        try:
            embeddings = [item["embedding"] for item in sorted(payload["data"], key=lambda item: item["index"])]
        except (KeyError, TypeError) as exc:
            raise EmbeddingError("Embedding provider returned an unexpected response shape.") from exc
        if len(embeddings) != len(texts):
            raise EmbeddingError("Embedding provider returned a different number of embeddings than requested.")
        for embedding in embeddings:
            if len(embedding) != self.dimension:
                raise EmbeddingError(
                    f"Embedding dimension mismatch: expected {self.dimension}, got {len(embedding)}."
                )
        usage = payload.get("usage") if isinstance(payload, dict) else {}
        usage = usage if isinstance(usage, dict) else {}
        input_tokens = _usage_int(usage, "prompt_tokens", "input_tokens")
        total_tokens = _usage_int(usage, "total_tokens") or input_tokens
        self.last_call = _embedding_call_metrics(
            provider=self.provider_name,
            model=str(payload.get("model") or self.model),
            input_tokens=input_tokens,
            total_tokens=total_tokens,
            latency_ms=(perf_counter() - started) * 1000,
            estimated_cost_usd=(input_tokens / 1_000_000) * self.input_cost_per_million_tokens,
            input_cost_per_million_tokens=self.input_cost_per_million_tokens,
        )
        return embeddings


def make_embedding_provider(settings: Settings) -> EmbeddingProvider:
    provider = settings.embedding_provider.lower()
    if provider in {"local", "fake", "deterministic"}:
        return LocalEmbeddingProvider(dimension=settings.embedding_dimension)
    if provider in {"openai", "openai_compatible", "qwen", "bge"}:
        api_key = settings.embedding_api_key or settings.openai_api_key
        base_url = settings.embedding_base_url or settings.openai_base_url
        if not api_key:
            raise EmbeddingError(
                "EMBEDDING_API_KEY or OPENAI_API_KEY is required when "
                f"EMBEDDING_PROVIDER={settings.embedding_provider}. Use EMBEDDING_PROVIDER=local "
                "for zero-config deterministic embeddings."
            )
        if not base_url:
            raise EmbeddingError(
                "EMBEDDING_BASE_URL or OPENAI_BASE_URL is required when "
                f"EMBEDDING_PROVIDER={settings.embedding_provider}."
            )
        if not settings.embedding_model:
            raise EmbeddingError(
                "EMBEDDING_MODEL is required when "
                f"EMBEDDING_PROVIDER={settings.embedding_provider}."
            )
        return OpenAICompatibleEmbeddingProvider(
            api_key=api_key,
            base_url=base_url,
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
            timeout_seconds=settings.embedding_timeout_seconds,
            input_cost_per_million_tokens=settings.embedding_input_cost_per_million_tokens,
        )
    raise EmbeddingError(f"Unsupported EMBEDDING_PROVIDER: {settings.embedding_provider}")


def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    similarity = sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)
    return round(max(-1.0, min(1.0, similarity)), 6)


def _hash_tokens(text: str, dimension: int) -> list[float]:
    vector = [0.0] * dimension
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    return vector


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]


def _embedding_call_metrics(
    provider: str,
    model: str,
    input_tokens: int,
    latency_ms: float,
    estimated_cost_usd: float,
    input_cost_per_million_tokens: float,
    total_tokens: int | None = None,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "model": model,
        "latency_ms": round(latency_ms, 3),
        "input_tokens": int(input_tokens),
        "output_tokens": 0,
        "total_tokens": int(total_tokens if total_tokens is not None else input_tokens),
        "estimated_cost_usd": round(estimated_cost_usd, 8),
        "input_cost_per_million_tokens": input_cost_per_million_tokens,
    }


def _usage_int(usage: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = usage.get(key)
        if isinstance(value, int):
            return value
    return 0
