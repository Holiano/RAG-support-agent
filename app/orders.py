"""Ordrer: opprettelse, oppslag og historikk."""
from datetime import datetime

from .db import query_all, query_one, transaction


class OrderError(Exception):
    pass


def _hydrate(row) -> dict:
    order = dict(row)
    order["lines"] = [dict(r) for r in query_all(
        "SELECT * FROM order_lines WHERE order_number = ? ORDER BY id", (order["order_number"],))]
    order["history"] = [dict(r) for r in query_all(
        "SELECT * FROM order_status_history WHERE order_number = ? ORDER BY at, id", (order["order_number"],))]
    return order


def get_order(order_number: str) -> dict | None:
    row = query_one("SELECT * FROM orders WHERE order_number = ?", (order_number,))
    return _hydrate(row) if row else None


def orders_for_customer(customer_id: int) -> list[dict]:
    rows = query_all("SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))
    return [_hydrate(r) for r in rows]


def find_for_tracking(order_number: str, email: str) -> dict | None:
    row = query_one("SELECT * FROM orders WHERE upper(order_number) = ? AND lower(email) = ?",
                    (order_number.strip().upper(), email.strip().lower()))
    return _hydrate(row) if row else None


def create_order(*, customer_id: int | None, email: str, address: dict, method: str, lines: list[dict],
                 totals: dict, code: str | None) -> str:
    """Lagrer ordren, trekker fra lager og skriver første statushistorikk. Kaster OrderError ved for lite lager."""
    now = datetime.now().isoformat(timespec="minutes")
    with transaction() as conn:
        for l in lines:
            updated = conn.execute("UPDATE variants SET stock = stock - ? WHERE sku = ? AND stock >= ?",
                                   (l["quantity"], l["sku"], l["quantity"])).rowcount
            if not updated:
                raise OrderError(f"{l['name']} ({l['variant_label']}) har ikke nok på lager lenger.")

        last = conn.execute("SELECT MAX(CAST(SUBSTR(order_number, 4) AS INTEGER)) FROM orders").fetchone()[0] or 10000
        number = f"VH-{last + 1}"
        conn.execute(
            "INSERT INTO orders (order_number, customer_id, email, created_at, status, shipping_method, shipping_cost, "
            "discount_code, discount_amount, subtotal, total, tracking_number, refund_amount, ship_name, ship_street, "
            "ship_postal_code, ship_city) VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,?,?,?,?)",
            (number, customer_id, email, now, "mottatt", method, totals["shipping"], code, totals["discount"],
             totals["subtotal"], totals["total"], address["name"], address["street"], address["postal_code"],
             address["city"]))
        for l in lines:
            conn.execute(
                "INSERT INTO order_lines (order_number, product_id, sku, name, variant_label, quantity, unit_price) "
                "VALUES (?,?,?,?,?,?,?)",
                (number, l["product_id"], l["sku"], l["name"], l["variant_label"], l["quantity"], l["unit_price"]))
        conn.execute("INSERT INTO order_status_history (order_number, status, at, note) VALUES (?,?,?,?)",
                     (number, "mottatt", now, "Bestillingen er mottatt."))
    return number
