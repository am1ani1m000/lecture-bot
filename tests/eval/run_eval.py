"""Полный прогон eval без Telegram.

Для каждого вопроса из tests/eval/questions.csv делает то же, что answer_question в bot.py:
search.search -> фильтр MIN_SCORE -> llm.ask(..., "answer") -> строка источников.
Пишет tests/eval/results_ГГГГ-ММ-ДД.csv.

Запуск из корня репозитория:
    python tests/eval/run_eval.py 864120961
    python tests/eval/run_eval.py 864120961 --own-doc --limit 5
"""
import argparse
import csv
import logging
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import config  
import db  
import llm  
import search  

EVAL_DIR = ROOT / "tests" / "eval"
QUESTIONS = EVAL_DIR / "questions.csv"
REFUSALS = ("ответа не нашёл", "ответа не нашел", "не вижу в лекции")
MIN_SCORE = getattr(config, "MIN_SCORE", None)
PAUSE_SEC = 3  # лимит бесплатной модели около 20 запросов в минуту

log = logging.getLogger("run_eval")


def doc_ids_by_name(user_id: int) -> dict[str, int]:
    """Имя файла лекции -> doc_id (для --own-doc)."""
    return {d["filename"]: d["doc_id"] for d in db.list_documents(user_id)}


def find_chunks(question: str, user_id: int, doc_id: int | None) -> list[dict]:
    """Поиск кусков с тем же фильтром, что в боте."""
    chunks = search.search(question, user_id, config.TOP_K, doc_id=doc_id)
    if MIN_SCORE is not None:
        chunks = [c for c in chunks if c["score"] >= MIN_SCORE]
    return chunks


def sources_line(chunks: list[dict]) -> str:
    """Строка «файл, стр. N; ...» без повторов, в порядке поиска."""
    seen = []
    for c in chunks:
        item = f"{c['source']}, стр. {c['page']}"
        if item not in seen:
            seen.append(item)
    return "; ".join(seen)


def is_refusal(answer: str) -> bool:
    return any(p in answer.lower() for p in REFUSALS)


def auto_verdict(row: dict, answer: str, chunks: list[dict]) -> tuple[str, str]:
    """Очевидные вердикты. Остальное пусто, с подсказкой для ручной проверки."""
    answerable = row["answerable"].strip().lower() == "yes"
    if is_refusal(answer):
        return ("неверно", "отказ, хотя ответ есть") if answerable else ("верно", "честный отказ")
    if not answerable:
        return "", "ответил на вопрос без ответа: проверить, не выдумал ли"
    if row["doc"] not in {c["source"] for c in chunks}:
        return "неверный источник", "нужной лекции нет в источниках"
    return "", f"сверить с эталоном, ждём стр. {row['expected_page']}"


def run_one(row: dict, user_id: int, doc_id: int | None) -> dict:
    """Один вопрос. Ошибка модели не роняет прогон."""
    try:
        chunks = find_chunks(row["question"], user_id, doc_id)
        if not chunks:
            answer = "В материалах ответа не нашёл"
        else:
            answer = llm.ask(row["question"], chunks, "answer")
        verdict, comment = auto_verdict(row, answer, chunks)
        sources = sources_line(chunks)
    except Exception as e:  # noqa: BLE001
        log.exception("Вопрос %s упал", row["id"])
        answer, sources, verdict, comment = "", "", "", f"ошибка: {type(e).__name__}: {e}"
    return {**row, "bot_answer": answer, "sources": sources, "verdict": verdict, "comment": comment}


def main() -> None:
    p = argparse.ArgumentParser(description="Прогон eval без Telegram")
    p.add_argument("user_id", type=int)
    p.add_argument("--own-doc", action="store_true", help="искать только в лекции из колонки doc")
    p.add_argument("--limit", type=int, default=None, help="прогнать только первые N вопросов")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    with open(QUESTIONS, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))[: args.limit]
    names = doc_ids_by_name(args.user_id) if args.own_doc else {}

    meta = {
        "model": config.LLM_MODEL,
        "chunk_size": config.CHUNK_SIZE,
        "top_k": config.TOP_K,
        "search": "own_doc" if args.own_doc else "all_docs",
        "date": date.today().isoformat(),
    }
    results = []
    for i, row in enumerate(rows, 1):
        doc_id = names.get(row["doc"]) if args.own_doc else None
        if args.own_doc and doc_id is None:
            log.warning("Лекция %s не найдена у пользователя, ищу по всем", row["doc"])
        log.info("[%d/%d] вопрос %s", i, len(rows), row["id"])
        results.append({**run_one(row, args.user_id, doc_id), **meta})
        if i < len(rows):
            time.sleep(PAUSE_SEC)

    out = EVAL_DIR / f"results_{meta['date']}.csv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)

    done = [r for r in results if r["verdict"]]
    print(f"Готово: {out}")
    print(f"Автовердиктов: {len(done)} из {len(results)}, верно: "
          f"{sum(r['verdict'] == 'верно' for r in done)}, ошибок: "
          f"{sum(r['comment'].startswith('ошибка') for r in results)}")


if __name__ == "__main__":
    main()