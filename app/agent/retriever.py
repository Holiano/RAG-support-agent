"""Henting av tekstbiter. Agenten ser bare grensesnittet `Retriever`, slik at lager og strategi kan byttes.

- VectorRetriever: vektorsøk i agentens database (det agenten bruker i drift).
- FullContextRetriever: alle tekstbiter, uten søk. Referansemåling i testsettet.
- LocalFullContextRetriever: alle tekstbiter lest rett fra data/docs. Krever verken database eller nøkkel.
"""
from pathlib import Path
from typing import Protocol

from . import settings
from .chunking import chunk_markdown


class Retriever(Protocol):
    def search(self, query: str) -> list[dict]: ...


class VectorRetriever:
    def __init__(self, shop_id: int = settings.SHOP_ID, k: int = settings.TOP_K):
        self.shop_id, self.k = shop_id, k

    def search(self, query: str) -> list[dict]:
        from . import embeddings, store
        return store.search(self.shop_id, embeddings.embed_query(query), self.k)


class FullContextRetriever:
    def __init__(self, shop_id: int = settings.SHOP_ID):
        self.shop_id = shop_id

    def search(self, query: str) -> list[dict]:
        from . import store
        return store.all_chunks(self.shop_id)


class LocalFullContextRetriever:
    def __init__(self, docs_dir: Path):
        self.chunks = [
            {"doc_slug": c.doc_slug, "doc_title": c.doc_title, "heading_path": c.heading_path, "content": c.content,
             "score": None}
            for path in sorted(docs_dir.glob("*.md"))
            for c in chunk_markdown(path.stem, path.read_text(encoding="utf-8"))
        ]

    def search(self, query: str) -> list[dict]:
        return list(self.chunks)
