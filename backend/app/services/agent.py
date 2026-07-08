import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import (
    AgentRun,
    Document,
    ExtractedField,
    RiskFinding,
    ToolCall,
)
from app.services.diff import compare_extracted_fields
from app.services.llm import guarded_synthesize_answer, make_llm_provider
from app.services.retrieval import (
    build_evidence_answer,
    is_evidence_sufficient,
    retrieve_document_evidence,
)
from app.services.risk_rules import check_risk_rules


def run_agent(
    session: Session,
    settings: Settings,
    objective: str,
    document_ids: list[int],
    document_a_id: int | None = None,
    document_b_id: int | None = None,
) -> dict:
    started = time.perf_counter()
    run = AgentRun(objective=objective, status="running")
    session.add(run)
    session.flush()

    lower_objective = objective.lower()
    tool_outputs: dict[str, Any] = {}

    if document_a_id and document_b_id:
        tool_outputs["cross_doc_diff_tool"] = _record_tool_call(
            session,
            run,
            "cross_doc_diff_tool",
            {"document_a_id": document_a_id, "document_b_id": document_b_id},
            lambda: cross_doc_diff_tool(session, document_a_id, document_b_id),
        )

    if document_ids and any(term in lower_objective for term in ["risk", "review", "check", "report"]):
        tool_outputs["risk_rule_check_tool"] = _record_tool_call(
            session,
            run,
            "risk_rule_check_tool",
            {"document_id": document_ids[0]},
            lambda: risk_rule_check_tool(session, document_ids[0]),
        )

    if document_ids and ("report" in lower_objective or "summary" in lower_objective):
        findings = tool_outputs.get("risk_rule_check_tool") or risk_rule_check_tool(session, document_ids[0])
        tool_outputs["report_generator_tool"] = _record_tool_call(
            session,
            run,
            "report_generator_tool",
            {"document_id": document_ids[0], "finding_count": len(findings)},
            lambda: report_generator_tool(session, document_ids[0], findings),
        )

    if document_ids:
        tool_outputs["evidence_search_tool"] = _record_tool_call(
            session,
            run,
            "evidence_search_tool",
            {"question": objective, "document_ids": document_ids},
            lambda: evidence_search_tool(session, settings, objective, document_ids),
        )
        if is_evidence_sufficient(
            tool_outputs["evidence_search_tool"],
            min_score=settings.min_retrieval_score,
        ):
            answer = _record_tool_call(
                session,
                run,
                "guarded_llm_synthesis",
                {
                    "question": objective,
                    "evidence_count": len(tool_outputs["evidence_search_tool"]),
                },
                lambda: guarded_synthesize_answer(
                    question=objective,
                    evidence=tool_outputs["evidence_search_tool"],
                    provider=make_llm_provider(settings),
                    min_score=settings.min_retrieval_score,
                )
                | {"success": True},
            )
        else:
            answer = build_evidence_answer(
                objective,
                tool_outputs["evidence_search_tool"],
                min_score=settings.min_retrieval_score,
            )
    elif "cross_doc_diff_tool" in tool_outputs:
        answer = {
            "answer": "Comparison completed. Review the structured differences for fields marked changed or uncertain.",
            "evidence": [],
            "confidence": 0.5,
        }
    else:
        answer = {
            "answer": "Select at least one document so the agent can ground its work in uploaded evidence.",
            "evidence": [],
            "confidence": 0.0,
        }

    run.status = "completed"
    run.answer = answer
    run.latency_ms = int((time.perf_counter() - started) * 1000)
    session.flush()
    return _agent_run_to_dict(run)


def evidence_search_tool(
    session: Session,
    settings: Settings,
    question: str,
    document_ids: list[int],
) -> list[dict]:
    return retrieve_document_evidence(
        session=session,
        settings=settings,
        question=question,
        document_ids=document_ids,
        limit=settings.retrieval_limit,
    )


def risk_rule_check_tool(session: Session, document_id: int) -> list[dict]:
    document = _get_document(session, document_id)
    pages = _pages_from_chunks(document)
    findings = check_risk_rules(document_id, pages)
    session.execute(delete(RiskFinding).where(RiskFinding.document_id == document_id))
    for finding in findings:
        session.add(RiskFinding(**finding))
    session.flush()
    return findings


def cross_doc_diff_tool(session: Session, document_a_id: int, document_b_id: int) -> list[dict]:
    left = _fields_for_document(session, document_a_id)
    right = _fields_for_document(session, document_b_id)
    return compare_extracted_fields(left, right)


def report_generator_tool(session: Session, document_id: int, findings: list[dict]) -> dict:
    document = _get_document(session, document_id)
    high_count = sum(1 for finding in findings if finding["severity"] == "high")
    medium_count = sum(1 for finding in findings if finding["severity"] == "medium")
    return {
        "document_id": document.id,
        "document_title": document.title,
        "summary": f"{document.title} has {len(findings)} rule-based findings: {high_count} high and {medium_count} medium.",
        "findings": findings,
        "disclaimer": "This report is evidence-first engineering output and is not professional legal advice.",
    }


def _record_tool_call(
    session: Session,
    run: AgentRun,
    tool_name: str,
    input_payload: dict[str, Any],
    tool: Callable[[], dict | list],
) -> dict | list:
    started = time.perf_counter()
    output = tool()
    call = ToolCall(
        agent_run=run,
        tool_name=tool_name,
        input_payload=input_payload,
        output_payload=output,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
    session.add(call)
    session.flush()
    return output


def _get_document(session: Session, document_id: int) -> Document:
    document = session.get(Document, document_id)
    if not document:
        raise ValueError(f"Document {document_id} does not exist.")
    return document


def _pages_from_chunks(document: Document) -> list[dict]:
    pages_by_number: dict[int, list[str]] = {}
    for chunk in sorted(document.chunks, key=lambda item: (item.page_number, item.chunk_index)):
        pages_by_number.setdefault(chunk.page_number, []).append(chunk.text)
    return [
        {"page_number": page_number, "text": "\n".join(texts)}
        for page_number, texts in sorted(pages_by_number.items())
    ]


def _fields_for_document(session: Session, document_id: int) -> dict[str, dict]:
    fields = session.scalars(
        select(ExtractedField).where(ExtractedField.document_id == document_id)
    ).all()
    return {
        field.field_name: {
            "value": field.value,
            "page_number": field.page_number,
            "confidence": field.confidence,
            "evidence_text": field.evidence_text,
        }
        for field in fields
    }


def _agent_run_to_dict(run: AgentRun) -> dict:
    return {
        "id": run.id,
        "objective": run.objective,
        "status": run.status,
        "answer": run.answer,
        "latency_ms": run.latency_ms,
        "tool_calls": [
            {
                "id": call.id,
                "tool_name": call.tool_name,
                "input_payload": call.input_payload,
                "output_payload": call.output_payload,
                "latency_ms": call.latency_ms,
                "status": _tool_status(call.output_payload),
                "evidence_count": _tool_evidence_count(call.output_payload),
            }
            for call in run.tool_calls
        ],
    }


def _tool_status(output_payload) -> str:
    if isinstance(output_payload, dict):
        return "success" if output_payload.get("success", True) else "failed"
    return "success"


def _tool_evidence_count(output_payload) -> int:
    if isinstance(output_payload, list):
        return len(output_payload)
    if isinstance(output_payload, dict):
        evidence = output_payload.get("evidence")
        if isinstance(evidence, list):
            return len(evidence)
        if "evidence_count" in output_payload:
            return int(output_payload["evidence_count"])
    return 0
