import os
import tempfile
import unittest

from pypdf import PdfWriter

from documents import chunk_pages, load_pdf

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

    def test_does_not_cut_words(self):
        words = [f"слово{i}" for i in range(400)]
        page = {"text": " ".join(words), "source": "t.pdf", "page": 1}
        for c in chunk_pages([page]):
            parts = c["text"].split()
            self.assertIn(parts[0], words)
            self.assertIn(parts[-1], words)

    def test_no_tail_inside_previous_chunk(self):
        words = " ".join(f"слово{i}" for i in range(400))
        chunks = chunk_pages([{"text": words, "source": "t.pdf", "page": 1}])
        for prev, cur in zip(chunks, chunks[1:]):
            self.assertNotIn(cur["text"], prev["text"])

    def test_long_word_is_cut(self):
        chunks = chunk_pages([{"text": "x" * 2000, "source": "t.pdf", "page": 1}])
        self.assertEqual([len(c["text"]) for c in chunks], [800, 800, 600])


class TestLoadPdf(unittest.TestCase):
    def test_blank_pages_are_skipped(self):
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "blank.pdf")
            with open(path, "wb") as f:
                writer.write(f)
            self.assertEqual(load_pdf(path), [])


if __name__ == "__main__":
    unittest.main()