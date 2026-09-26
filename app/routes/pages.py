"""Forside, produktliste, produktside, infosider og produktbilder."""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from .. import catalog, docs
from ..auth import current_user
from ..config import CATEGORY_LABELS
from ..db import query_all
from ..images import placeholder_svg
from ..templating import render

router = APIRouter()


def _int_or_none(value: str | None) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except ValueError:
        return None


def _wishlist_ids(user: dict | None) -> set[int]:
    if not user:
        return set()
    return {r["product_id"] for r in query_all("SELECT product_id FROM wishlist WHERE customer_id = ?", (user["id"],))}


@router.get("/")
def home(request: Request):
    products = catalog.list_products()
    featured = [p for p in catalog.filter_products(products, sort="anbefalt") if p["featured"]][:8]
    on_sale = catalog.filter_products(products, on_sale=True, sort="pris_lav")
    newest = catalog.filter_products(products, sort="nyheter")[:4]
    return render(request, "home.html", featured=featured, on_sale=on_sale, newest=newest,
                  wishlist=_wishlist_ids(current_user(request)))


@router.get("/produkter")
def product_list(request: Request):
    qp = request.query_params
    category = qp.get("kategori", "")
    if category not in CATEGORY_LABELS:
        category = ""
    sort = qp.get("sorter", "anbefalt")
    q = qp.get("q", "").strip()
    min_price, max_price = _int_or_none(qp.get("min")), _int_or_none(qp.get("maks"))
    in_stock, on_sale = qp.get("pa_lager") == "1", qp.get("tilbud") == "1"

    all_products = catalog.list_products()
    results = catalog.filter_products(all_products, q, category, min_price, max_price, in_stock, on_sale, sort)
    return render(
        request, "products.html", products=results, total=len(all_products), q=q, category=category,
        min_price=min_price, max_price=max_price, in_stock=in_stock, on_sale=on_sale, sort=sort,
        sorts=catalog.SORTS, wishlist=_wishlist_ids(current_user(request)),
    )


@router.get("/kategori/{slug}")
def category_redirect(slug: str):
    return RedirectResponse(f"/produkter?kategori={slug}", status_code=307)


@router.get("/produkt/{slug}")
def product_detail(request: Request, slug: str):
    product = catalog.get_product(slug)
    if product is None:
        return render(request, "error.html", status_code=404, title="Fant ikke produktet",
                      message="Produktet finnes ikke lenger, eller lenken er feil.")
    user = current_user(request)
    return render(
        request, "product.html", product=product, reviews=catalog.get_reviews(product["id"]),
        related=catalog.related_products(product), wishlist=_wishlist_ids(user),
        first_available=next((v for v in product["variants"] if v["stock"] > 0), None),
    )


@router.get("/info/{slug}")
def info_page(request: Request, slug: str):
    rendered = docs.render_doc(slug)
    if rendered is None:
        return render(request, "error.html", status_code=404, title="Fant ikke siden",
                      message="Denne infosiden finnes ikke.")
    title, html = rendered
    return render(request, "doc.html", title=title, content=html, slug=slug)


@router.get("/bilde/produkt/{product_id}.svg")
def product_image(product_id: int):
    product = catalog.get_product_by_id(product_id)
    if product is None:
        return Response(status_code=404)
    return Response(placeholder_svg(product["image_color"], product["category"]), media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=3600"})
