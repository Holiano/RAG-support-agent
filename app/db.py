"""Databasetilgang (sqlite3). Skjemaet ligger her og brukes av seed.py."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.environ.get("DB_PATH", ROOT / "shop.db"))

SCHEMA = """
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price INTEGER NOT NULL,
    sale_price INTEGER,
    sku TEXT NOT NULL UNIQUE,
    image_color TEXT NOT NULL,
    short_description TEXT NOT NULL,
    description TEXT NOT NULL,
    specs TEXT NOT NULL,              -- JSON (ordnet)
    care TEXT NOT NULL,
    warranty_years INTEGER NOT NULL,
    added TEXT NOT NULL,
    featured INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE variants (
    sku TEXT PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    size TEXT,
    color TEXT,
    stock INTEGER NOT NULL
);
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    author TEXT NOT NULL,
    rating INTEGER NOT NULL,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    date TEXT NOT NULL,
    is_demo_data INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    street TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    city TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE orders (
    order_number TEXT PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    email TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    shipping_method TEXT NOT NULL,
    shipping_cost INTEGER NOT NULL,
    discount_code TEXT,
    discount_amount INTEGER NOT NULL DEFAULT 0,
    subtotal INTEGER NOT NULL,
    total INTEGER NOT NULL,
    tracking_number TEXT,
    refund_amount INTEGER,
    ship_name TEXT NOT NULL,
    ship_street TEXT NOT NULL,
    ship_postal_code TEXT NOT NULL,
    ship_city TEXT NOT NULL
);
CREATE TABLE order_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL REFERENCES orders(order_number),
    product_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    name TEXT NOT NULL,
    variant_label TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price INTEGER NOT NULL
);
CREATE TABLE order_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL REFERENCES orders(order_number),
    status TEXT NOT NULL,
    at TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE discount_codes (
    code TEXT PRIMARY KEY,
    type TEXT NOT NULL,               -- 'percent' | 'fixed'
    value INTEGER NOT NULL,
    min_subtotal INTEGER NOT NULL DEFAULT 0,
    valid_from TEXT NOT NULL,
    valid_to TEXT NOT NULL,
    excludes_sale_items INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL
);
CREATE TABLE wishlist (
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    added_at TEXT NOT NULL,
    PRIMARY KEY (customer_id, product_id)
);
CREATE TABLE docs (
    slug TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction():
    """Én tilkobling, commit ved suksess og rollback ved feil."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query_all(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    with transaction() as conn:
        return conn.execute(sql, params).fetchall()


def query_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    with transaction() as conn:
        return conn.execute(sql, params).fetchone()


def execute(sql: str, params: tuple = ()) -> int:
    with transaction() as conn:
        return conn.execute(sql, params).rowcount
