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


def search(question: str, user_id: int, k: int = 4,
           doc_id: int | None = None) -> list[dict]:
    """Возвращает k ближайших кусков:
    [{"text": str, "source": str, "page": int, "score": float}]."""
    if not question.strip():
            return []
    
    collection = _get_collection(user_id)
    total = collection.count()
    if total == 0:
        return []

    question_vector = llm.embed([question])[0]
    where = {"doc_id": doc_id} if doc_id is not None else None

    results = collection.query(
        query_embeddings=[question_vector],
        n_results=min(k, total),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    found = []
    for text, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        found.append({
            "text": text,
            "source": meta["source"],
            "page": meta["page"],
            "score": round(1 - distance, 3),
        })
    return found