import re
from collections import Counter
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.models import DocumentChunk

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "The uploaded documents do not contain enough evidence to answer this question reliably."
)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
}


def tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOPWORDS]


def _get_value(chunk: Any, key: str, default: Any = None) -> Any:
    if isinstance(chunk, dict):
        return chunk.get(key, default)
    return getattr(chunk, key, default)


def _document_title(chunk: Any) -> str:
    title = _get_value(chunk, "document_title")
    if title:
        return title
    document = _get_value(chunk, "document")
    return getattr(document, "title", "Unknown document")


def retrieve_relevant_chunks(
    question: str,
    chunks: list[Any],
    limit: int = 5,
    query_embedding: list[float] | None = None,
    retrieval_method: str = "keyword",
) -> list[dict]:
    from app.services.embeddings import cosine_similarity

    query_tokens = tokenize(question)
    if not query_tokens:
        return []
    query_counter = Counter(query_tokens)
    scored: list[dict] = []
    for chunk in chunks:
        text = _get_value(chunk, "text", "")
        text_tokens = tokenize(text)
        if not text_tokens:
            continue
        text_counter = Counter(text_tokens)
        raw_overlap = sum(min(count, text_counter[token]) for token, count in query_counter.items())
        phrase_bonus = 0.0
        lower_text = text.lower()
        if "bid deadline" in question.lower() and "bid deadline" in lower_text:
            phrase_bonus += 1.5
        if "opening time" in question.lower() and "opening time" in lower_text:
            phrase_bonus += 1.5
        if "acceptance" in question.lower() and "acceptance criteria" in lower_text:
            phrase_bonus += 1.5
        if "payment" in question.lower() and "payment terms" in lower_text:
            phrase_bonus += 1.5
        if "dispute" in question.lower() and "dispute resolution" in lower_text:
            phrase_bonus += 1.5
        if "contract amount" in question.lower() and "contract amount" in lower_text:
            phrase_bonus += 1.5
        keyword_score = (raw_overlap + phrase_bonus) / max(len(set(query_tokens)), 1)
        similarity_score = cosine_similarity(query_embedding, _get_value(chunk, "embedding"))
        if query_embedding is not None and _get_value(chunk, "embedding"):
            if keyword_score > 0:
                score = (keyword_score * 0.6) + (max(similarity_score, 0.0) * 0.4)
            else:
                score = max(similarity_score, 0.0) * 0.05
        else:
            score = keyword_score
        scored.append(
            {
                "chunk_id": _get_value(chunk, "id"),
                "document_id": _get_value(chunk, "document_id"),
                "document_title": _document_title(chunk),
                "page_number": _get_value(chunk, "page_number"),
                "text": text,
                "score": round(score, 4),
                "similarity_score": round(max(similarity_score, 0.0), 4),
                "keyword_score": round(keyword_score, 4),
                "retrieval_method": retrieval_method,
                "has_keyword_match": keyword_score > 0,
            }
        )
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]


def retrieve_document_evidence(
    session: Session,
    settings: Settings,
    question: str,
    document_ids: list[int],
    limit: int,
) -> list[dict]:
    from app.services.embeddings import EmbeddingError, make_embedding_provider

    provider = make_embedding_provider(settings)
    try:
        query_embedding = provider.embed_texts([question])[0]
    except EmbeddingError:
        query_embedding = None

    if session.bind is not None and session.bind.dialect.name == "postgresql" and query_embedding:
        pgvector_results = _try_pgvector_search(session, question, document_ids, query_embedding, limit)
        if pgvector_results:
            return pgvector_results

    chunks = session.scalars(
        select(DocumentChunk)
        .options(selectinload(DocumentChunk.document))
        .where(DocumentChunk.document_id.in_(document_ids))
    ).all()
    return retrieve_relevant_chunks(
        question,
        list(chunks),
        limit=limit,
        query_embedding=query_embedding,
        retrieval_method="hybrid_fallback",
    )


def _try_pgvector_search(
    session: Session,
    question: str,
    document_ids: list[int],
    query_embedding: list[float],
    limit: int,
) -> list[dict]:
    vector_literal = "[" + ",".join(str(value) for value in query_embedding) + "]"
    try:
        rows = session.execute(
            text(
                """
                SELECT
                    c.id AS chunk_id,
                    c.document_id AS document_id,
                    d.title AS document_title,
                    c.page_number AS page_number,
                    c.text AS text,
                    c.embedding AS embedding,
                    1 - (c.embedding_vector <=> CAST(:query_embedding AS vector)) AS similarity_score
                FROM document_chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.document_id = ANY(:document_ids)
                  AND c.embedding_vector IS NOT NULL
                ORDER BY c.embedding_vector <=> CAST(:query_embedding AS vector)
                LIMIT :limit
                """
            ),
            {
                "query_embedding": vector_literal,
                "document_ids": document_ids,
                "limit": limit,
            },
        ).mappings()
    except Exception:
        session.rollback()
        return []

    candidates = []
    for row in rows:
        candidate = dict(row)
        candidate["id"] = candidate["chunk_id"]
        candidates.append(candidate)
    return retrieve_relevant_chunks(
        question,
        candidates,
        limit=limit,
        query_embedding=query_embedding,
        retrieval_method="pgvector",
    )


def is_evidence_sufficient(evidence: list[dict], min_score: float = 0.05) -> bool:
    usable_evidence = [
        item
        for item in evidence
        if item.get("score", 0) >= min_score
        and (
            item.get("has_keyword_match", item.get("score", 0) > 0)
            or item.get("retrieval_method") == "pgvector"
        )
    ]
    return bool(usable_evidence)


def build_evidence_answer(question: str, evidence: list[dict], min_score: float = 0.05) -> dict:
    usable_evidence = [
        item
        for item in evidence
        if item.get("score", 0) >= min_score
        and (item.get("has_keyword_match", item.get("score", 0) > 0) or item.get("retrieval_method") == "pgvector")
    ]
    if not usable_evidence:
        return {
            "answer": INSUFFICIENT_EVIDENCE_MESSAGE,
            "evidence": [],
            "confidence": 0.0,
            "llm_synthesis_used": False,
            "synthesis_provider": None,
        }

    top = usable_evidence[0]
    sentence = _best_sentence(question, top["text"])
    answer = (
        f"Based on {top['document_title']} page {top['page_number']}, {sentence}"
        if sentence
        else f"Based on {top['document_title']} page {top['page_number']}, the retrieved evidence is relevant but should be reviewed directly."
    )
    confidence = min(1.0, max(item["score"] for item in usable_evidence))
    return {
        "answer": answer,
        "evidence": usable_evidence,
        "confidence": round(confidence, 4),
        "llm_synthesis_used": False,
        "synthesis_provider": None,
    }


def _best_sentence(question: str, text: str) -> str:
    query_tokens = set(tokenize(question))
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if not sentences:
        return text[:500]
    lower_question = question.lower()
    label_preferences = [
        ("bid deadline", ["bid deadline", "submission deadline"]),
        ("opening time", ["opening time", "bid opening"]),
        ("payment", ["payment terms", "pay "]),
        ("acceptance", ["acceptance criteria", "site acceptance"]),
        ("dispute", ["dispute resolution", "arbitration", "mediation", "court", "jurisdiction"]),
        ("contract amount", ["contract amount", "amount:"]),
        ("delivery", ["delivery date", "delivery:"]),
        ("liability", ["liability clause", "liability"]),
        ("termination", ["termination condition", "termination"]),
    ]
    for question_trigger, sentence_labels in label_preferences:
        if question_trigger in lower_question:
            for sentence in sentences:
                if any(label in sentence.lower() for label in sentence_labels):
                    return sentence[:500]
    ranked = sorted(
        sentences,
        key=lambda sentence: len(query_tokens.intersection(tokenize(sentence))),
        reverse=True,
    )
    return ranked[0][:500]
