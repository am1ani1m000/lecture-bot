MODES = ("answer", "summary", "cards", "cheatsheet")

def ask(question: str, chunks: list[dict], mode: str) -> str:
    """mode:answer / summary / cards / cheatsheet. Возвращает текст."""
    if mode not in MODES:
        raise ValueError(f"Неизвестный режим: {mode}")
    return f"[заглушка llm] режим={mode}, кусков={len(chunks)}"

def embed(texts: list[str]) -> list[list[float]]:
    """Возвращает векторы для списка текстов."""
    return [[0.0] for _ in texts]
