"""Проверяет, что PDF читается и режется на куски (в базу ничего не пишет)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from documents import chunk_pages, load_pdf

path = sys.argv[1]
pages = load_pdf(path)
chunks = chunk_pages(pages)
chars = sum(len(p["text"]) for p in pages)

print(f"Страниц: {len(pages)}, символов: {chars}, кусков: {len(chunks)}")
print(pages[0]["text"][:300] if pages else "Страниц нет")