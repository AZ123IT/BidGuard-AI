from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

import httpx

from app.config import Settings
from app.services.retrieval import (
    INSUFFICIENT_EVIDENCE_MESSAGE,
    build_evidence_answer,
    filter_usable_evidence,
    is_evidence_sufficient,
)


class LLMError(RuntimeError):
    pass


class AnswerProvider(Protocol):
    provider_name: str
    model: str
    last_call: dict[str, Any]

    def synthesize(self, question: str, evidence: list[dict]) -> str:
        pass


@dataclass
class DeterministicLLMProvider:
    model: str = "local-fake-v1"
    provider_name: str = "local_fake"
    last_call: dict[str, Any] = field(default_factory=dict, init=False)

    def synthesize(self, question: str, evidence: list[dict]) -> str:
        started = perf_counter()
        answer = build_evidence_answer(question, evidence)["answer"]
        input_tokens = len(question.split()) + sum(len(item.get("text", "").split()) for item in evidence)
        output_tokens = len(answer.split())
        self.last_call = _llm_call_metrics(
            provider=self.provider_name,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=(perf_counter() - started) * 1000,
            estimated_cost_usd=0.0,
            input_cost_per_million_tokens=0.0,
            output_cost_per_million_tokens=0.0,
        )
        return answer


@dataclass
class OpenAICompatibleLLMProvider:
    base_url: str
    model: str
    api_key: str
    temperature: float = 0.0
    provider_name: str = "openai_compatible"
    timeout_seconds: float = 30.0
    input_cost_per_million_tokens: float = 0.0
    cached_input_cost_per_million_tokens: float | None = None
    output_cost_per_million_tokens: float = 0.0
    last_call: dict[str, Any] = field(default_factory=dict, init=False)

    def synthesize(self, question: str, evidence: list[dict]) -> str:
        started = perf_counter()
        evidence_block = "\n\n".join(
            f"[{index}] {item['document_title']} page {item['page_number']}: {item['text']}"
            for index, item in enumerate(evidence, start=1)
        )
        system_prompt = (
            "You are BidGuard AI. Answer only from the provided evidence. "
            "Do not use general knowledge. Do not invent citations. "
            "If the evidence is insufficient, say exactly: "
            f"{INSUFFICIENT_EVIDENCE_MESSAGE}"
        )
        try:
            response = httpx.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "temperature": self.temperature,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": f"Question: {question}\n\nEvidence:\n{evidence_block}",
                        },
                    ],
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise LLMError(f"LLM provider returned HTTP {exc.response.status_code}: {detail}") from exc
        except httpx.TimeoutException as exc:
            raise LLMError(
                f"LLM provider request timed out after {self.timeout_seconds} seconds."
            ) from exc
        except httpx.RequestError as exc:
            raise LLMError(f"LLM provider request failed: {exc}") from exc
        try:
            payload = response.json()
            answer = payload["choices"][0]["message"]["content"].strip()
        except ValueError as exc:
            raise LLMError("LLM provider returned non-JSON response.") from exc
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM provider returned an unexpected response shape.") from exc
        usage = payload.get("usage") if isinstance(payload, dict) else {}
        usage = usage if isinstance(usage, dict) else {}
        input_tokens = _usage_int(usage, "prompt_tokens", "input_tokens")
        cache_hit_input_tokens = _usage_int(usage, "prompt_cache_hit_tokens")
        cache_miss_input_tokens = _usage_int(usage, "prompt_cache_miss_tokens")
        if cache_hit_input_tokens + cache_miss_input_tokens == 0:
            cache_miss_input_tokens = input_tokens
        elif cache_hit_input_tokens + cache_miss_input_tokens < input_tokens:
            cache_miss_input_tokens += input_tokens - (
                cache_hit_input_tokens + cache_miss_input_tokens
            )
        output_tokens = _usage_int(usage, "completion_tokens", "output_tokens")
        total_tokens = _usage_int(usage, "total_tokens") or input_tokens + output_tokens
        cached_input_rate = (
            self.cached_input_cost_per_million_tokens
            if self.cached_input_cost_per_million_tokens is not None
            else self.input_cost_per_million_tokens
        )
        estimated_cost = (
            (cache_hit_input_tokens / 1_000_000) * cached_input_rate
            + (cache_miss_input_tokens / 1_000_000) * self.input_cost_per_million_tokens
            + (output_tokens / 1_000_000) * self.output_cost_per_million_tokens
        )
        self.last_call = _llm_call_metrics(
            provider=self.provider_name,
            model=str(payload.get("model") or self.model),
            input_tokens=input_tokens,
            cache_hit_input_tokens=cache_hit_input_tokens,
            cache_miss_input_tokens=cache_miss_input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=(perf_counter() - started) * 1000,
            estimated_cost_usd=estimated_cost,
            input_cost_per_million_tokens=self.input_cost_per_million_tokens,
            cached_input_cost_per_million_tokens=cached_input_rate,
            output_cost_per_million_tokens=self.output_cost_per_million_tokens,
        )
        return answer


def make_llm_provider(settings: Settings) -> AnswerProvider:
    provider = settings.llm_provider.lower()
    if provider in {"local", "local_fake", "fake", "deterministic"}:
        return DeterministicLLMProvider()
    if provider in {"openai", "openai_compatible", "qwen"}:
        api_key = settings.llm_api_key or settings.openai_api_key
        base_url = settings.llm_base_url or settings.openai_base_url
        if not api_key:
            raise LLMError(
                "LLM_API_KEY or OPENAI_API_KEY is required when "
                f"LLM_PROVIDER={settings.llm_provider}. Use LLM_PROVIDER=local_fake "
                "for zero-config deterministic synthesis."
            )
        if not base_url:
            raise LLMError(
                "LLM_BASE_URL or OPENAI_BASE_URL is required when "
                f"LLM_PROVIDER={settings.llm_provider}."
            )
        if not settings.llm_model:
            raise LLMError(f"LLM_MODEL is required when LLM_PROVIDER={settings.llm_provider}.")
        return OpenAICompatibleLLMProvider(
            base_url=base_url,
            model=settings.llm_model,
            api_key=api_key,
            temperature=settings.llm_temperature,
            timeout_seconds=settings.llm_timeout_seconds,
            input_cost_per_million_tokens=settings.llm_input_cost_per_million_tokens,
            cached_input_cost_per_million_tokens=(
                settings.llm_cached_input_cost_per_million_tokens
            ),
            output_cost_per_million_tokens=settings.llm_output_cost_per_million_tokens,
        )
    raise LLMError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


def guarded_synthesize_answer(
    question: str,
    evidence: list[dict],
    provider: AnswerProvider,
    min_score: float,
    raise_on_provider_error: bool = False,
) -> dict:
    embedding_usage = next(
        (
            dict(item["embedding_usage"])
            for item in evidence
            if isinstance(item.get("embedding_usage"), dict)
        ),
        {},
    )
    usable_evidence = filter_usable_evidence(evidence, min_score=min_score)
    if not usable_evidence or not is_evidence_sufficient(
        question,
        usable_evidence,
        min_score=min_score,
    ):
        return {
            "answer": INSUFFICIENT_EVIDENCE_MESSAGE,
            "evidence": [],
            "confidence": 0.0,
            "llm_synthesis_used": False,
            "synthesis_provider": provider.provider_name,
            "provider_usage": {},
            "embedding_usage": embedding_usage,
        }

    try:
        answer = provider.synthesize(question, usable_evidence)
        synthesis_used = True
    except LLMError:
        if raise_on_provider_error:
            raise
        answer = build_evidence_answer(question, usable_evidence)["answer"]
        synthesis_used = False

    return {
        "answer": answer,
        "evidence": usable_evidence,
        "confidence": round(min(1.0, max(item.get("score", 0.0) for item in usable_evidence)), 4),
        "llm_synthesis_used": synthesis_used,
        "synthesis_provider": provider.provider_name,
        "provider_usage": dict(getattr(provider, "last_call", {})),
        "embedding_usage": embedding_usage,
    }


def _llm_call_metrics(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    estimated_cost_usd: float,
    input_cost_per_million_tokens: float,
    output_cost_per_million_tokens: float,
    total_tokens: int | None = None,
    cache_hit_input_tokens: int = 0,
    cache_miss_input_tokens: int | None = None,
    cached_input_cost_per_million_tokens: float | None = None,
) -> dict[str, Any]:
    cache_miss_input_tokens = (
        input_tokens if cache_miss_input_tokens is None else cache_miss_input_tokens
    )
    cached_input_cost_per_million_tokens = (
        input_cost_per_million_tokens
        if cached_input_cost_per_million_tokens is None
        else cached_input_cost_per_million_tokens
    )
    return {
        "provider": provider,
        "model": model,
        "latency_ms": round(latency_ms, 3),
        "input_tokens": int(input_tokens),
        "cache_hit_input_tokens": int(cache_hit_input_tokens),
        "cache_miss_input_tokens": int(cache_miss_input_tokens),
        "output_tokens": int(output_tokens),
        "total_tokens": int(total_tokens if total_tokens is not None else input_tokens + output_tokens),
        "estimated_cost_usd": round(estimated_cost_usd, 8),
        "input_cost_per_million_tokens": input_cost_per_million_tokens,
        "cached_input_cost_per_million_tokens": cached_input_cost_per_million_tokens,
        "output_cost_per_million_tokens": output_cost_per_million_tokens,
    }


def _usage_int(usage: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = usage.get(key)
        if isinstance(value, int):
            return value
    return 0
