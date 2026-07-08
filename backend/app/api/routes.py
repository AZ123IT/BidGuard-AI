from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_session
from app.models import AgentRun, Document, DocumentChunk, ExtractedField, RiskFinding
from app.schemas import (
    AgentRunRequest,
    DevSeedDocumentRequest,
    DiffRequest,
    QARequest,
    RiskCheckRequest,
)
from app.services.agent import (
    cross_doc_diff_tool,
    risk_rule_check_tool,
    run_agent,
)
from app.services.chunking import chunk_pages
from app.services.embeddings import EmbeddingError, make_embedding_provider
from app.services.field_extractor import extract_fields
from app.services.llm import guarded_synthesize_answer, make_llm_provider
from app.services.pdf_parser import extract_pdf_pages
from app.services.retrieval import retrieve_document_evidence

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "bidguard-ai-backend"}


@router.get("/dashboard")
def dashboard(session: Annotated[Session, Depends(get_session)]) -> dict:
    document_count = session.scalar(select(func.count(Document.id))) or 0
    risk_finding_count = session.scalar(select(func.count(RiskFinding.id))) or 0
    recent_runs = session.scalars(
        select(AgentRun).options(selectinload(AgentRun.tool_calls)).order_by(AgentRun.id.desc()).limit(5)
    ).all()
    return {
        "document_count": document_count,
        "risk_finding_count": risk_finding_count,
        "recent_agent_runs": [_agent_run_view(run) for run in recent_runs],
    }


@router.post("/documents/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    file: Annotated[UploadFile, File()],
) -> dict:
    is_pdf = file.content_type == "application/pdf" or file.filename.lower().endswith(".pdf")
    is_text = (file.content_type or "").startswith("text/") or file.filename.lower().endswith(".txt")
    if not is_pdf and not is_text:
        raise HTTPException(status_code=400, detail="Only PDF and TXT uploads are supported.")
    content = await file.read()
    try:
        pages = extract_pdf_pages(content) if is_pdf else [{"page_number": 1, "text": content.decode("utf-8")}]
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="The uploaded text file must be UTF-8 encoded.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    title = Path(file.filename).stem or "Untitled document"
    document = Document(
        title=title,
        filename=file.filename,
        content_type=file.content_type or "application/pdf",
        status="complete",
        page_count=len(pages),
    )
    session.add(document)
    session.flush()

    upload_dir: Path = request.app.state.settings.resolved_upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = upload_dir / f"{document.id}-{Path(file.filename).name}"
    saved_path.write_bytes(content)
    document.source_path = str(saved_path)
    try:
        _store_extraction(session, document, pages, request.app.state.settings)
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    session.flush()
    return _document_detail(document)


@router.get("/documents")
def list_documents(session: Annotated[Session, Depends(get_session)]) -> dict:
    documents = session.scalars(select(Document).order_by(Document.created_at.desc())).all()
    return {"items": [_document_summary(document) for document in documents]}


@router.get("/documents/{document_id}")
def get_document(document_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return _document_detail(document)


@router.post("/qa")
def question_answer(
    payload: QARequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    document_ids = payload.document_ids
    if not document_ids:
        document_ids = [item[0] for item in session.execute(select(Document.id)).all()]
    settings = request.app.state.settings
    evidence = retrieve_document_evidence(
        session=session,
        settings=settings,
        question=payload.question,
        document_ids=document_ids,
        limit=settings.retrieval_limit,
    )
    return guarded_synthesize_answer(
        question=payload.question,
        evidence=evidence,
        provider=make_llm_provider(settings),
        min_score=settings.min_retrieval_score,
    )


@router.post("/risk-check")
def risk_check(
    payload: RiskCheckRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    try:
        findings = risk_rule_check_tool(session, payload.document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"document_id": payload.document_id, "findings": findings}


@router.post("/diff")
def diff_documents(payload: DiffRequest, session: Annotated[Session, Depends(get_session)]) -> dict:
    if not session.get(Document, payload.document_a_id) or not session.get(Document, payload.document_b_id):
        raise HTTPException(status_code=404, detail="One or both documents were not found.")
    rows = cross_doc_diff_tool(session, payload.document_a_id, payload.document_b_id)
    return {
        "document_a_id": payload.document_a_id,
        "document_b_id": payload.document_b_id,
        "differences": rows,
    }


@router.post("/agent/run")
def agent_run(
    payload: AgentRunRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    try:
        return run_agent(
            session=session,
            settings=request.app.state.settings,
            objective=payload.objective,
            document_ids=payload.document_ids,
            document_a_id=payload.document_a_id,
            document_b_id=payload.document_b_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/agent/runs")
def list_agent_runs(session: Annotated[Session, Depends(get_session)]) -> dict:
    runs = session.scalars(
        select(AgentRun).options(selectinload(AgentRun.tool_calls)).order_by(AgentRun.id.desc()).limit(20)
    ).all()
    return {"items": [_agent_run_view(run) for run in runs]}


@router.post("/dev/seed-text-document", status_code=status.HTTP_201_CREATED)
def seed_text_document(
    payload: DevSeedDocumentRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    pages = [page.model_dump() for page in payload.pages]
    document = Document(
        title=payload.title,
        filename=f"{payload.title}.txt",
        content_type="text/plain",
        status="complete",
        page_count=len(pages),
    )
    session.add(document)
    session.flush()
    try:
        _store_extraction(session, document, pages, request.app.state.settings)
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    session.flush()
    return _document_detail(document)


def _store_extraction(session: Session, document: Document, pages: list[dict], settings) -> None:
    session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    session.execute(delete(ExtractedField).where(ExtractedField.document_id == document.id))
    chunk_payloads = chunk_pages(document.id, pages)
    provider = make_embedding_provider(settings)
    embeddings = provider.embed_texts([chunk["text"] for chunk in chunk_payloads])
    chunk_models: list[DocumentChunk] = []
    for chunk, embedding in zip(chunk_payloads, embeddings, strict=True):
        chunk_model = DocumentChunk(
            **chunk,
            embedding=embedding,
            embedding_provider=provider.provider_name,
            embedding_model=provider.model,
            embedding_dimension=provider.dimension,
        )
        chunk_models.append(chunk_model)
        session.add(chunk_model)
    session.flush()
    _store_pgvector_embeddings(session, chunk_models)
    for field_name, field in extract_fields(pages).items():
        session.add(
            ExtractedField(
                document_id=document.id,
                field_name=field_name,
                value=field["value"],
                page_number=field["page_number"],
                confidence=field["confidence"],
                evidence_text=field["evidence_text"],
            )
        )


def _document_summary(document: Document) -> dict:
    return {
        "id": document.id,
        "title": document.title,
        "filename": document.filename,
        "content_type": document.content_type,
        "status": document.status,
        "page_count": document.page_count,
        "created_at": document.created_at.isoformat() if document.created_at else None,
    }


def _document_detail(document: Document) -> dict:
    fields = {
        field.field_name: {
            "value": field.value,
            "page_number": field.page_number,
            "confidence": field.confidence,
            "evidence_text": field.evidence_text,
        }
        for field in document.extracted_fields
    }
    return {
        **_document_summary(document),
        "chunk_count": len(document.chunks),
        "embedding_status": _embedding_status(document),
        "risk_finding_count": len(document.risk_findings),
        "extracted_fields": fields,
        "error_message": document.error_message,
    }


def _agent_run_view(run: AgentRun) -> dict:
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


def _embedding_status(document: Document) -> str:
    if not document.chunks:
        return "not_chunked"
    return "embedded" if all(chunk.embedding for chunk in document.chunks) else "missing"


def _store_pgvector_embeddings(session: Session, chunks: list[DocumentChunk]) -> None:
    if session.bind is None or session.bind.dialect.name != "postgresql":
        return
    from sqlalchemy import text

    for chunk in chunks:
        if chunk.embedding:
            vector_literal = "[" + ",".join(str(value) for value in chunk.embedding) + "]"
            session.execute(
                text(
                    "UPDATE document_chunks SET embedding_vector = CAST(:embedding AS vector) "
                    "WHERE id = :chunk_id"
                ),
                {"embedding": vector_literal, "chunk_id": chunk.id},
            )


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
