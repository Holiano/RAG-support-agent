"""Deler et markdown-dokument i tekstbiter: én per overskrift, med overskriftsstien lagt først i teksten."""
import hashlib
import re
from dataclasses import dataclass

HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.M)


@dataclass(frozen=True)
class Chunk:
    doc_slug: str
    doc_title: str
    heading_path: str  # f.eks. "Retur og bytte > Hva kan ikke returneres?"
    content: str  # overskriftssti + tekst, slik det embeddes og vises til modellen
    content_hash: str

    @property
    def key(self) -> tuple[str, str]:
        return self.doc_slug, self.heading_path


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_markdown(doc_slug: str, text: str) -> list[Chunk]:
    text = text.replace("\r\n", "\n")
    matches = list(HEADING.finditer(text))
    title = next((m.group(2).strip() for m in matches if len(m.group(1)) == 1), doc_slug)

    if not matches:
        body = text.strip()
        return [Chunk(doc_slug, title, title, f"{title}\n\n{body}", _hash(body))] if body else []

    chunks: list[Chunk] = []
    path: list[str] = [title]
    for i, m in enumerate(matches):
        level = len(m.group(1))
        name = m.group(2).strip()
        path = [name] if level == 1 else path[: level - 1] + [name]
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        if not body:
            continue  # overskrift som bare samler underoverskrifter
        heading_path = " > ".join(path)
        content = f"{heading_path}\n\n{body}"
        chunks.append(Chunk(doc_slug, title, heading_path, content, _hash(content)))
    return chunks
