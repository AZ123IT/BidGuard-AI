from typing import Any

from pydantic import BaseModel, Field


class EvidenceChunk(BaseModel):
    chunk_id: int | None = None
    document_id: int
    document_title: str
    page_number: int
    text: str
    score: float


class QARequest(BaseModel):
    question: str = Field(min_length=1)
    document_ids: list[int] = Field(default_factory=list)


class QAResponse(BaseModel):
    answer: str
    evidence: list[EvidenceChunk]
    confidence: float


class RiskCheckRequest(BaseModel):
    document_id: int


class DiffRequest(BaseModel):
    document_a_id: int
    document_b_id: int


class AgentRunRequest(BaseModel):
    objective: str = Field(min_length=1)
    document_ids: list[int] = Field(default_factory=list)
    document_a_id: int | None = None
    document_b_id: int | None = None


class TextPage(BaseModel):
    page_number: int
    text: str


class DevSeedDocumentRequest(BaseModel):
    title: str
    pages: list[TextPage]


class ToolCallView(BaseModel):
    id: int
    tool_name: str
    input_payload: dict[str, Any]
    output_payload: dict[str, Any] | list[Any]
    latency_ms: int


class AgentRunView(BaseModel):
    id: int
    objective: str
    status: str
    answer: dict[str, Any] | None
    latency_ms: int
    tool_calls: list[ToolCallView]
