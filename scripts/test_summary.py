"""Проверка выжимки в два шага. Запуск: python scripts/test_summary.py"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import llm

logging.basicConfig(level=logging.INFO)

text = (ROOT / "tests/fixtures/recursion_lecture.txt").read_text(encoding="utf-8")
paragraphs = [p for p in text.split("\n\n") if p.strip()]
chunks = [{"text": p, "source": "recursion_lecture.txt", "page": 1} for p in paragraphs]

# Маленький лимит, чтобы короткая лекция разбилась на части и сработал второй шаг.
llm.SUMMARY_PART_CHARS = 1500
print(llm.ask("", chunks, "summary"))
