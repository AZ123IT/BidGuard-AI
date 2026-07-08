from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import Settings
from app.services.retrieval import (
    INSUFFICIENT_EVIDENCE_MESSAGE,
    build_evidence_answer,
    is_evidence_sufficient,
)


class LLMError(RuntimeError):
    pass


class AnswerProvider(Protocol):
    provider_name: str
    model: str

    def synthesize(self, question: str, evidence: list[dict]) -> str:
        pass


@dataclass(frozen=True)
class DeterministicLLMProvider:
    model: str = "local-fake-v1"
    provider_name: str = "local_fake"

    def synthesize(self, question: str, evidence: list[dict]) -> str:
        return build_evidence_answer(question, evidence)["answer"]


@dataclass(frozen=True)
class OpenAICompatibleLLMProvider:
    base_url: str
    model: str
    api_key: str
    temperature: float = 0.0
    provider_name: str = "openai_compatible"
    timeout_seconds: float = 30.0

    def synthesize(self, question: str, evidence: list[dict]) -> str:
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
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM provider request failed: {exc}") from exc
        try:
            return response.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM provider returned an unexpected response shape.") from exc


def make_llm_provider(settings: Settings) -> AnswerProvider:
    provider = settings.llm_provider.lower()
    if provider in {"local", "local_fake", "fake", "deterministic"}:
        return DeterministicLLMProvider(model=settings.llm_model)
    if provider in {"openai", "openai_compatible", "qwen"}:
        api_key = settings.llm_api_key or settings.openai_api_key
        if not api_key:
            raise LLMError("LLM_API_KEY is required when LLM_PROVIDER is not local_fake.")
        return OpenAICompatibleLLMProvider(
            base_url=settings.llm_base_url or settings.openai_base_url,
            model=settings.llm_model,
            api_key=api_key,
            temperature=settings.llm_temperature,
        )
    raise LLMError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


def guarded_synthesize_answer(
    question: str,
    evidence: list[dict],
    provider: AnswerProvider,
    min_score: float,
) -> dict:
    if not is_evidence_sufficient(evidence, min_score=min_score):
        return {
            "answer": INSUFFICIENT_EVIDENCE_MESSAGE,
            "evidence": [],
            "confidence": 0.0,
            "llm_synthesis_used": False,
            "synthesis_provider": provider.provider_name,
        }

    try:
        answer = provider.synthesize(question, evidence)
        synthesis_used = True
    except LLMError:
        answer = build_evidence_answer(question, evidence)["answer"]
        synthesis_used = False

    return {
        "answer": answer,
        "evidence": evidence,
        "confidence": round(min(1.0, max(item.get("score", 0.0) for item in evidence)), 4),
        "llm_synthesis_used": synthesis_used,
        "synthesis_provider": provider.provider_name,
    }
