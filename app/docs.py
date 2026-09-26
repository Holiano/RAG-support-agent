"""Infosider rendres direkte fra markdown-filene i data/docs (samme tekst som en senere RAG-løsning bruker)."""
import re
from functools import lru_cache

import markdown

from .config import DOC_ORDER
from .db import DATA_DIR

DOCS_DIR = DATA_DIR / "docs"


def _title(text: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else fallback


def list_docs() -> list[dict]:
    """[{slug, title}] i fast rekkefølge (DOC_ORDER først, resten alfabetisk)."""
    slugs = {p.stem for p in DOCS_DIR.glob("*.md")}
    ordered = [s for s in DOC_ORDER if s in slugs] + sorted(slugs - set(DOC_ORDER))
    return [{"slug": s, "title": _title((DOCS_DIR / f"{s}.md").read_text(encoding="utf-8"), s)} for s in ordered]


@lru_cache(maxsize=64)
def _render(slug: str, mtime: float) -> tuple[str, str]:
    text = (DOCS_DIR / f"{slug}.md").read_text(encoding="utf-8")
    html = markdown.markdown(text, extensions=["tables", "sane_lists"])
    return _title(text, slug), html


def render_doc(slug: str) -> tuple[str, str] | None:
    """(tittel, html) eller None. Cachen nullstilles når filen endres."""
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        return None
    path = DOCS_DIR / f"{slug}.md"
    if not path.is_file():
        return None
    return _render(slug, path.stat().st_mtime)
