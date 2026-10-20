import unittest

from documents import chunk_pages

TEXT = "".join(str(i % 10) for i in range(1500))
PAGES = [
    {"text": TEXT, "source": "t.pdf", "page": 1},
    {"text": "короткая", "source": "t.pdf", "page": 2},
]


class TestChunkPages(unittest.TestCase):
    def test_size_and_overlap(self):
        chunks = chunk_pages(PAGES, size=800, overlap=100)
        self.assertEqual(len(chunks[0]["text"]), 800)
        self.assertEqual(chunks[0]["text"][-100:], chunks[1]["text"][:100])

    def test_does_not_cross_pages(self):
        chunks = chunk_pages(PAGES)
        self.assertEqual([c["page"] for c in chunks], [1, 1, 2])
        self.assertEqual(chunks[2]["text"], "короткая")

    def test_fields_and_unique_ids(self):
        chunks = chunk_pages(PAGES)
        for c in chunks:
            self.assertEqual(set(c), {"text", "source", "page", "chunk_id"})
        ids = [c["chunk_id"] for c in chunks]
        self.assertEqual(len(ids), len(set(ids)))

    def test_empty_input(self):
        self.assertEqual(chunk_pages([]), [])

    def test_bad_overlap(self):
        with self.assertRaises(ValueError):
            chunk_pages(PAGES, size=100, overlap=100)


if __name__ == "__main__":
    unittest.main()