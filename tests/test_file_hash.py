import os
import tempfile
import unittest

from documents import file_hash


class TestFileHash(unittest.TestCase):
    def test_same_content_same_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [os.path.join(folder, n) for n in ("a.pdf", "b.pdf", "c.pdf")]
            for path, data in zip(paths, (b"lecture", b"lecture", b"other")):
                with open(path, "wb") as f:
                    f.write(data)
            self.assertEqual(file_hash(paths[0]), file_hash(paths[1]))
            self.assertNotEqual(file_hash(paths[0]), file_hash(paths[2]))


if __name__ == "__main__":
    unittest.main()
