import re
from collections.abc import Callable

BUILT_IN_RULES = [
    {
        "name": "Payment period longer than 90 days",
        "severity": "high",
        "description": "Flags payment periods that exceed 90 days after invoice, acceptance, or delivery.",
    },
    {
        "name": "Acceptance criteria are vague or missing",
        "severity": "medium",
        "description": "Flags acceptance wording that is subjective or absent.",
    },
    {
        "name": "Liability clause only constrains one party",
        "severity": "medium",
        "description": "Flags liability wording that appears to limit only supplier or contractor liability.",
    },
    {
        "name": "Termination condition is unclear",
        "severity": "medium",
        "description": "Flags missing or vague termination rights and triggers.",
    },
    {
        "name": "Bid deadline and opening time appear inconsistent",
        "severity": "medium",
        "description": "Flags when bid deadline and opening time are both present and look inconsistent.",
    },
    {
        "name": "Qualification requirement appears overly specific",
        "severity": "low",
        "description": "Flags requirements that may be tailored to one vendor or brand.",
    },
    {
        "name": "Scoring standard is not quantified",
        "severity": "medium",
        "description": "Flags scoring language without clear numeric weights or points.",
    },
    {
        "name": "Missing dispute resolution clause",
        "severity": "high",
        "description": "Flags documents without arbitration, jurisdiction, court, mediation, or dispute wording.",
    },
]


def check_risk_rules(document_id: int, pages: list[dict]) -> list[dict]:
    full_text = "\n".join(page["text"] for page in pages)
    checks: list[Callable[[int, list[dict], str], list[dict]]] = [
        _payment_longer_than_90_days,
        _vague_acceptance,
        _one_sided_liability,
        _unclear_termination,
        _deadline_opening_inconsistent,
        _overly_specific_qualification,
        _unquantified_scoring,
        _missing_dispute_resolution,
    ]
    findings: list[dict] = []
    for check in checks:
        findings.extend(check(document_id, pages, full_text))
    return findings


def _finding(
    document_id: int,
    rule_name: str,
    severity: str,
    explanation: str,
    evidence_text: str | None,
    page_number: int | None,
) -> dict:
    return {
        "document_id": document_id,
        "rule_name": rule_name,
        "severity": severity,
        "explanation": explanation,
        "evidence_text": evidence_text,
        "page_number": page_number,
    }


def _payment_longer_than_90_days(document_id: int, pages: list[dict], full_text: str) -> list[dict]:
    del full_text
    pattern = re.compile(r"\b(9[1-9]|[1-9]\d{2,})\s+days\b", re.IGNORECASE)
    for page in pages:
        match = pattern.search(page["text"])
        if match and any(term in page["text"].lower() for term in ["payment", "pay", "invoice"]):
            days = int(match.group(1))
            return [
                _finding(
                    document_id,
                    "Payment period longer than 90 days",
                    "high",
                    f"Payment wording includes a {days}-day period, which exceeds the 90-day review threshold.",
                    _snippet_around(page["text"], match.start(), match.end()),
                    page["page_number"],
                )
            ]
    return []


def _vague_acceptance(document_id: int, pages: list[dict], full_text: str) -> list[dict]:
    vague_terms = ["satisfactory", "reasonable satisfaction", "sole discretion", "as determined"]
    if "acceptance" not in full_text.lower():
        return [
            _finding(
                document_id,
                "Acceptance criteria are vague or missing",
                "medium",
                "The document does not contain clear acceptance criteria wording.",
                None,
                None,
            )
        ]
    for page in pages:
        lower = page["text"].lower()
        if "acceptance" in lower and any(term in lower for term in vague_terms):
            return [
                _finding(
                    document_id,
                    "Acceptance criteria are vague or missing",
                    "medium",
                    "Acceptance appears to depend on subjective or undefined satisfaction wording.",
                    _line_with(page["text"], "acceptance"),
                    page["page_number"],
                )
            ]
    return []


def _one_sided_liability(document_id: int, pages: list[dict], full_text: str) -> list[dict]:
    del full_text
    for page in pages:
        lower = page["text"].lower()
        if "liability" in lower and ("supplier liability" in lower or "contractor liability" in lower):
            if "purchaser liability" not in lower and "buyer liability" not in lower:
                return [
                    _finding(
                        document_id,
                        "Liability clause only constrains one party",
                        "medium",
                        "Liability language appears to constrain only one party.",
                        _line_with(page["text"], "liability"),
                        page["page_number"],
                    )
                ]
    return []


def _unclear_termination(document_id: int, pages: list[dict], full_text: str) -> list[dict]:
    lower = full_text.lower()
    if "termination" not in lower and "terminate" not in lower:
        return [
            _finding(
                document_id,
                "Termination condition is unclear",
                "medium",
                "The document does not appear to define termination conditions.",
                None,
                None,
            )
        ]
    for page in pages:
        page_lower = page["text"].lower()
        if "termination" in page_lower and any(term in page_lower for term in ["as needed", "at any time", "without reason"]):
            return [
                _finding(
                    document_id,
                    "Termination condition is unclear",
                    "medium",
                    "Termination wording appears broad or lacks objective triggers.",
                    _line_with(page["text"], "termination"),
                    page["page_number"],
                )
            ]
    return []


def _deadline_opening_inconsistent(document_id: int, pages: list[dict], full_text: str) -> list[dict]:
    lower = full_text.lower()
    if "bid deadline" not in lower or "opening time" not in lower:
        return []
    deadline_match = re.search(r"bid deadline[:\s]+([^.。\n]+)", full_text, re.IGNORECASE)
    opening_match = re.search(r"opening time[:\s]+([^.。\n]+)", full_text, re.IGNORECASE)
    if deadline_match and opening_match and deadline_match.group(1).strip() != opening_match.group(1).strip():
        page_number = _page_for_offset(pages, deadline_match.group(0))
        return [
            _finding(
                document_id,
                "Bid deadline and opening time appear inconsistent",
                "medium",
                "Bid deadline and opening time are both present but do not match.",
                f"{deadline_match.group(0)}; {opening_match.group(0)}",
                page_number,
            )
        ]
    return []


def _overly_specific_qualification(document_id: int, pages: list[dict], full_text: str) -> list[dict]:
    del full_text
    triggers = ["specific brand", "designated manufacturer", "only vendor", "exclusive distributor"]
    for page in pages:
        lower = page["text"].lower()
        if any(trigger in lower for trigger in triggers):
            return [
                _finding(
                    document_id,
                    "Qualification requirement appears overly specific",
                    "low",
                    "Qualification wording may be overly tailored to a vendor, brand, or channel.",
                    _line_with(page["text"], triggers[0]) if triggers[0] in lower else page["text"][:300],
                    page["page_number"],
                )
            ]
    return []


def _unquantified_scoring(document_id: int, pages: list[dict], full_text: str) -> list[dict]:
    lower = full_text.lower()
    if "scoring" not in lower and "evaluation criteria" not in lower:
        return []
    if not re.search(r"\b\d{1,3}\s*(points|marks|%)\b", lower):
        page = next((p for p in pages if "scoring" in p["text"].lower() or "evaluation criteria" in p["text"].lower()), pages[0])
        return [
            _finding(
                document_id,
                "Scoring standard is not quantified",
                "medium",
                "Evaluation or scoring wording appears without numeric weights, points, or percentages.",
                page["text"][:300],
                page["page_number"],
            )
        ]
    return []


def _missing_dispute_resolution(document_id: int, pages: list[dict], full_text: str) -> list[dict]:
    del pages
    lower = full_text.lower()
    has_dispute_clause = any(
        term in lower for term in ["dispute", "arbitration", "court", "jurisdiction", "mediation"]
    )
    if has_dispute_clause:
        return []
    return [
        _finding(
            document_id,
            "Missing dispute resolution clause",
            "high",
            "The document does not contain enough evidence of a dispute resolution mechanism.",
            None,
            None,
        )
    ]


def _snippet_around(text: str, start: int, end: int, radius: int = 120) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)].strip()


def _line_with(text: str, keyword: str) -> str:
    for line in re.split(r"[\n.。]", text):
        if keyword.lower() in line.lower():
            return line.strip()
    return text[:300]


def _page_for_offset(pages: list[dict], phrase: str) -> int | None:
    for page in pages:
        if phrase in page["text"]:
            return page["page_number"]
    return None
