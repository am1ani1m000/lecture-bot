import os
from pypdf import PdfReader


def load_pdf(path):
    reader = PdfReader(path)
    source = os.path.basename(path)
    result = []
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            result.append({"text": text, "source": source, "page": number})
    return result

def chunk_pages(pages: list[dict], size: int = 800, overlap: int = 100) -> list[dict]:
    """Режет текст страниц на куски с перекрытием.

    Кусок не пересекает границу страницы, поэтому источник всегда точный.
    """
    if not 0 <= overlap < size:
        raise ValueError("overlap должен быть от 0 и меньше size")
    step = size - overlap
    chunks = []
    for page in pages:
        text = page["text"]
        for start in range(0, len(text), step):
            piece = text[start:start + size].strip()
            if piece:
                chunks.append({
                    "text": piece,
                    "source": page["source"],
                    "page": page["page"],
                    "chunk_id": str(len(chunks)),
                })
            if start + size >= len(text):
                break
    return chunks
