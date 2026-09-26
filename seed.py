"""Bygger databasen på nytt fra /data. Kjør: python seed.py"""
import hashlib
import json
import re
import secrets

from app import db
from app.db import DATA_DIR


def hash_password(password: str) -> str:
    salt = secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def load(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def doc_title(text: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else fallback


def main() -> None:
    if db.DB_PATH.exists():
        db.DB_PATH.unlink()
    conn = db.connect()
    conn.executescript(db.SCHEMA)

    products = load("products.json")
    for p in products:
        conn.execute(
            "INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (p["id"], p["slug"], p["name"], p["category"], p["price"], p["sale_price"], p["sku"], p["image_color"],
             p["short_description"], p["description"], json.dumps(p["specs"], ensure_ascii=False), p["care"],
             p["warranty_years"], p["added"], int(p["featured"])),
        )
        for v in p["variants"]:
            conn.execute("INSERT INTO variants VALUES (?,?,?,?,?)", (v["sku"], p["id"], v["size"], v["color"], v["stock"]))

    for r in load("reviews.json"):
        conn.execute("INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?)",
                     (r["id"], r["product_id"], r["author"], r["rating"], r["title"], r["text"], r["date"],
                      int(r["is_demo_data"])))

    customers = load("customers.json")
    for c in customers:
        a = c["address"]
        conn.execute("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?)",
                     (c["id"], c["name"], c["email"], hash_password(c["password"]), a["street"], a["postal_code"],
                      a["city"], c["created_at"]))

    for d in load("discount_codes.json"):
        conn.execute("INSERT INTO discount_codes VALUES (?,?,?,?,?,?,?,?)",
                     (d["code"], d["type"], d["value"], d["min_subtotal"], d["valid_from"], d["valid_to"],
                      int(d["excludes_sale_items"]), d["description"]))

    orders = load("orders.json")
    for o in orders:
        a = o["shipping_address"]
        conn.execute(
            "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (o["order_number"], o["customer_id"], o["email"], o["created_at"], o["status"], o["shipping_method"],
             o["shipping_cost"], o["discount_code"], o["discount_amount"], o["subtotal"], o["total"],
             o["tracking_number"], o["refund_amount"], a["name"], a["street"], a["postal_code"], a["city"]),
        )
        for l in o["lines"]:
            conn.execute(
                "INSERT INTO order_lines (order_number, product_id, sku, name, variant_label, quantity, unit_price) "
                "VALUES (?,?,?,?,?,?,?)",
                (o["order_number"], l["product_id"], l["sku"], l["name"], l["variant_label"], l["quantity"],
                 l["unit_price"]))
        for h in o["status_history"]:
            conn.execute("INSERT INTO order_status_history (order_number, status, at, note) VALUES (?,?,?,?)",
                         (o["order_number"], h["status"], h["at"], h["note"]))

    docs = sorted((DATA_DIR / "docs").glob("*.md"))
    for path in docs:
        text = path.read_text(encoding="utf-8")
        conn.execute("INSERT INTO docs VALUES (?,?,?)", (path.stem, doc_title(text, path.stem), text))

    conn.commit()
    conn.close()
    print(f"Database bygget: {db.DB_PATH}")
    print(f"  {len(products)} produkter, {len(customers)} kunder, {len(orders)} ordrer, {len(docs)} dokumenter")


if __name__ == "__main__":
    main()
