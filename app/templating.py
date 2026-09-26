"""Jinja2-oppsett med felles kontekst (bruker, handlekurv, infosider, flashmeldinger) og filtre."""
from datetime import datetime
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from . import auth, cart, docs
from .config import CATEGORIES, CATEGORY_LABELS, SHOP_NAME, STATUS
from .pricing import FREE_SHIPPING_THRESHOLD, SHIPPING_METHODS

MONTHS = ["januar", "februar", "mars", "april", "mai", "juni", "juli", "august", "september", "oktober",
          "november", "desember"]


def kr(value) -> str:
    if value is None:
        return ""
    return f"{int(value):,}".replace(",", " ") + " kr"


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def dato(value: str) -> str:
    d = _parse(value)
    return f"{d.day}. {MONTHS[d.month - 1]} {d.year}"


def dato_tid(value: str) -> str:
    d = _parse(value)
    return f"{d.day}. {MONTHS[d.month - 1]} {d.year} kl. {d:%H:%M}"


def _context(request: Request) -> dict:
    return {
        "shop_name": SHOP_NAME,
        "user": auth.current_user(request),
        "cart_count": cart.cart_count(request),
        "categories": CATEGORIES,
        "category_labels": CATEGORY_LABELS,
        "doc_links": docs.list_docs(),
        "flashes": request.session.pop("flashes", []),
        "status_info": STATUS,
        "shipping_methods": SHIPPING_METHODS,
        "free_threshold": FREE_SHIPPING_THRESHOLD,
    }


templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"), context_processors=[_context])
templates.env.filters.update({"kr": kr, "dato": dato, "dato_tid": dato_tid})


def flash(request: Request, message: str, kind: str = "info") -> None:
    request.session.setdefault("flashes", [])
    request.session["flashes"] = request.session["flashes"] + [{"kind": kind, "text": message}]


def render(request: Request, name: str, status_code: int = 200, **context):
    return templates.TemplateResponse(request, name, context, status_code=status_code)
