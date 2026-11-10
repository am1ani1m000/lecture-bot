import hashlib
import os
from pypdf import PdfReader


def load_pdf(path: str) -> list[dict]:
    """Читает PDF и возвращает страницы с текстом.

    Каждая страница: {"text": str, "source": str, "page": int}.
    source это имя файла, page нумеруется с 1. Пустые страницы пропускаются.
    """
    reader = PdfReader(path)
    source = os.path.basename(path)
    result = []
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            result.append({"text": text, "source": source, "page": number})
    return result



def count_pages(path: str) -> int:
    """Сколько всего страниц в PDF, включая страницы без текста."""
    return len(PdfReader(path).pages)


def skipped_pages(pages: list[dict], total: int) -> list[int]:
    """Номера страниц без текста: их нет в результате load_pdf."""
    have = {p["page"] for p in pages}
    return [n for n in range(1, total + 1) if n not in have]


def _cut_end(text: str, start: int, size: int, overlap: int) -> int:
    """Конец куска: последний пробел перед start + size, чтобы не резать слово."""
    end = start + size
    if end >= len(text):
        return len(text)
    space = text.rfind(" ", start + overlap + 1, end + 1)
    return space if space != -1 else end


def _next_start(text: str, end: int, overlap: int) -> int:
    """Начало следующего куска: отступаем на overlap и встаём на начало слова."""
    start = end - overlap
    if start == 0 or text[start - 1] == " ":
        return start
    space = text.find(" ", start, end)
    return space + 1 if space != -1 else start




def chunk_pages(pages: list[dict], size: int = 800, overlap: int = 100) -> list[dict]:
    """Режет текст страниц на куски с перекрытием, не разрезая слова.

    Кусок не пересекает границу страницы, поэтому источник всегда точный.
    Слово режется только если оно длиннее куска.
    """
    if not 0 <= overlap < size:
        raise ValueError("overlap должен быть от 0 и меньше size")
    chunks = []
    for page in pages:
        text = page["text"]
        start = 0
        while start < len(text):
            end = _cut_end(text, start, size, overlap)
            piece = text[start:end].strip()
            if piece:
                chunks.append({
                    "text": piece,
                    "source": page["source"],
                    "page": page["page"],
                    "chunk_id": str(len(chunks)),
                })
            if end >= len(text):
                break
            start = _next_start(text, end, overlap)
    return chunks


def file_hash(path: str) -> str:
    """SHA-256 содержимого файла: одинаковые файлы дают одинаковый хэш."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()
