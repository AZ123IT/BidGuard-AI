import hashlib
import math
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import Settings
from app.services.retrieval import tokenize


class EmbeddingError(RuntimeError):
    pass


class EmbeddingProvider(Protocol):
    provider_name: str
    model: str
    dimension: int

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        pass


@dataclass(frozen=True)
class LocalEmbeddingProvider:
    dimension: int
    model: str = "local-hash-v1"
    provider_name: str = "local"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [_normalize(_hash_tokens(text, self.dimension)) for text in texts]


@dataclass(frozen=True)
class OpenAICompatibleEmbeddingProvider:
    api_key: str
    base_url: str
    model: str
    dimension: int
    provider_name: str = "openai_compatible"
    timeout_seconds: float = 30.0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = httpx.post(
                f"{self.base_url.rstrip('/')}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": texts},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"Embedding provider request failed: {exc}") from exc

        payload = response.json()
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
        return embeddings


def make_embedding_provider(settings: Settings) -> EmbeddingProvider:
    provider = settings.embedding_provider.lower()
    if provider in {"local", "fake", "deterministic"}:
        return LocalEmbeddingProvider(
            dimension=settings.embedding_dimension,
            model=settings.embedding_model,
        )
    if provider in {"openai", "openai_compatible", "qwen", "bge"}:
        api_key = settings.embedding_api_key or settings.openai_api_key
        if not api_key:
            raise EmbeddingError(
                "EMBEDDING_API_KEY is required when EMBEDDING_PROVIDER is not local."
            )
        return OpenAICompatibleEmbeddingProvider(
            api_key=api_key,
            base_url=settings.embedding_base_url or settings.openai_base_url,
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
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
