from app.services.chunking import chunk_pages
from app.services.diff import compare_extracted_fields
from app.services.field_extractor import extract_fields
from app.services.retrieval import (
    INSUFFICIENT_EVIDENCE_MESSAGE,
    build_evidence_answer,
    retrieve_relevant_chunks,
)
from app.services.risk_rules import check_risk_rules


def test_chunk_pages_preserves_page_numbers_and_chunks_text():
    pages = [
        {
            "page_number": 1,
            "text": "Payment terms are net 120 days after invoice. Acceptance criteria are subject to buyer satisfaction.",
        }
    ]

    chunks = chunk_pages(document_id=7, pages=pages, chunk_size=8, overlap=2)

    assert len(chunks) >= 2
    assert chunks[0]["document_id"] == 7
    assert chunks[0]["page_number"] == 1
    assert "Payment terms" in chunks[0]["text"]
    assert chunks[1]["text"].startswith("after invoice")


def test_retrieval_returns_ranked_page_level_evidence():
    chunks = [
        {"id": 1, "document_id": 2, "document_title": "Tender A", "page_number": 3, "text": "The bid deadline is 30 July 2026 at 17:00.", "chunk_index": 0},
        {"id": 2, "document_id": 2, "document_title": "Tender A", "page_number": 4, "text": "Warranty service must be available for two years.", "chunk_index": 1},
    ]

    results = retrieve_relevant_chunks("What is the bid deadline?", chunks, limit=2)

    assert results[0]["page_number"] == 3
    assert results[0]["score"] > results[1]["score"]
    assert results[0]["document_title"] == "Tender A"


def test_evidence_answer_refuses_when_no_relevant_evidence():
    response = build_evidence_answer("What is the liability cap?", [])

    assert response["answer"] == INSUFFICIENT_EVIDENCE_MESSAGE
    assert response["evidence"] == []


def test_evidence_answer_refuses_partial_keyword_match_for_missing_identifier():
    response = build_evidence_answer(
        "What is the vendor tax ID?",
        [
            {
                "document_title": "Contract",
                "page_number": 1,
                "text": "Vendor: BrightGrid Pty Ltd. Payment terms: Net 45 days.",
                "score": 0.2,
                "keyword_score": 0.3333,
                "keyword_coverage": 0.3333,
                "has_keyword_match": True,
            }
        ],
    )

    assert response["answer"] == INSUFFICIENT_EVIDENCE_MESSAGE
    assert response["evidence"] == []


def test_domain_phrase_match_allows_contract_synonyms_without_overmatching_identifier():
    chunks = [
        {
            "id": 1,
            "document_id": 2,
            "document_title": "Tender A",
            "page_number": 1,
            "text": "Payment terms: The purchaser shall pay the supplier within 45 days after receiving a valid invoice.",
            "chunk_index": 0,
        },
        {
            "id": 2,
            "document_id": 2,
            "document_title": "Tender A",
            "page_number": 1,
            "text": "Vendor: BrightGrid Pty Ltd.",
            "chunk_index": 1,
        },
    ]

    payment_results = retrieve_relevant_chunks("What payment period does the tender specify?", chunks)
    payment_answer = build_evidence_answer("What payment period does the tender specify?", payment_results)

    assert payment_results[0]["phrase_match"] is True
    assert "45 days" in payment_answer["answer"]

    tax_results = retrieve_relevant_chunks("What is the vendor tax ID?", chunks)
    tax_answer = build_evidence_answer("What is the vendor tax ID?", tax_results)

    assert tax_answer["answer"] == INSUFFICIENT_EVIDENCE_MESSAGE


def test_evidence_answer_prefers_clause_sentence_matching_question():
    response = build_evidence_answer(
        "What is the bid deadline for the Harbor Solar Microgrid Upgrade?",
        [
            {
                "document_title": "Demo Tender",
                "page_number": 1,
                "text": "Project name: Harbor Solar Microgrid Upgrade. Bid deadline: 20 August 2026 at 17:00. Payment terms: 45 days after invoice.",
                "score": 0.9,
            }
        ],
    )

    assert "Bid deadline: 20 August 2026 at 17:00" in response["answer"]


def test_risk_rules_find_payment_and_missing_dispute_resolution_evidence():
    pages = [
        {
            "page_number": 2,
            "text": "The purchaser shall pay the supplier within 120 days after receiving a valid invoice. Acceptance will be determined as satisfactory by the purchaser.",
        }
    ]

    findings = check_risk_rules(document_id=5, pages=pages)
    rule_names = {finding["rule_name"] for finding in findings}

    assert "Payment period longer than 90 days" in rule_names
    assert "Missing dispute resolution clause" in rule_names
    payment = next(f for f in findings if f["rule_name"] == "Payment period longer than 90 days")
    assert payment["severity"] == "high"
    assert payment["page_number"] == 2
    assert "120 days" in payment["evidence_text"]


def test_compare_extracted_fields_marks_changed_and_uncertain_values():
    left = {
        "project_name": {"value": "Bridge Upgrade", "page_number": 1, "confidence": 0.8},
        "payment_terms": {"value": "90 days", "page_number": 5, "confidence": 0.7},
    }
    right = {
        "project_name": {"value": "Bridge Upgrade", "page_number": 1, "confidence": 0.8},
        "payment_terms": {"value": "120 days", "page_number": 6, "confidence": 0.6},
        "liability_clause": {"value": None, "page_number": None, "confidence": 0.0},
    }

    rows = compare_extracted_fields(left, right)
    payment = next(row for row in rows if row["field"] == "payment_terms")
    liability = next(row for row in rows if row["field"] == "liability_clause")

    assert payment["status"] == "changed"
    assert payment["document_a_value"] == "90 days"
    assert payment["document_b_value"] == "120 days"
    assert liability["status"] == "uncertain"


def test_field_extractor_handles_common_contract_synonyms():
    pages = [
        {
            "page_number": 1,
            "text": (
                "Project Title: Solar Microgrid Upgrade\n"
                "Procuring Entity: City Energy Department\n"
                "Vendor: BrightGrid Pty Ltd\n"
                "Closing date: 20 August 2026 at 17:00\n"
                "Tender opening: 20 August 2026 at 17:30\n"
                "Total contract value: AUD 1,250,000\n"
                "Net 45 days after invoice approval.\n"
                "Completion date: 30 November 2026.\n"
                "Acceptance: commissioning certificate and safety test pass.\n"
                "Liability cap: supplier liability is capped at the contract amount.\n"
                "Governing law and dispute forum: courts of New South Wales."
            ),
        }
    ]

    fields = extract_fields(pages)

    assert fields["project_name"]["value"] == "Solar Microgrid Upgrade"
    assert fields["buyer"]["value"] == "City Energy Department"
    assert fields["supplier"]["value"] == "BrightGrid Pty Ltd"
    assert fields["bid_deadline"]["value"] == "20 August 2026 at 17:00"
    assert fields["opening_time"]["value"] == "20 August 2026 at 17:30"
    assert fields["contract_amount"]["value"] == "AUD 1,250,000"
    assert "45 days" in fields["payment_terms"]["value"]
    assert fields["delivery_date"]["value"] == "30 November 2026"
    assert "commissioning certificate" in fields["acceptance_criteria"]["value"]
    assert "supplier liability" in fields["liability_clause"]["value"].lower()
    assert "New South Wales" in fields["dispute_resolution_clause"]["value"]
