"""Замер скорости модели (#68). Запуск: python scripts/measure_speed.py"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config
import llm

QUESTIONS = [
    "Что такое рекурсия?",
    "Чем базовый случай отличается от рекурсивного шага?",
    "Почему глубокая рекурсия может упасть с ошибкой?",
]
VARIANTS = {
    "как сейчас": {},
    "без рассуждений": {"reasoning": {"enabled": False}},
}

client = llm._get_client()
for name, extra in VARIANTS.items():
    print(f"\n== {name}")
    for q in QUESTIONS:
        start = time.perf_counter()
        resp = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": q}],
            temperature=0,
            extra_body=extra,  # параметры OpenRouter, которых нет в библиотеке openai
        )
        seconds = time.perf_counter() - start
        details = resp.usage.completion_tokens_details
        reasoning = details.reasoning_tokens if details else None
        print(f"{seconds:5.1f} с, токенов {resp.usage.completion_tokens}, на рассуждение {reasoning} | {q}")
