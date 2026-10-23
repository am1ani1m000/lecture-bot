"""Проверка embed(). Запуск: python scripts/test_embed.py"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import llm

logging.basicConfig(level=logging.INFO)


def sim(a: list[float], b: list[float]) -> float:
    """Косинусное сходство нормализованных векторов: сумма произведений."""
    return sum(x * y for x, y in zip(a, b))


cat, kitten, tax = llm.embed(["кошка", "кот", "налог"])
print("Длина вектора:", len(cat))
print("Норма вектора (должна быть 1.0):", round(sum(x * x for x in cat) ** 0.5, 3))
print(f"кошка ~ кот:   {sim(cat, kitten):.3f}")
print(f"кошка ~ налог: {sim(cat, tax):.3f}")
print("ОК" if sim(cat, kitten) > sim(cat, tax) else "ОШИБКА: кошка ближе к налогу")
print("Пустой список:", llm.embed([]))
