"""Produktkatalog: henting, søk, filtrering og sortering."""
import json

from .config import CATEGORY_LABELS
from .db import query_all


def stock_status(stock: int) -> tuple[str, str]:
    """(tekst, nøkkel) for lagerstatus."""
    if stock <= 0:
        return "Utsolgt", "out"
    if stock <= 3:
        return f"Få igjen ({stock})", "low"
    return "På lager", "ok"


def _variant_label(size, color) -> str:
    return " / ".join(x for x in (size, color) if x)


def list_products() -> list[dict]:
    rows = query_all("SELECT * FROM products")
    variants = query_all("SELECT * FROM variants ORDER BY rowid")
    ratings = {r["product_id"]: r for r in query_all(
        "SELECT product_id, AVG(rating) AS avg, COUNT(*) AS n FROM reviews GROUP BY product_id")}

    by_product: dict[int, list[dict]] = {}
    for v in variants:
        text, key = stock_status(v["stock"])
        by_product.setdefault(v["product_id"], []).append({
            "sku": v["sku"], "size": v["size"], "color": v["color"], "stock": v["stock"],
            "label": _variant_label(v["size"], v["color"]), "stock_text": text, "stock_key": key,
        })

    products = []
    for r in rows:
        p = dict(r)
        p["specs"] = json.loads(p["specs"])
        p["variants"] = by_product.get(p["id"], [])
        p["total_stock"] = sum(v["stock"] for v in p["variants"])
        p["in_stock"] = p["total_stock"] > 0
        p["on_sale"] = p["sale_price"] is not None
        p["eff_price"] = p["sale_price"] if p["on_sale"] else p["price"]
        p["category_label"] = CATEGORY_LABELS[p["category"]]
        rating = ratings.get(p["id"])
        p["avg_rating"] = round(rating["avg"], 1) if rating else None
        p["review_count"] = rating["n"] if rating else 0
        if not p["in_stock"]:
            p["stock_text"], p["stock_key"] = "Utsolgt", "out"
        elif any(0 < v["stock"] <= 3 for v in p["variants"]):
            p["stock_text"], p["stock_key"] = "Få igjen i noen varianter", "low"
        else:
            p["stock_text"], p["stock_key"] = "På lager", "ok"
        products.append(p)
    return products


def get_product(slug: str) -> dict | None:
    return next((p for p in list_products() if p["slug"] == slug), None)


def get_product_by_id(product_id: int) -> dict | None:
    return next((p for p in list_products() if p["id"] == product_id), None)


def get_reviews(product_id: int) -> list[dict]:
    return [dict(r) for r in query_all("SELECT * FROM reviews WHERE product_id = ? ORDER BY date DESC", (product_id,))]


def related_products(product: dict, limit: int = 4) -> list[dict]:
    same = [p for p in list_products() if p["category"] == product["category"] and p["id"] != product["id"]]
    same.sort(key=lambda p: (not p["in_stock"], -p["featured"], p["name"]))
    return same[:limit]


SORTS = [
    ("anbefalt", "Anbefalt"),
    ("pris_lav", "Pris: lav til høy"),
    ("pris_hoy", "Pris: høy til lav"),
    ("navn", "Navn A–Å"),
    ("nyheter", "Nyheter"),
]

_NORWEGIAN_ORDER = str.maketrans({"æ": "{", "ø": "|", "å": "}"})


def _name_key(p: dict) -> str:
    return p["name"].lower().translate(_NORWEGIAN_ORDER)


def filter_products(products: list[dict], q: str = "", category: str = "", min_price: int | None = None,
                    max_price: int | None = None, in_stock: bool = False, on_sale: bool = False,
                    sort: str = "anbefalt") -> list[dict]:
    result = products
    tokens = q.lower().split()
    if tokens:
        def haystack(p):
            return " ".join([p["name"], p["category_label"], p["sku"], p["short_description"], p["description"],
                             " ".join(v["label"] for v in p["variants"])]).lower()
        result = [p for p in result if all(t in haystack(p) for t in tokens)]
    if category:
        result = [p for p in result if p["category"] == category]
    if min_price is not None:
        result = [p for p in result if p["eff_price"] >= min_price]
    if max_price is not None:
        result = [p for p in result if p["eff_price"] <= max_price]
    if in_stock:
        result = [p for p in result if p["in_stock"]]
    if on_sale:
        result = [p for p in result if p["on_sale"]]

    if sort == "pris_lav":
        result = sorted(result, key=lambda p: (p["eff_price"], _name_key(p)))
    elif sort == "pris_hoy":
        result = sorted(result, key=lambda p: (-p["eff_price"], _name_key(p)))
    elif sort == "navn":
        result = sorted(result, key=_name_key)
    elif sort == "nyheter":
        result = sorted(result, key=lambda p: (p["added"], p["id"]), reverse=True)
    else:
        result = sorted(result, key=lambda p: (-p["featured"], _name_key(p)))
    return result
