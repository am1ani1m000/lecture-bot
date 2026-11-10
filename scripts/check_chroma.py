"""Показывает, какие лекции и сколько кусков лежат в Chroma."""
from collections import Counter

import chromadb

client = chromadb.PersistentClient(path="chroma_db")

for item in client.list_collections():
    # в новых версиях chromadb тут строка, в старых — объект коллекции
    name = item if isinstance(item, str) else item.name
    col = client.get_collection(name)
    data = col.get(include=["metadatas"])

    counts = Counter(m.get("source", "?") for m in data["metadatas"])
    print(f"\n=== Коллекция {name}: {col.count()} кусков, {len(counts)} лекций")
    for source, n in sorted(counts.items()):
        print(f"{n:6}  {source}")