"""Обращение к языковой модели и эмбеддингам."""
import logging
from pathlib import Path

import time
from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

import config

log = logging.getLogger(__name__)

MODES = ("answer", "summary", "cards", "cheatsheet")
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Создаёт клиента при первом вызове, а не при импорте модуля."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL, timeout=60)
    return _client


def _load_prompt(mode: str) -> str:
    """Читает шаблон промпта из prompts/<mode>.txt."""
    return (PROMPTS_DIR / f"{mode}.txt").read_text(encoding="utf-8")


def _format_context(chunks: list[dict]) -> str:
    """Склеивает куски в один текст с пометкой источника у каждого."""
    parts = [f"[{c['source']}, стр. {c['page']}]\n{c['text']}" for c in chunks]
    return "\n\n".join(parts)

RETRY_PAUSES = (2, 5, 10)  # секунды перед повторами при 429 и таймауте


class LLMBusyError(Exception):
    """Модель недоступна после всех повторов."""


def _call_model(prompt: str) -> str:
    """Отправляет промпт модели. При 429 и таймауте повторяет с паузами 2, 5, 10 с."""
    for attempt, pause in enumerate((0, *RETRY_PAUSES)):
        if pause:
            log.warning("Модель недоступна, повтор %d через %d с", attempt, pause)
            time.sleep(pause)
        try:
            resp = _get_client().chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content or ""
        except (RateLimitError, APITimeoutError, APIConnectionError) as e:
            log.warning("Ошибка модели: %s", type(e).__name__)
    raise LLMBusyError("Модель сейчас перегружена, попробуй через минуту")

SUMMARY_PART_CHARS = 12_000  # сколько символов лекции отправляем модели за один запрос


def _split_by_size(chunks: list[dict], limit: int) -> list[list[dict]]:
    """Делит куски на группы, в каждой не больше limit символов текста."""
    groups: list[list[dict]] = [[]]
    size = 0
    for chunk in chunks:
        if groups[-1] and size + len(chunk["text"]) > limit:
            groups.append([])
            size = 0
        groups[-1].append(chunk)
        size += len(chunk["text"])
    return groups


def _summarize(template: str, chunks: list[dict]) -> str:
    """Выжимка. Длинную лекцию делаем в два шага: по частям, потом сводную."""
    groups = _split_by_size(chunks, SUMMARY_PART_CHARS)
    if len(groups) == 1:
        return _call_model(template.replace("{context}", _format_context(chunks)))
    log.info("Длинная лекция: %d частей, запросов к модели: %d", len(groups), len(groups) + 1)
    parts = [_call_model(template.replace("{context}", _format_context(g))) for g in groups]
    joined = "\n\n".join(f"[Часть {i}]\n{p}" for i, p in enumerate(parts, start=1))
    return _call_model(template.replace("{context}", joined))

def ask(question: str, chunks: list[dict], mode: str) -> str:
    """mode: answer / summary / cards / cheatsheet. Возвращает текст ответа модели."""
    if mode not in MODES:
        raise ValueError(f"Неизвестный режим: {mode}")
    template = _load_prompt(mode)
    if not template.strip():
        raise ValueError(f"Пустой промпт prompts/{mode}.txt")
    if mode == "summary":
        return _summarize(template, chunks)
    prompt = template.replace("{context}", _format_context(chunks))
    prompt = prompt.replace("{question}", question)
    return _call_model(prompt)

_embed_model = None  # SentenceTransformer, загружается при первом вызове embed()


def _get_embed_model():
    """Загружает модель эмбеддингов один раз: сначала из кэша, без сети."""
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer  # тяжёлый импорт, только когда нужен

        name = config.EMBED_MODEL
        try:
            # только из кэша ~/.cache/huggingface, без запросов к Hugging Face
            _embed_model = SentenceTransformer(name, local_files_only=True)
            log.info("Модель эмбеддингов %s загружена из кэша", name)
        except Exception:
            log.info("Модели %s нет в кэше, скачиваю (один раз)", name)
            try:
                _embed_model = SentenceTransformer(name)
            except Exception as e:
                raise RuntimeError(
                    f"Не удалось загрузить модель эмбеддингов '{name}'. "
                    "Проверь EMBED_MODEL в .env и интернет при первом запуске."
                ) from e
    return _embed_model


def embed(texts: list[str]) -> list[list[float]]:
    """Возвращает нормализованные векторы для списка текстов (локальная модель)."""
    if not texts:
        return []
    vectors = _get_embed_model().encode(texts, normalize_embeddings=True)
    return vectors.tolist()
