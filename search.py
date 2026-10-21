"""Поиск по кускам лекций в Chroma."""
import logging

import chromadb

import llm

logger = logging.getLogger(__name__)

CHROMA_PATH = "chroma_db"

_client = chromadb.PersistentClient(path=CHROMA_PATH)


def _get_collection(user_id: int):
    """Возвращает коллекцию пользователя, при первом обращении создаёт её."""
    return _client.get_or_create_collection(
        name=f"user_{user_id}",
        configuration={"hnsw": {"space": "cosine"}},
    )


def add_chunks(chunks: list[dict], user_id: int, doc_id: int) -> None:
    """Считает эмбеддинги и сохраняет куски в Chroma (коллекция на пользователя)."""
    if not chunks:
        logger.warning("Пустой список кусков, doc_id=%s", doc_id)
        return

    texts = [c["text"] for c in chunks]
    vectors = llm.embed(texts)

    ids = [f"{doc_id}_{c['page']}_{c['chunk_id']}" for c in chunks]
    metadatas = [
        {"source": c["source"], "page": c["page"], "doc_id": doc_id}
        for c in chunks
    ]

    collection = _get_collection(user_id)
    collection.upsert(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)
    logger.info("Сохранено %d кусков, doc_id=%s", len(chunks), doc_id)