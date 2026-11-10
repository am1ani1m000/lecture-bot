"""Показывает, какие лекции и сколько кусков лежат в Chroma."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb

from search import CHROMA_PATH

client = chromadb.PersistentClient(path=str(CHROMA_PATH))

for item in client.list_collections():
    # в новых версиях chromadb тут строка, в старых — объект коллекции
    name = item if isinstance(item, str) else item.name
    col = client.get_collection(name)
    data = col.get(include=["metadatas"])

    counts = Counter(m.get("source", "?") for m in data["metadatas"])
    print(f"\n=== Коллекция {name}: {col.count()} кусков, {len(counts)} лекций")
    for source, n in sorted(counts.items()):
        print(f"{n:6}  {source}")