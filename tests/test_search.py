"""Автотесты search.py: сохранение, поиск, фильтр, изоляция."""
import unittest
from unittest.mock import patch

import chromadb

import search

LECTURE = [
    {"text": "Рекурсия — это вызов функции самой себя.", "source": "recursion.pdf", "page": 1, "chunk_id": "0"},
    {"text": "Базовый случай останавливает рекурсию.", "source": "recursion.pdf", "page": 1, "chunk_id": "1"},
    {"text": "Стек вызовов хранит незавершённые функции.", "source": "recursion.pdf", "page": 2, "chunk_id": "2"},
]
OTHER = [
    {"text": "Быстрая сортировка выбирает опорный элемент.", "source": "sort.pdf", "page": 1, "chunk_id": "0"},
]


class SearchTest(unittest.TestCase):
    def setUp(self):
        """Перед каждым тестом: база в памяти вместо базы на диске."""
        self.client = chromadb.EphemeralClient()
        p = patch.object(search, "_client", self.client)
        p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        """После каждого теста: удалить все коллекции."""
        for collection in self.client.list_collections():
            self.client.delete_collection(collection.name)

    def test_upsert_no_duplicates(self):
        search.add_chunks(LECTURE, user_id=1, doc_id=1)
        search.add_chunks(LECTURE, user_id=1, doc_id=1)
        self.assertEqual(search._get_collection(1).count(), 3)

    def test_finds_right_chunk_with_source(self):
        search.add_chunks(LECTURE, user_id=1, doc_id=1)
        top = search.search("Что останавливает рекурсию?", user_id=1, k=2)[0]
        self.assertEqual(top["text"], "Базовый случай останавливает рекурсию.")
        self.assertEqual(top["source"], "recursion.pdf")
        self.assertEqual(top["page"], 1)
        self.assertTrue(0 <= top["score"] <= 1)

    def test_doc_id_filter(self):
        search.add_chunks(LECTURE, user_id=1, doc_id=1)
        search.add_chunks(OTHER, user_id=1, doc_id=2)
        results = search.search("Как работает быстрая сортировка?", user_id=1, doc_id=1)
        self.assertTrue(results)
        for r in results:
            self.assertEqual(r["source"], "recursion.pdf")

    def test_users_isolated(self):
        search.add_chunks(LECTURE, user_id=1, doc_id=1)
        self.assertEqual(search.search("рекурсия", user_id=2), [])

    def test_empty_chunks_do_nothing(self):
        search.add_chunks([], user_id=1, doc_id=1)
        self.assertEqual(search.search("рекурсия", user_id=1), [])

    def test_k_larger_than_collection(self):
        search.add_chunks(OTHER, user_id=1, doc_id=2)
        self.assertEqual(len(search.search("сортировка", user_id=1, k=4)), 1)

    def test_empty_question(self):
        search.add_chunks(LECTURE, user_id=1, doc_id=1)
        self.assertEqual(search.search("   ", user_id=1), [])


if __name__ == "__main__":
    unittest.main()
