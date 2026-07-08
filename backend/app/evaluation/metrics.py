from app.services.retrieval import INSUFFICIENT_EVIDENCE_MESSAGE


def score_eval_case(case: dict, answer: dict, tool_calls: list[dict] | None = None) -> dict:
    evidence = answer.get("evidence", [])
    expected_page = case.get("expected_evidence_page")
    expected_keywords = [keyword.lower() for keyword in case.get("expected_answer_keywords", [])]
    expected_tools = case.get("expected_tools", [])
    answer_text = answer.get("answer", "").lower()
    tool_names = [call.get("tool_name") for call in (tool_calls or [])]

    insufficient_expected = case.get("eval_type") == "insufficient"
    insufficient_actual = answer.get("answer") == INSUFFICIENT_EVIDENCE_MESSAGE

    return {
        "retrieval_hit": bool(evidence) if not insufficient_expected else not evidence,
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
        "tool_call_hit": all(tool in tool_names for tool in expected_tools) if expected_tools else True,
    }
