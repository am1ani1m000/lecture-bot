"""Поиск по кускам лекций. Пока, что просто заглушка"""
import logging

# заводим свой журнал; __name__ подставит имя файла: "search"
logger = logging.getLogger(__name__)


def add_chunks(chunks: list[dict], user_id: int, doc_id: int) -> None:
    """Сохраняет куски в поисковую базу. Пока только пишет в лог."""
    # запись в журнал: от кого пришли куски, какой документ, сколько кусков
    logger.info("add chunks: user=%s doc=%s chunks=%s", user_id, doc_id, len(chunks))

def search(question: str, user_id: int, k: int = 4, doc_id: int | None = None ) -> list[dict]:
    """Возвращает k ближайших кусков. Пока один фиксированный кусок."""
    # фальшивый кусок той же формы, что будет у настоящего
    fake = {
        "text": "Это заглушка: настоящий поиск скоро появится.",
        "source": "example.pdf", # источник: имя файла
        "page": 1,               # страница
        "score": 0.0,            # оценка похожести на вопрос   
    }
    # кладём кусок в список и берём из него не больше k штук  
    return [fake][:k]