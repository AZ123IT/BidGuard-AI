from app.models import Document

DISCLAIMER = "This report is evidence-first engineering output and is not professional legal advice."


def generate_review_report(document: Document) -> dict:
    findings = sorted(
        document.risk_findings,
        key=lambda finding: (finding.severity != "high", finding.severity != "medium", finding.rule_name),
    )
    fields = sorted(document.extracted_fields, key=lambda field: field.field_name)
    chunks = sorted(document.chunks, key=lambda chunk: (chunk.page_number, chunk.chunk_index))

    lines = [
        "# BidGuard AI Review Report",
        "",
        f"Document: {document.title}",
        f"File: {document.filename}",
        f"Pages: {document.page_count}",
        f"Chunks: {len(chunks)}",
        "",
        "## Important Boundary",
        "",
        DISCLAIMER,
        "",
        "## Extracted Fields",
        "",
    ]

    if fields:
        for field in fields:
            value = field.value or "Not found"
            page = f"page {field.page_number}" if field.page_number else "no page"
            lines.append(f"- {field.field_name.replace('_', ' ').title()}: {value} ({page}, confidence {field.confidence:.2f})")
    else:
        lines.append("- No extracted fields were stored.")

    lines.extend(["", "## Risk Findings", ""])
    if findings:
        for finding in findings:
            page = f"page {finding.page_number}" if finding.page_number else "no page"
            lines.extend(
                [
                    f"### {finding.rule_name}",
                    "",
                    f"- Category: {finding.category}",
                    f"- Severity: {finding.severity}",
                    f"- Evidence location: {page}",
                    f"- Explanation: {finding.explanation}",
                ]
            )
            if finding.evidence_text:
                lines.extend(["", f"> {finding.evidence_text}"])
            lines.append("")
    else:
        lines.append("- No risk findings have been recorded for this document.")

    lines.extend(["## Evidence Chunk Index", ""])
    if chunks:
        for chunk in chunks[:20]:
            snippet = " ".join(chunk.text.split())[:220]
            lines.append(f"- Page {chunk.page_number}, chunk {chunk.id}: {snippet}")
    else:
        lines.append("- No chunks are available.")

    content = "\n".join(lines).strip() + "\n"
    return {
        "document_id": document.id,
        "document_title": document.title,
        "format": "markdown",
        "content": content,
    }
