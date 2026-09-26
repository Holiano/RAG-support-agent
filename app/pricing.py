"""Priser, rabattkoder og frakt. Reglene her følger data/docs/frakt-og-levering.md og betaling.md."""
from datetime import date

FREE_SHIPPING_THRESHOLD = 1200  # varesum etter rabatt

SHIPPING_METHODS = {
    "hentested": {"name": "Hentested", "price": 49, "free_eligible": True,
                  "description": "Hentes på hentested nær deg"},
    "hjemlevering": {"name": "Hjemlevering", "price": 99, "free_eligible": True,
                     "description": "Leveres hjem til deg"},
    "ekspress": {"name": "Ekspress", "price": 199, "free_eligible": False,
                 "description": "Neste virkedag ved bestilling før kl. 14:00 (aldri gratis)"},
}
DEFAULT_SHIPPING = "hjemlevering"

# (standard, ekspress)
DELIVERY_TIMES = {
    "Vestlandet": ("1–3 virkedager", "1 virkedag"),
    "Austlandet": ("2–3 virkedager", "1–2 virkedager"),
    "Sørlandet": ("2–4 virkedager", "1–2 virkedager"),
    "Trøndelag": ("2–4 virkedager", "1–2 virkedager"),
    "Nord-Norge": ("3–6 virkedager", "2–3 virkedager"),
}


def is_blocked_postal(postal_code: str) -> bool:
    """Svalbard (9170–9179) og Jan Mayen (8099) leveres ikke via nettbutikken."""
    n = int(postal_code)
    return 9170 <= n <= 9179 or n == 8099


def region_for_postal(postal_code: str) -> str:
    n = int(postal_code)
    if n < 4000:
        return "Austlandet"
    if n < 4400 or 5000 <= n < 7000:
        return "Vestlandet"
    if n < 5000:
        return "Sørlandet"
    if n < 8000:
        return "Trøndelag"
    return "Nord-Norge"


def delivery_estimate(postal_code: str, method: str) -> str:
    standard, express = DELIVERY_TIMES[region_for_postal(postal_code)]
    return express if method == "ekspress" else standard


def check_code(code: dict, lines: list[dict], subtotal: int, today: date) -> tuple[int, str | None]:
    """Returnerer (rabatt i kroner, feilmelding). Feilmelding er None når koden kan brukes."""
    if today < date.fromisoformat(code["valid_from"]):
        return 0, f"Rabattkoden {code['code']} er ikke gyldig ennå."
    if today > date.fromisoformat(code["valid_to"]):
        return 0, f"Rabattkoden {code['code']} er utløpt."
    if subtotal < code["min_subtotal"]:
        missing = code["min_subtotal"] - subtotal
        return 0, (f"Rabattkoden {code['code']} krever varekjøp på minst {code['min_subtotal']:,} kr "
                   f"(du mangler {missing:,} kr).".replace(",", " "))
    if code["type"] == "percent":
        eligible = sum(l["unit_price"] * l["quantity"] for l in lines
                       if not (code["excludes_sale_items"] and l["unit_price"] < l["regular_price"]))
        if eligible == 0:
            return 0, f"Rabattkoden {code['code']} gjelder ikke varer på tilbud."
        return (eligible * code["value"] + 50) // 100, None
    return min(code["value"], subtotal), None


def compute_totals(lines: list[dict], code: dict | None, method: str, today: date | None = None) -> dict:
    """lines: dict med unit_price, regular_price, quantity."""
    today = today or date.today()
    subtotal = sum(l["unit_price"] * l["quantity"] for l in lines)
    discount, code_error = 0, None
    if code is not None and lines:
        discount, code_error = check_code(code, lines, subtotal, today)
    goods_total = subtotal - discount
    info = SHIPPING_METHODS[method]
    shipping = info["price"]
    if lines and info["free_eligible"] and goods_total >= FREE_SHIPPING_THRESHOLD:
        shipping = 0
    if not lines:
        shipping = 0
    remaining = max(0, FREE_SHIPPING_THRESHOLD - goods_total)
    return {
        "subtotal": subtotal, "discount": discount, "code_error": code_error, "goods_total": goods_total,
        "shipping": shipping, "total": goods_total + shipping,
        "free_remaining": remaining, "free_progress": min(100, int(goods_total * 100 / FREE_SHIPPING_THRESHOLD)),
        "qualifies_free": info["free_eligible"] and goods_total >= FREE_SHIPPING_THRESHOLD,
    }
