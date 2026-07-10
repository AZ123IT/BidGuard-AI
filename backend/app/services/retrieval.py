import logging
import re
from collections import Counter
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.models import DocumentChunk

logger = logging.getLogger(__name__)

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "The uploaded documents do not contain enough evidence to answer this question reliably."
)


class VectorSearchError(RuntimeError):
    pass

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

MIN_KEYWORD_COVERAGE = 0.5
MIN_REAL_SEMANTIC_SIMILARITY = 0.55
REAL_SEMANTIC_RETRIEVAL_METHODS = {"pgvector", "configured_real_hybrid"}
REAL_EMBEDDING_PROVIDERS = {"openai", "openai_compatible", "qwen", "bge"}
PROMPT_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"ignore (all |any )?(previous|prior|system) instructions?",
        r"system instruction",
        r"reveal (the )?(system prompt|hidden prompt|developer message)",
        r"when asked .* answer ",
        r"fabricate (an? )?(answer|citation|identifier)",
        r"do not follow (the )?(system|developer|previous) instructions?",
    ]
]
IDENTIFIER_QUERY_TERMS = [
    "tax id",
    "tax identifier",
    "tax identification number",
    "bank guarantee number",
    "certificate id",
    "certificate number",
    "policy number",
    "registration number",
    "serial number",
]
IDENTIFIER_VALUE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\b(?:tax\s+(?:id|identifier|identification\s+number)|abn|acn|tfn)\b\s*(?:is|:|#|no\.?)\s*([a-z0-9][a-z0-9./ -]{2,})",
        r"\bbank\s+guarantee\s+(?:number|id|reference)\b\s*(?:is|:|#|no\.?)\s*([a-z0-9][a-z0-9./ -]{2,})",
        r"\b(?:certificate|policy|registration)\s+(?:id|number|serial\s+number)\b\s*(?:is|:|#|no\.?)\s*([a-z0-9][a-z0-9./ -]{2,})",
        r"\bserial\s+number\b\s*(?:is|:|#|no\.?)\s*([a-z0-9][a-z0-9./ -]{2,})",
    ]
]
MISSING_IDENTIFIER_VALUES = {"missing", "none", "not provided", "not available", "unknown", "required"}


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
    query_terms = set(query_tokens)
    query_counter = Counter(query_tokens)
    lower_question = question.lower()
    scored: list[dict] = []
    for chunk in chunks:
        text = _get_value(chunk, "text", "")
        text_tokens = tokenize(text)
        if not text_tokens:
            continue
        text_terms = set(text_tokens)
        text_counter = Counter(text_tokens)
        raw_overlap = sum(min(count, text_counter[token]) for token, count in query_counter.items())
        matched_unique_terms = len(query_terms.intersection(text_terms))
        keyword_coverage = matched_unique_terms / max(len(query_terms), 1)
        lower_text = text.lower()
        prompt_injection_detected = detect_prompt_injection(text)
        embedding_provider = str(_get_value(chunk, "embedding_provider", "")).lower()
        real_semantic_path = (
            retrieval_method in REAL_SEMANTIC_RETRIEVAL_METHODS
            and embedding_provider in REAL_EMBEDDING_PROVIDERS
        )
        phrase_bonus, phrase_match = _domain_phrase_match(lower_question, lower_text)
        scope_score = _document_scope_score(
            lower_question,
            lower_text,
            _document_title(chunk).lower(),
        )
        keyword_score = max(
            0.0,
            (raw_overlap + phrase_bonus) / max(len(set(query_tokens)), 1),
        )
        similarity_score = cosine_similarity(query_embedding, _get_value(chunk, "embedding"))
        if query_embedding is not None and _get_value(chunk, "embedding"):
            if keyword_score > 0:
                score = (keyword_score * 0.6) + (max(similarity_score, 0.0) * 0.4)
            elif real_semantic_path:
                score = max(similarity_score, 0.0)
            else:
                score = max(similarity_score, 0.0) * 0.05
        else:
            score = keyword_score
        # An explicit document version in the question is a retrieval constraint,
        # not another weak keyword. Apply it after hybrid scoring so a semantically
        # similar revision cannot outrank the requested original (or vice versa).
        score = max(0.0, score + (scope_score * 0.25))
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
                "keyword_coverage": round(keyword_coverage, 4),
                "phrase_match": phrase_match,
                "document_scope_score": round(scope_score, 4),
                "prompt_injection_detected": prompt_injection_detected,
                "embedding_provider": embedding_provider or None,
                "embedding_model": _get_value(chunk, "embedding_model"),
                "embedding_dimension": _get_value(chunk, "embedding_dimension"),
                "retrieval_method": retrieval_method,
                "has_keyword_match": matched_unique_terms > 0,
            }
        )
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]


def _domain_phrase_match(lower_question: str, lower_text: str) -> tuple[float, bool]:
    phrase_groups = [
        (
            ["bid deadline", "submission deadline", "closing date", "closing time", "deadline"],
            ["bid deadline", "submission deadline", "closing date", "closing time", "tender closing"],
        ),
        (["opening time", "bid opening", "tender opening"], ["opening time", "bid opening", "tender opening"]),
        (
            ["payment", "invoice", "payment period"],
            ["payment terms", "pay the supplier", "pay within", "within 45 days", "within 60 days", "within 90 days"],
        ),
        (["acceptance"], ["acceptance criteria", "site acceptance", "acceptance requires"]),
        (["dispute", "arbitration", "mediation"], ["dispute resolution", "arbitration", "mediation", "court", "jurisdiction"]),
        (["contract amount", "amount", "contract value", "price"], ["contract amount", "contract value", "fixed price", "amount:"]),
        (["delivery", "completion date"], ["delivery date", "completion date", "delivery:"]),
        (["liability"], ["liability clause", "liability cap", "liability is capped"]),
        (["termination"], ["termination condition", "terminate", "termination"]),
    ]

    bonus = 0.0
    matched = False
    for question_terms, text_terms in phrase_groups:
        if _contains_any(lower_question, question_terms) and _contains_any(lower_text, text_terms):
            bonus += 1.5
            matched = True

    identifier_question = "tax" in lower_question and _contains_any(
        lower_question,
        ["id", "identifier", "identification", "number"],
    )
    identifier_text = (
        ("tax" in lower_text and _contains_any(lower_text, ["id", "identifier", "identification", "number"]))
        or _contains_any(lower_text, ["abn", "acn", "tax file number", "tfn"])
    )
    if identifier_question and identifier_text:
        bonus += 1.5
        matched = True

    return bonus, matched


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def detect_prompt_injection(text: str) -> bool:
    return any(pattern.search(text) for pattern in PROMPT_INJECTION_PATTERNS)


def _document_scope_score(lower_question: str, lower_text: str, document_title: str) -> float:
    score = 0.0
    asks_for_original = any(
        phrase in lower_question
        for phrase in ["original contract", "original draft", "contract draft", "not the revised"]
    )
    revision_is_negated = "not the revised" in lower_question or "not revised" in lower_question
    asks_for_revised = not revision_is_negated and any(
        phrase in lower_question
        for phrase in ["revised contract", "revised draft", "addendum", "updated contract"]
    )
    is_original = (
        "document type: contract draft" in lower_text
        or ("draft" in document_title and "revised" not in document_title)
        or "original" in document_title
    )
    is_revised = (
        "revised contract" in lower_text
        or "contract addendum" in lower_text
        or "revised" in document_title
        or "addendum" in document_title
    )
    if asks_for_original:
        score += 2.0 if is_original else 0.0
        score -= 2.0 if is_revised else 0.0
    if asks_for_revised:
        score += 2.0 if is_revised else 0.0
        score -= 2.0 if is_original else 0.0
    return score


def retrieve_document_evidence(
    session: Session,
    settings: Settings,
    question: str,
    document_ids: list[int],
    limit: int,
) -> list[dict]:
    from app.services.embeddings import EmbeddingError, make_embedding_provider

    provider = make_embedding_provider(settings)
    fallback_reason = None
    try:
        query_embedding = provider.embed_texts([question])[0]
    except EmbeddingError as exc:
        fallback_reason = f"Embedding query failed: {exc}"
        logger.warning(fallback_reason)
        query_embedding = None

    if session.bind is not None and session.bind.dialect.name == "postgresql" and query_embedding:
        try:
            pgvector_results = _try_pgvector_search(
                session,
                question,
                document_ids,
                query_embedding,
                limit,
            )
        except VectorSearchError as exc:
            fallback_reason = str(exc)
            logger.warning(fallback_reason)
            pgvector_results = []
        if pgvector_results:
            return _attach_embedding_observability(pgvector_results, provider)

    chunks = session.scalars(
        select(DocumentChunk)
        .options(selectinload(DocumentChunk.document))
        .where(DocumentChunk.document_id.in_(document_ids))
    ).all()
    fallback_method = (
        "configured_real_hybrid"
        if provider.provider_name in REAL_EMBEDDING_PROVIDERS
        else "hybrid_fallback"
    )
    results = retrieve_relevant_chunks(
        question,
        list(chunks),
        limit=limit,
        query_embedding=query_embedding,
        retrieval_method=fallback_method,
    )
    results = _attach_embedding_observability(results, provider)
    if fallback_reason:
        for item in results:
            item["retrieval_fallback_reason"] = fallback_reason
    return results


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
                    c.embedding_provider AS embedding_provider,
                    c.embedding_model AS embedding_model,
                    c.embedding_dimension AS embedding_dimension,
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
    except Exception as exc:
        session.rollback()
        raise VectorSearchError(f"pgvector query failed: {exc}") from exc

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


def is_evidence_sufficient(
    question: str,
    evidence: list[dict],
    min_score: float = 0.05,
) -> bool:
    usable_evidence = filter_usable_evidence(evidence, min_score=min_score)
    if not usable_evidence:
        return False
    if _question_requires_identifier(question):
        return any(_contains_identifier_value(item.get("text", "")) for item in usable_evidence)
    return True


def build_evidence_answer(question: str, evidence: list[dict], min_score: float = 0.05) -> dict:
    usable_evidence = filter_usable_evidence(evidence, min_score=min_score)
    if not is_evidence_sufficient(question, usable_evidence, min_score=min_score):
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


def filter_usable_evidence(evidence: list[dict], min_score: float) -> list[dict]:
    usable = []
    for item in evidence:
        if item.get("prompt_injection_detected"):
            continue
        if item.get("score", 0) < min_score:
            continue
        has_keyword_match = item.get("has_keyword_match", item.get("score", 0) > 0)
        semantic_match = (
            item.get("retrieval_method") in REAL_SEMANTIC_RETRIEVAL_METHODS
            and item.get("embedding_provider") in REAL_EMBEDDING_PROVIDERS
            and item.get("similarity_score", 0) >= MIN_REAL_SEMANTIC_SIMILARITY
        )
        if not has_keyword_match and not semantic_match:
            continue
        keyword_coverage = item.get("keyword_coverage")
        if keyword_coverage is None:
            usable.append(item)
            continue
        if (
            semantic_match
            or item.get("phrase_match")
            or keyword_coverage >= MIN_KEYWORD_COVERAGE
            or item.get("keyword_score", 0) >= 0.75
        ):
            usable.append(item)
    return usable


def _question_requires_identifier(question: str) -> bool:
    lower_question = question.lower()
    return "identifier" in lower_question or any(
        term in lower_question for term in IDENTIFIER_QUERY_TERMS
    )


def _contains_identifier_value(text: str) -> bool:
    for pattern in IDENTIFIER_VALUE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        value = match.group(1).strip(" .,:;").lower()
        if value and value not in MISSING_IDENTIFIER_VALUES:
            return True
    return False


def _attach_embedding_observability(results: list[dict], provider) -> list[dict]:
    usage = dict(getattr(provider, "last_call", {}))
    for item in results:
        item["embedding_provider"] = provider.provider_name
        item["embedding_model"] = provider.model
        item["embedding_usage"] = usage
    return results


def _best_sentence(question: str, text: str) -> str:
    query_tokens = set(tokenize(question))
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if not sentences:
        return text[:500]
    lower_question = question.lower()
    label_preferences = [
        ("bid deadline", ["bid deadline", "submission deadline"]),
        ("opening time", ["opening time", "bid opening"]),
        ("buyer", ["buyer:", "purchaser:", "procuring entity:"]),
        ("purchaser", ["buyer:", "purchaser:", "procuring entity:"]),
        ("payment", ["payment terms", "pay "]),
        ("acceptance", ["acceptance criteria", "site acceptance"]),
        ("dispute", ["dispute resolution", "arbitration", "mediation", "court", "jurisdiction"]),
        ("contract amount", ["contract amount", "amount:"]),
        ("delivery", ["delivery date", "delivery:"]),
        ("delivered", ["delivery date", "delivery:"]),
        ("due for delivery", ["delivery date", "delivery:"]),
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
