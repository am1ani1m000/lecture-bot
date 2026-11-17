"""Проверка поиска без модели: на каком месте нужная страница для каждого вопроса.

Запуск: python scripts/eval_search.py USER_ID
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db
import search

K = 10  # сколько результатов поиска смотрим
QUESTIONS = Path(__file__).resolve().parent.parent / "tests" / "eval" / "questions.csv"


def parse_pages(text: str) -> set[int]:
    """'5-7' -> {5, 6, 7}, '11;14' -> {11, 14}."""
    pages = set()
    for part in text.split(";"):
        if "-" in part:
            a, b = part.split("-")
            pages.update(range(int(a), int(b) + 1))
        else:
            pages.add(int(part))
    return pages


def find_rank(results: list[dict], source: str, pages: set[int]) -> int | None:
    """Место (с 1) первого куска из нужного файла с нужной страницы, иначе None."""
    for i, r in enumerate(results, start=1):
        if r["source"] == source and r["page"] in pages:
            return i
    return None

def main() -> None:
    user_id = int(sys.argv[1])
    doc_ids = {d["filename"]: d["doc_id"] for d in db.list_documents(user_id)}
    with open(QUESTIONS, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["answerable"] == "yes"]

    hits = {"все лекции, топ-4": 0, "все лекции, топ-10": 0,
            "своя лекция, топ-4": 0, "своя лекция, топ-10": 0}
    print("id | все лекции | своя лекция | вопрос")
    for row in rows:
        source = row["doc"] + ".pdf"
        if source not in doc_ids:
            print(f"{row['id']} | файла {source} нет в базе")
            continue
        pages = parse_pages(row["expected_page"])
        q = row["question"]
        rank_all = find_rank(search.search(q, user_id, k=K), source, pages)
        rank_doc = find_rank(search.search(q, user_id, k=K, doc_id=doc_ids[source]), source, pages)
        for name, rank in [("все лекции", rank_all), ("своя лекция", rank_doc)]:
            if rank and rank <= 4:
                hits[f"{name}, топ-4"] += 1
            if rank:
                hits[f"{name}, топ-10"] += 1
        print(f"{row['id']} | {rank_all or '-'} | {rank_doc or '-'} | {q[:50]}")

    n = len(rows)
    print(f"\nВопросов: {n}")
    for name, count in hits.items():
        print(f"{name}: {count} из {n} ({count * 100 // n}%)")


if __name__ == "__main__":
    main()