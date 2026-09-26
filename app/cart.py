"""Handlekurv i sesjon (cookie): {variant-SKU: antall}, pluss valgt frakt og rabattkode."""
from fastapi import Request

from .db import query_all, query_one
from .pricing import DEFAULT_SHIPPING, SHIPPING_METHODS, compute_totals

MAX_QTY_PER_LINE = 10


def get_cart(request: Request) -> dict[str, int]:
    return dict(request.session.get("cart", {}))


def set_cart(request: Request, cart: dict[str, int]) -> None:
    request.session["cart"] = cart


def cart_count(request: Request) -> int:
    return sum(request.session.get("cart", {}).values())


def get_shipping_method(request: Request) -> str:
    method = request.session.get("shipping_method", DEFAULT_SHIPPING)
    return method if method in SHIPPING_METHODS else DEFAULT_SHIPPING


def get_code(code: str | None) -> dict | None:
    if not code:
        return None
    row = query_one("SELECT * FROM discount_codes WHERE code = ?", (code.strip().upper(),))
    return dict(row) if row else None


def build_lines(cart: dict[str, int]) -> list[dict]:
    if not cart:
        return []
    placeholders = ",".join("?" * len(cart))
    rows = query_all(
        f"SELECT v.sku, v.size, v.color, v.stock, p.id AS product_id, p.name, p.slug, p.price, p.sale_price, "
        f"p.image_color, p.category FROM variants v JOIN products p ON p.id = v.product_id "
        f"WHERE v.sku IN ({placeholders})", tuple(cart))
    by_sku = {r["sku"]: r for r in rows}
    lines = []
    for sku, qty in cart.items():
        r = by_sku.get(sku)
        if r is None:
            continue
        unit = r["sale_price"] if r["sale_price"] is not None else r["price"]
        lines.append({
            "sku": sku, "product_id": r["product_id"], "name": r["name"], "slug": r["slug"],
            "variant_label": " / ".join(x for x in (r["size"], r["color"]) if x),
            "quantity": qty, "unit_price": unit, "regular_price": r["price"], "line_total": unit * qty,
            "on_sale": r["sale_price"] is not None, "stock": r["stock"],
        })
    return lines


def summarize(request: Request) -> dict:
    """Alt handlekurv og kasse trenger: linjer, rabattkode, fraktvalg og totaler."""
    lines = build_lines(get_cart(request))
    method = get_shipping_method(request)
    code_str = request.session.get("discount_code")
    code = get_code(code_str)
    totals = compute_totals(lines, code, method)
    return {"lines": lines, "method": method, "code": code, "code_str": code_str, **totals,
            "count": sum(l["quantity"] for l in lines),
            "stock_problems": [l for l in lines if l["quantity"] > l["stock"]]}
