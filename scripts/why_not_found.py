"""Почему бот не нашёл ответ: текст страницы, токены кусков, что находит поиск."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import llm
import search
from documents import chunk_pages, load_pdf

pdf, page, user_id, question = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]

# 1. Что pypdf достал со страницы
pages = [p for p in load_pdf(pdf) if p["page"] == page]
print("=== Текст страницы (начало):")
print(pages[0]["text"][:500] if pages else "ТЕКСТА НЕТ")

# 2. Сколько токенов в каждом куске этой страницы
model = llm._get_embed_model()
print(f"\n=== Модель читает максимум {model.max_seq_length} токенов")
for c in chunk_pages(pages):
    n = len(model.tokenizer(c["text"])["input_ids"])
    print(f"кусок {c['chunk_id']}: {len(c['text'])} символов, {n} токенов")

# 3. Что находит поиск среди всех лекций
print("\n=== Первые 10 результатов поиска:")
name = Path(pdf).name
for i, r in enumerate(search.search(question, user_id, k=10), start=1):
    mark = "  <-- НУЖНАЯ" if r["source"] == name and r["page"] == page else ""
    print(f"{i}. {r['score']}  {r['source']} стр.{r['page']}{mark}")