"""Проверка, что языковая модель отвечает. Настройки берутся из config.py."""
import sys
from pathlib import Path

# Скрипт лежит в scripts/, а config.py в корне проекта.
# Добавляем корень в путь поиска модулей, чтобы сработал import config.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import OpenAI

import config

if not config.LLM_API_KEY:
    sys.exit("Нет LLM_API_KEY: проверь, что файл .env есть и ключ заполнен")

client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)
resp = client.chat.completions.create(
    model=config.LLM_MODEL,
    messages=[{"role": "user", "content": "Скажи привет одним предложением"}],
)
print(f"Модель: {resp.model}")
print(resp.choices[0].message.content)
