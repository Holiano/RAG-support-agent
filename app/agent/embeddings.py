"""Embeddinger via Gemini. Samme modell og dimensjon brukes for tekstbiter og spørsmål."""
from google.genai import types

from . import settings
from .gemini import client

BATCH = 50


def embed(texts: list[str]) -> list[list[float]]:
    """Én embedding per tekst. Tekstene må pakkes som hver sin Content; en liste med strenger tolkes som ett innhold."""
    out: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        batch = texts[i:i + BATCH]
        res = client().models.embed_content(
            model=settings.EMBEDDING_MODEL,
            contents=[types.Content(parts=[types.Part.from_text(text=t)]) for t in batch],
            config=types.EmbedContentConfig(output_dimensionality=settings.EMBEDDING_DIM))
        if len(res.embeddings) != len(batch):
            raise RuntimeError(f"Gemini ga {len(res.embeddings)} embeddinger for {len(batch)} tekster")
        out.extend(list(e.values) for e in res.embeddings)
    return out


def embed_query(text: str) -> list[float]:
    return embed([text])[0]
