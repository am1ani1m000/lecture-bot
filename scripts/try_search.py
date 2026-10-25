"""Ручная проверка search на настоящей модели эмбеддингов."""
from sentence_transformers import SentenceTransformer

import llm
import search

model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
llm.embed = lambda texts: model.encode(texts).tolist()

lecture_1 = [
    {"text": "Рекурсия — это вызов функции самой себя.", "source": "recursion.pdf", "page": 1, "chunk_id": "0"},
    {"text": "Базовый случай останавливает рекурсию.", "source": "recursion.pdf", "page": 1, "chunk_id": "1"},
    {"text": "Стек вызовов хранит незавершённые функции.", "source": "recursion.pdf", "page": 2, "chunk_id": "2"},
]
lecture_2 = [
    {"text": "Быстрая сортировка выбирает опорный элемент.", "source": "sort.pdf", "page": 1, "chunk_id": "0"},
]

search.add_chunks(lecture_1, user_id=999, doc_id=1)
search.add_chunks(lecture_2, user_id=999, doc_id=2)

for question, doc_id in [
    ("Что останавливает рекурсию?", None),
    ("Как работает быстрая сортировка?", None),
    ("Как работает быстрая сортировка?", 1),
]:
    print(f"\nВопрос: {question} | doc_id={doc_id}")
    for r in search.search(question, user_id=999, k=2, doc_id=doc_id):
        print(f"  {r['score']}  {r['source']} стр.{r['page']}  {r['text']}")

print("\nЧужой пользователь:", search.search("рекурсия", user_id=1000))