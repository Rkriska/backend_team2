"""
Text chunking service.
- Narrative docs (TOR): chunk by paragraph
- Policy/regulation (ACUAN, KEPMEN): chunk by pasal (article)
"""
import re
from app.core.constants import DocType, ChunkType


def chunk_document(text: str, doc_type: DocType) -> list[dict]:
    """
    Returns list of:
    {content, chunk_index, chunk_type, pasal_number, page_number}
    """
    if doc_type in (DocType.ACUAN, DocType.KEPMEN):
        return _chunk_by_pasal(text)
    else:
        return _chunk_by_paragraph(text)


def _chunk_by_paragraph(text: str, min_chars: int = 100) -> list[dict]:
    """Split on double newlines, merge short paragraphs."""
    # Extract page markers
    page_map = {}
    current_page = 1
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        m = re.match(r"\[PAGE (\d+)\]", line)
        if m:
            current_page = int(m.group(1))
        else:
            page_map[len(cleaned_lines)] = current_page
            cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines)
    raw_chunks = re.split(r"\n{2,}", cleaned_text)

    chunks = []
    buffer = ""
    for part in raw_chunks:
        part = part.strip()
        if not part:
            continue
        buffer = (buffer + "\n\n" + part).strip() if buffer else part
        if len(buffer) >= min_chars:
            chunks.append(buffer)
            buffer = ""
    if buffer:
        chunks.append(buffer)

    return [
        {
            "content": c,
            "chunk_index": i,
            "chunk_type": ChunkType.PARAGRAF,
            "pasal_number": None,
            "page_number": None,
        }
        for i, c in enumerate(chunks)
    ]


def _chunk_by_pasal(text: str) -> list[dict]:
    """Split by 'Pasal X' markers."""
    pattern = r"(Pasal\s+\d+[a-zA-Z]?)"
    parts = re.split(pattern, text, flags=re.IGNORECASE)

    chunks = []
    idx = 0
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if re.match(r"Pasal\s+\d+", part, re.IGNORECASE):
            pasal_num = part
            content = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if content:
                chunks.append({
                    "content": f"{pasal_num}\n{content}",
                    "chunk_index": idx,
                    "chunk_type": ChunkType.PASAL,
                    "pasal_number": pasal_num,
                    "page_number": None,
                })
                idx += 1
            i += 2
        else:
            if part and idx == 0:
                # preamble before first pasal
                chunks.append({
                    "content": part,
                    "chunk_index": idx,
                    "chunk_type": ChunkType.PARAGRAF,
                    "pasal_number": None,
                    "page_number": None,
                })
                idx += 1
            i += 1

    return chunks
