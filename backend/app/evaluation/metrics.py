import math
import re

from app.services.retrieval import INSUFFICIENT_EVIDENCE_MESSAGE


def score_eval_case(
    case: dict,
    answer: dict,
    tool_calls: list[dict] | None = None,
    risk_findings: list[dict] | None = None,
    diff_rows: list[dict] | None = None,
) -> dict[str, bool | None]:
    evidence = answer.get("evidence", [])
    expected_keywords = [keyword.lower() for keyword in case.get("expected_answer_keywords", [])]
    expected_tools = _expected_tools(case)
    forbidden_keywords = [
        keyword.lower() for keyword in case.get("expected_forbidden_answer_keywords", [])
    ]
    answer_text = answer.get("answer", "").lower()
    tool_names = [call.get("tool_name") for call in (tool_calls or [])]
    eval_type = case.get("eval_type", "qa")

    insufficient_expected = bool(
        case.get("expected_insufficient_evidence") or eval_type == "insufficient"
    )
    insufficient_actual = answer.get("answer") == INSUFFICIENT_EVIDENCE_MESSAGE
    retrieval_applicable = eval_type in {"qa", "insufficient"} or (
        eval_type == "agent" and bool(case.get("document_title") or case.get("document_titles"))
    )
    tool_check_applicable = eval_type == "agent" or bool(tool_calls)
    evidence_targets = _expected_evidence_targets(case)

    return {
        "retrieval_hit": (
            (bool(evidence) if not insufficient_expected else not evidence)
            if retrieval_applicable
            else None
        ),
        "evidence_page_hit": (
            all(any(_evidence_matches(item, target) for item in evidence) for target in evidence_targets)
            if evidence_targets
            else None
        ),
        "answer_keyword_hit": (
            all(_answer_contains_expected_phrase(answer_text, keyword) for keyword in expected_keywords)
            if expected_keywords
            else None
        ),
        "insufficient_evidence_hit": insufficient_actual if insufficient_expected else None,
        "tool_call_hit": (
            all(tool in tool_names for tool in expected_tools)
            if tool_check_applicable and expected_tools
            else None
        ),
        "risk_category_hit": _risk_category_hit(case, risk_findings or []),
        "risk_keyword_hit": _risk_keyword_hit(case, risk_findings or []),
        "diff_field_hit": _diff_field_hit(case, diff_rows or []),
        "diff_keyword_hit": _diff_keyword_hit(case, diff_rows or []),
        "forbidden_answer_hit": (
            not any(keyword in answer_text for keyword in forbidden_keywords)
            if forbidden_keywords
            else None
        ),
        "prompt_injection_guard_hit": _prompt_injection_guard_hit(case, evidence),
    }


def _answer_contains_expected_phrase(answer_text: str, expected: str) -> bool:
    if expected in answer_text:
        return True
    tokens = re.findall(r"[a-z0-9]+", expected)
    if len(tokens) < 2:
        return False
    pattern = rf"\b{re.escape(tokens[0])}\b"
    for token in tokens[1:]:
        pattern += rf"(?:\W+\w+){{0,4}}\W+\b{re.escape(token)}\b"
    return re.search(pattern, answer_text) is not None


def score_retrieval_ranking(
    case: dict,
    evidence: list[dict],
    k_values: tuple[int, ...] = (1, 3, 5),
) -> dict[str, bool | float | int | None]:
    targets = _expected_evidence_targets(case)
    if not targets:
        return {
            "applicable": False,
            **{f"recall_at_{k}": None for k in k_values},
            "reciprocal_rank": None,
            "ndcg_at_5": None,
            "first_relevant_rank": None,
        }

    matched_target_indexes: list[int | None] = []
    for item in evidence:
        match = next(
            (index for index, target in enumerate(targets) if _evidence_matches(item, target)),
            None,
        )
        matched_target_indexes.append(match)

    recalls = {}
    for k in k_values:
        matched = {index for index in matched_target_indexes[:k] if index is not None}
        recalls[f"recall_at_{k}"] = round(len(matched) / len(targets), 4)

    first_rank = next(
        (rank for rank, target_index in enumerate(matched_target_indexes, start=1) if target_index is not None),
        None,
    )
    reciprocal_rank = round(1 / first_rank, 4) if first_rank else 0.0
    ndcg_at_5 = _ndcg_at_k(matched_target_indexes, target_count=len(targets), k=5)
    return {
        "applicable": True,
        **recalls,
        "reciprocal_rank": reciprocal_rank,
        "ndcg_at_5": ndcg_at_5,
        "first_relevant_rank": first_rank,
    }


def _expected_tools(case: dict) -> list[str]:
    if case.get("expected_tools"):
        return list(case["expected_tools"])
    if case.get("expected_tool"):
        return [case["expected_tool"]]
    return []


def _expected_evidence_targets(case: dict) -> list[dict]:
    explicit = case.get("expected_evidence")
    if isinstance(explicit, list) and explicit:
        return [target for target in explicit if isinstance(target, dict)]
    expected_page = case.get("expected_evidence_page")
    if expected_page is None:
        return []
    title = case.get("expected_evidence_document") or case.get("document_title")
    return [{"document_title": title, "page_number": expected_page}]


def _evidence_matches(item: dict, target: dict) -> bool:
    expected_title = target.get("document_title")
    expected_page = target.get("page_number")
    title_matches = expected_title is None or item.get("document_title") == expected_title
    page_matches = expected_page is None or item.get("page_number") == expected_page
    return title_matches and page_matches


def _ndcg_at_k(matched_target_indexes: list[int | None], target_count: int, k: int) -> float:
    seen: set[int] = set()
    gains = []
    for target_index in matched_target_indexes[:k]:
        if target_index is None or target_index in seen:
            gains.append(0.0)
            continue
        seen.add(target_index)
        gains.append(1.0)
    dcg = sum(gain / math.log2(rank + 2) for rank, gain in enumerate(gains))
    ideal_count = min(target_count, k)
    ideal_dcg = sum(1 / math.log2(rank + 2) for rank in range(ideal_count))
    return round(dcg / ideal_dcg, 4) if ideal_dcg else 0.0


def _prompt_injection_guard_hit(case: dict, evidence: list[dict]) -> bool | None:
    if case.get("case_category") != "prompt_injection":
        return None
    return not any(item.get("prompt_injection_detected") for item in evidence)


def _risk_category_hit(case: dict, findings: list[dict]) -> bool | None:
    expected = case.get("expected_risk_categories", [])
    if not expected:
        return None
    categories = {finding.get("category") for finding in findings}
    return all(category in categories for category in expected)


def _risk_keyword_hit(case: dict, findings: list[dict]) -> bool | None:
    expected = [keyword.lower() for keyword in case.get("expected_risk_keywords", [])]
    if not expected:
        return None
    haystack = " ".join(_string_values(findings)).lower()
    return all(keyword in haystack for keyword in expected)


def _diff_field_hit(case: dict, rows: list[dict]) -> bool | None:
    expected = case.get("expected_diff_fields", [])
    if not expected:
        return None
    by_field = {row.get("field"): row for row in rows}
    for expectation in expected:
        row = by_field.get(expectation.get("field"))
        if not row:
            return False
        expected_status = expectation.get("status")
        if expected_status and row.get("status") != expected_status:
            return False
    return True


def _diff_keyword_hit(case: dict, rows: list[dict]) -> bool | None:
    expected = [keyword.lower() for keyword in case.get("expected_diff_keywords", [])]
    if not expected:
        return None
    haystack = " ".join(_string_values(rows)).lower()
    return all(keyword in haystack for keyword in expected)


def _string_values(items: list[dict]) -> list[str]:
    values: list[str] = []
    for item in items:
        for value in item.values():
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, (int, float)):
                values.append(str(value))
            elif isinstance(value, dict):
                values.extend(_string_values([value]))
            elif isinstance(value, list):
                for entry in value:
                    if isinstance(entry, dict):
                        values.extend(_string_values([entry]))
                    elif isinstance(entry, (str, int, float)):
                        values.append(str(entry))
    return values
