import fitz


def extract_pdf_pages(pdf_bytes: bytes) -> list[dict]:
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError("The uploaded file could not be parsed as a PDF.") from exc

    pages: list[dict] = []
    try:
        for index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            pages.append({"page_number": index, "text": text})
    finally:
        document.close()
    if not pages:
        raise ValueError("The PDF does not contain readable pages.")
    return pages
