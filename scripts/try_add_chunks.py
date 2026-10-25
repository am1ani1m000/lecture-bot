"""Ручная проверка add_chunks на настоящей модели эмбеддингов."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentence_transformers import SentenceTransformer

import llm
import search

model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
llm.embed = lambda texts: model.encode(texts).tolist()

chunks = [
    {"text": "Рекурсия — это вызов функции самой себя.",
     "source": "test.pdf", "page": 1, "chunk_id": "0"},
    {"text": "Базовый случай останавливает рекурсию.",
     "source": "test.pdf", "page": 1, "chunk_id": "1"},
    {"text": "Стек вызовов хранит незавершённые функции.",
     "source": "test.pdf", "page": 2, "chunk_id": "2"},
]

search.add_chunks(chunks, user_id=999, doc_id=1)
search.add_chunks(chunks, user_id=999, doc_id=1)  # повтор: дублей быть не должно

collection = search._get_collection(999)
print("Записей:", collection.count())
print(collection.get(ids=["1_2_2"]))