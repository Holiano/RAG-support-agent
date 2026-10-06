"""Indekserer kunnskapsbasen: deler data/docs/*.md i tekstbiter, embedder nye og endrede, og lagrer dem i agentens
database. Uendrede tekstbiter (samme innholdshash) embeddes ikke på nytt. Tekstbiter som er borte fra dokumentene slettes.

Kjør:  python index_docs.py            indekser
       python index_docs.py --dry-run  vis tekstbitene uten å bruke nett eller database
"""
import argparse
import sys

from app.agent import settings
from app.agent.chunking import chunk_markdown
from app.config import SHOP_NAME
from app.db import DATA_DIR

DOCS_DIR = DATA_DIR / "docs"


def load_chunks():
    return [c for path in sorted(DOCS_DIR.glob("*.md"))
            for c in chunk_markdown(path.stem, path.read_text(encoding="utf-8"))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Vis tekstbitene, ikke rør nett eller database.")
    parser.add_argument("--shop-id", type=int, default=settings.SHOP_ID)
    args = parser.parse_args()

    chunks = load_chunks()
    if args.dry_run:
        for c in chunks:
            print(f"[{c.doc_slug}] {c.heading_path}  ({len(c.content)} tegn, {c.content_hash[:8]})")
        print(f"\n{len(chunks)} tekstbiter fra {len(set(c.doc_slug for c in chunks))} dokumenter")
        return 0

    if not settings.is_configured():
        print("GEMINI_API_KEY og AGENT_DB_URL må være satt (se .env). Avbryter.", file=sys.stderr)
        return 1

    from app.agent import embeddings, store

    store.ensure_schema()
    store.ensure_shop(args.shop_id, SHOP_NAME)
    existing = store.existing_hashes(args.shop_id)
    changed = [c for c in chunks if existing.get(c.key) != c.content_hash]
    if changed:
        vectors = embeddings.embed([c.content for c in changed])
        store.upsert_chunks(args.shop_id, changed, vectors)
    removed = store.delete_chunks_except(args.shop_id, {c.key for c in chunks})
    print(f"Butikk {args.shop_id}: {len(chunks)} tekstbiter, {len(changed)} embeddet på nytt, "
          f"{len(chunks) - len(changed)} uendret, {removed} slettet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
