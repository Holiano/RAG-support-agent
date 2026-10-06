-- Agentens eget lager. {DIM} byttes ut med embedding-dimensjonen av store.ensure_schema().
-- Alle tabeller har shop_id: én rad per butikk (leietaker).
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS agent;

CREATE TABLE IF NOT EXISTS agent.shops (
    id          integer PRIMARY KEY,
    name        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent.chunks (
    id            bigserial PRIMARY KEY,
    shop_id       integer NOT NULL REFERENCES agent.shops(id),
    doc_slug      text NOT NULL,
    doc_title     text NOT NULL,
    heading_path  text NOT NULL,
    content       text NOT NULL,
    content_hash  text NOT NULL,
    embedding     vector({DIM}) NOT NULL,
    updated_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (shop_id, doc_slug, heading_path)
);
CREATE INDEX IF NOT EXISTS chunks_shop_idx ON agent.chunks (shop_id);
-- Ingen ANN-indeks ennå: med under noen tusen tekstbiter er eksakt søk raskt nok.
-- Legg til HNSW når det vokser: CREATE INDEX ON agent.chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS agent.chat_log (
    id              bigserial PRIMARY KEY,
    shop_id         integer NOT NULL REFERENCES agent.shops(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    customer_id     integer,
    message         text NOT NULL,
    history_length  integer NOT NULL DEFAULT 0,
    retrieved       jsonb NOT NULL DEFAULT '[]',
    tool_calls      jsonb NOT NULL DEFAULT '[]',
    reply           text,
    model           text NOT NULL,
    latency_ms      integer,
    input_tokens    integer,
    output_tokens   integer,
    cached_tokens   integer,
    error           text
);
CREATE INDEX IF NOT EXISTS chat_log_shop_time_idx ON agent.chat_log (shop_id, created_at DESC);
