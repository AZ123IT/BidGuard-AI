from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_docx_pages(docx_bytes: bytes) -> list[dict]:
    try:
        with ZipFile(BytesIO(docx_bytes)) as archive:
            document_xml = archive.read("word/document.xml")
    except (BadZipFile, KeyError) as exc:
        raise ValueError("The uploaded file could not be parsed as a DOCX document.") from exc

    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as exc:
        raise ValueError("The DOCX document XML could not be parsed.") from exc

    paragraphs: list[str] = []
    for paragraph in root.iter(f"{WORD_NAMESPACE}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{WORD_NAMESPACE}t")).strip()
        if text:
            paragraphs.append(text)

    if not paragraphs:
        raise ValueError("The DOCX document does not contain readable text.")
    return [{"page_number": 1, "text": "\n".join(paragraphs)}]
