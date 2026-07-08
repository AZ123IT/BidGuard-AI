from app.services.retrieval import INSUFFICIENT_EVIDENCE_MESSAGE


def score_eval_case(
    case: dict,
    answer: dict,
    tool_calls: list[dict] | None = None,
    risk_findings: list[dict] | None = None,
    diff_rows: list[dict] | None = None,
) -> dict[str, bool]:
    evidence = answer.get("evidence", [])
    expected_page = case.get("expected_evidence_page")
    expected_keywords = [keyword.lower() for keyword in case.get("expected_answer_keywords", [])]
    expected_tools = _expected_tools(case)
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

    return {
        "retrieval_hit": (
            (bool(evidence) if not insufficient_expected else not evidence)
            if retrieval_applicable
            else True
        ),
        "evidence_page_hit": (
            any(item.get("page_number") == expected_page for item in evidence)
            if expected_page is not None
            else True
        ),
        "answer_keyword_hit": (
            all(keyword in answer_text for keyword in expected_keywords)
            if expected_keywords
            else True
        ),
        "insufficient_evidence_hit": insufficient_actual if insufficient_expected else True,
        "tool_call_hit": (
            all(tool in tool_names for tool in expected_tools)
            if tool_check_applicable and expected_tools
            else True
        ),
        "risk_category_hit": _risk_category_hit(case, risk_findings or []),
        "risk_keyword_hit": _risk_keyword_hit(case, risk_findings or []),
        "diff_field_hit": _diff_field_hit(case, diff_rows or []),
        "diff_keyword_hit": _diff_keyword_hit(case, diff_rows or []),
    }


def _expected_tools(case: dict) -> list[str]:
    if case.get("expected_tools"):
        return list(case["expected_tools"])
    if case.get("expected_tool"):
        return [case["expected_tool"]]
    return []


def _risk_category_hit(case: dict, findings: list[dict]) -> bool:
    expected = case.get("expected_risk_categories", [])
    if not expected:
        return True
    categories = {finding.get("category") for finding in findings}
    return all(category in categories for category in expected)


def _risk_keyword_hit(case: dict, findings: list[dict]) -> bool:
    expected = [keyword.lower() for keyword in case.get("expected_risk_keywords", [])]
    if not expected:
        return True
    haystack = " ".join(_string_values(findings)).lower()
    return all(keyword in haystack for keyword in expected)


def _diff_field_hit(case: dict, rows: list[dict]) -> bool:
    expected = case.get("expected_diff_fields", [])
    if not expected:
        return True
    by_field = {row.get("field"): row for row in rows}
    for expectation in expected:
        row = by_field.get(expectation.get("field"))
        if not row:
            return False
        expected_status = expectation.get("status")
        if expected_status and row.get("status") != expected_status:
            return False
    return True


def _diff_keyword_hit(case: dict, rows: list[dict]) -> bool:
    expected = [keyword.lower() for keyword in case.get("expected_diff_keywords", [])]
    if not expected:
        return True
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
