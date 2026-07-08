def chunk_pages(
    document_id: int,
    pages: list[dict],
    chunk_size: int = 180,
    overlap: int = 35,
) -> list[dict]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be zero or lower than chunk_size")

    chunks: list[dict] = []
    chunk_index = 0
    for page in pages:
        words = page["text"].split()
        if not words:
            continue
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            text = " ".join(words[start:end]).strip()
            if text:
                chunks.append(
                    {
                        "document_id": document_id,
                        "chunk_index": chunk_index,
                        "page_number": page["page_number"],
                        "text": text,
                        "token_count": len(text.split()),
                    }
                )
                chunk_index += 1
            if end == len(words):
                break
            start = end - overlap
    return chunks
