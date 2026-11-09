"""Замер /summary на длинной лекции (#68).
Запуск: python scripts/measure_summary.py путь.pdf [--no-reasoning]"""
import functools
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import llm
from documents import chunk_pages, load_pdf

logging.basicConfig(level=logging.INFO)

if "--no-reasoning" in sys.argv:
    # подмешиваем параметр OpenRouter во все вызовы модели, не трогая llm.py
    completions = llm._get_client().chat.completions
    completions.create = functools.partial(
        completions.create, extra_body={"reasoning": {"enabled": False}}
    )

chunks = chunk_pages(load_pdf(sys.argv[1]))
print(f"Кусков: {len(chunks)}, символов: {sum(len(c['text']) for c in chunks)}")
start = time.perf_counter()
text = llm.ask("", chunks, "summary")
print(f"\nВыжимка за {time.perf_counter() - start:.0f} с, длина {len(text)} символов\n")
print(text[:1500])
