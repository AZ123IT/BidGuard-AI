import re

FIELD_NAMES = [
    "project_name",
    "buyer",
    "supplier",
    "bid_deadline",
    "opening_time",
    "contract_amount",
    "payment_terms",
    "delivery_date",
    "acceptance_criteria",
    "liability_clause",
    "dispute_resolution_clause",
]

PATTERNS = {
    "project_name": [r"project name[:\s]+([^\n.。]+)", r"project[:\s]+([^\n.。]+)"],
    "buyer": [r"buyer[:\s]+([^\n.。]+)", r"purchaser[:\s]+([^\n.。]+)"],
    "supplier": [r"supplier[:\s]+([^\n.。]+)", r"contractor[:\s]+([^\n.。]+)"],
    "bid_deadline": [r"bid deadline[:\s]+([^\n.。]+)", r"submission deadline[:\s]+([^\n.。]+)"],
    "opening_time": [r"opening time[:\s]+([^\n.。]+)", r"bid opening[:\s]+([^\n.。]+)"],
    "contract_amount": [r"contract amount[:\s]+([^\n.。]+)", r"amount[:\s]+(\$?[0-9][^\n.。]+)"],
    "payment_terms": [r"payment terms?[:\s]+([^\n.。]+)", r"(?:pay|payment)[^\n.。]{0,80}\b\d+\s+days\b[^\n.。]*"],
    "delivery_date": [r"delivery date[:\s]+([^\n.。]+)", r"delivery[:\s]+([^\n.。]+)"],
    "acceptance_criteria": [r"acceptance criteria[:\s]+([^\n.。]+)", r"acceptance[^\n.。]{0,180}"],
    "liability_clause": [r"liability[^\n.。]{0,220}"],
    "dispute_resolution_clause": [r"dispute resolution[:\s]+([^\n.。]+)", r"(?:arbitration|jurisdiction|mediation|court)[^\n.。]{0,180}"],
}


def extract_fields(pages: list[dict]) -> dict[str, dict]:
    extracted: dict[str, dict] = {}
    for field_name in FIELD_NAMES:
        extracted[field_name] = {
            "value": None,
            "page_number": None,
            "confidence": 0.0,
            "evidence_text": None,
        }
        for pattern in PATTERNS[field_name]:
            found = _find_first(pattern, pages)
            if found:
                value, page_number, evidence_text = found
                extracted[field_name] = {
                    "value": _clean_value(value),
                    "page_number": page_number,
                    "confidence": 0.65 if ":" in evidence_text else 0.45,
                    "evidence_text": evidence_text,
                }
                break
    return extracted


def _find_first(pattern: str, pages: list[dict]) -> tuple[str, int, str] | None:
    compiled = re.compile(pattern, re.IGNORECASE)
    for page in pages:
        match = compiled.search(page["text"])
        if match:
            value = match.group(1) if match.groups() else match.group(0)
            evidence = match.group(0).strip()
            return value, page["page_number"], evidence
    return None


def _clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" :-\t\n\r"))
