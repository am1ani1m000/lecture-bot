"""Мини-поиск без Chroma: для каждого вопроса показывает 3 ближайших куска лекции.

Запуск из корня проекта: python scripts/mini_search.py
"""
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()
MODEL_NAME = os.getenv(
    "EMBED_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

CHUNKS_FILE = Path(__file__).parent.parent / "tests" / "fixtures" / "recursion_lecture.txt"
TOP_K = 4

QUESTIONS = [
    "Почему программа ломается, если функция слишком много раз вызывает себя?",  # ответ: кусок 2
    "Сколько сравнений нужно бинарному поиску для миллиона элементов?",          # ответ: кусок 5
    "Какая сортировка не замедляется в худшем случае?",                           # ответ: кусок 7
    "Кто придумал сортировку слиянием?",                                          # ответа нет, тема та же
    "Какая погода будет завтра в Москве?",                                        # совсем не по теме
]


def load_chunks(path: Path) -> list[str]:
    """Читает файл и делит его на куски по пустым строкам."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return [part.strip() for part in text.split("\n\n") if part.strip()]

def mini_search(
    question: str,
    chunks: list[str],
    vectors: np.ndarray,
    model: SentenceTransformer,
    k: int = TOP_K,
) -> list[dict]:
    """Возвращает k самых похожих на вопрос кусков: [{"text", "number", "score"}]."""
    question_vector = model.encode([question], normalize_embeddings=True)[0]
    scores = vectors @ question_vector
    best = np.argsort(scores)[::-1][:k]
    return [
        {"text": chunks[i], "number": int(i) + 1, "score": float(scores[i])}
        for i in best
    ]

def main() -> None:
    """Загружает лекцию, считает векторы кусков и печатает результаты поиска."""
    chunks = load_chunks(CHUNKS_FILE)
    if not chunks:
        raise SystemExit(f"В файле {CHUNKS_FILE} не нашлось ни одного куска")

    model = SentenceTransformer(MODEL_NAME)
    vectors = model.encode(chunks, normalize_embeddings=True)
    print(f"Кусков в лекции: {len(chunks)}\n")

    for question in QUESTIONS:
        print(f"Вопрос: {question}")
        for found in mini_search(question, chunks, vectors, model):
            preview = found["text"][:70]
            print(f"  {found['score']:.3f}  кусок {found['number']}: {preview}...")
        print()


if __name__ == "__main__":
    main()