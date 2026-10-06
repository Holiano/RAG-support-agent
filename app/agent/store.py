"""Agentens eget lager (Postgres + pgvector): tekstbiter med embeddinger, samtalelogg og butikker.

Butikkens egne data (shop.db) røres aldri herfra, se docs/adr/0001.
"""
import json
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from . import settings
from .chunking import Chunk

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _vec(values: list[float]) -> str:
    """pgvector godtar tekstformen '[0.1,0.2,...]' når den castes til vector."""
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


@contextmanager
def connect():
    with psycopg.connect(settings.AGENT_DB_URL, row_factory=dict_row) as conn:
        yield conn


def ensure_schema() -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8").replace("{DIM}", str(settings.EMBEDDING_DIM))
    with connect() as conn:
        conn.execute(sql)


def ensure_shop(shop_id: int, name: str) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO agent.shops (id, name) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
                     (shop_id, name))


# ---- Tekstbiter ----

def existing_hashes(shop_id: int) -> dict[tuple[str, str], str]:
    with connect() as conn:
        rows = conn.execute("SELECT doc_slug, heading_path, content_hash FROM agent.chunks WHERE shop_id = %s",
                            (shop_id,)).fetchall()
    return {(r["doc_slug"], r["heading_path"]): r["content_hash"] for r in rows}


def upsert_chunks(shop_id: int, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    with connect() as conn:
        for chunk, emb in zip(chunks, embeddings, strict=True):
            conn.execute(
                """INSERT INTO agent.chunks (shop_id, doc_slug, doc_title, heading_path, content, content_hash, embedding)
                   VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                   ON CONFLICT (shop_id, doc_slug, heading_path) DO UPDATE SET
                     doc_title = EXCLUDED.doc_title, content = EXCLUDED.content, content_hash = EXCLUDED.content_hash,
                     embedding = EXCLUDED.embedding, updated_at = now()""",
                (shop_id, chunk.doc_slug, chunk.doc_title, chunk.heading_path, chunk.content, chunk.content_hash, _vec(emb)))


def delete_chunks_except(shop_id: int, keep: set[tuple[str, str]]) -> int:
    """Sletter tekstbiter som ikke lenger finnes i kunnskapsbasen. Returnerer antall slettet."""
    removed = 0
    with connect() as conn:
        for key in set(existing_hashes(shop_id)) - keep:
            removed += conn.execute("DELETE FROM agent.chunks WHERE shop_id = %s AND doc_slug = %s AND heading_path = %s",
                                    (shop_id, *key)).rowcount
    return removed


def search(shop_id: int, embedding: list[float], k: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT doc_slug, doc_title, heading_path, content, 1 - (embedding <=> %s::vector) AS score
               FROM agent.chunks WHERE shop_id = %s ORDER BY embedding <=> %s::vector LIMIT %s""",
            (_vec(embedding), shop_id, _vec(embedding), k)).fetchall()
    return [dict(r, score=round(float(r["score"]), 4)) for r in rows]


def all_chunks(shop_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT doc_slug, doc_title, heading_path, content FROM agent.chunks WHERE shop_id = %s "
                            "ORDER BY doc_slug, id", (shop_id,)).fetchall()
    return [dict(r, score=None) for r in rows]


# ---- Samtalelogg ----

def log_turn(shop_id: int, record: dict) -> None:
    with connect() as conn:
        conn.execute(
            """INSERT INTO agent.chat_log (shop_id, customer_id, message, history_length, retrieved, tool_calls, reply,
                                           model, latency_ms, input_tokens, output_tokens, cached_tokens, error)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (shop_id, record.get("customer_id"), record["message"], record.get("history_length", 0),
             Jsonb(record.get("retrieved", [])), Jsonb(json.loads(json.dumps(record.get("tool_calls", []), default=str))),
             record.get("reply"), record["model"], record.get("latency_ms"), record.get("input_tokens"),
             record.get("output_tokens"), record.get("cached_tokens"), record.get("error")))
