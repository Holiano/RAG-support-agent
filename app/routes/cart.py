"""Handlekurv: legg til, endre antall, fjern, rabattkode og fraktvalg."""
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from .. import cart as cart_svc
from ..auth import safe_next
from ..db import query_one
from ..pricing import SHIPPING_METHODS
from ..templating import flash, render

router = APIRouter()


def _back_to_cart() -> RedirectResponse:
    return RedirectResponse("/handlekurv", status_code=303)


@router.get("/handlekurv")
def view_cart(request: Request):
    summary = cart_svc.summarize(request)
    return render(request, "cart.html", cart=summary)


@router.post("/handlekurv/legg-til")
def add_to_cart(request: Request, sku: str = Form(""), quantity: int = Form(1), next: str = Form("")):
    variant = query_one("SELECT sku, stock FROM variants WHERE sku = ?", (sku,))
    if variant is None:
        flash(request, "Velg en variant før du legger varen i handlekurven.", "error")
        return RedirectResponse(safe_next(next, "/produkter"), status_code=303)
    if variant["stock"] <= 0:
        flash(request, "Denne varianten er utsolgt.", "error")
        return RedirectResponse(safe_next(next, "/produkter"), status_code=303)

    cart = cart_svc.get_cart(request)
    wanted = cart.get(sku, 0) + max(1, quantity)
    allowed = min(wanted, variant["stock"], cart_svc.MAX_QTY_PER_LINE)
    cart[sku] = allowed
    cart_svc.set_cart(request, cart)
    if allowed < wanted:
        flash(request, f"Vi har bare {allowed} igjen av denne varianten. Antallet er justert.", "info")
    else:
        flash(request, "Varen er lagt i handlekurven.", "success")
    return _back_to_cart()


@router.post("/handlekurv/oppdater")
def update_cart(request: Request, sku: str = Form(...), quantity: int = Form(...)):
    cart = cart_svc.get_cart(request)
    if sku in cart:
        if quantity <= 0:
            del cart[sku]
        else:
            variant = query_one("SELECT stock FROM variants WHERE sku = ?", (sku,))
            limit = min(variant["stock"] if variant else 0, cart_svc.MAX_QTY_PER_LINE)
            cart[sku] = max(1, min(quantity, limit)) if limit else cart[sku]
            if quantity > limit:
                flash(request, f"Du kan ikke bestille mer enn {limit} av denne varianten.", "info")
        cart_svc.set_cart(request, cart)
    return _back_to_cart()


@router.post("/handlekurv/fjern")
def remove_from_cart(request: Request, sku: str = Form(...)):
    cart = cart_svc.get_cart(request)
    cart.pop(sku, None)
    cart_svc.set_cart(request, cart)
    return _back_to_cart()


@router.post("/handlekurv/rabattkode")
def apply_code(request: Request, code: str = Form(""), action: str = Form("apply")):
    if action == "remove":
        request.session.pop("discount_code", None)
        flash(request, "Rabattkoden er fjernet.", "info")
        return _back_to_cart()

    code = code.strip().upper()
    if not code:
        return _back_to_cart()
    row = cart_svc.get_code(code)
    if row is None:
        flash(request, f"Vi finner ikke rabattkoden {code}.", "error")
        return _back_to_cart()
    request.session["discount_code"] = code
    summary = cart_svc.summarize(request)
    if summary["code_error"]:
        request.session.pop("discount_code", None)
        flash(request, summary["code_error"], "error")
    else:
        flash(request, f"Rabattkoden {code} er lagt til.", "success")
    return _back_to_cart()


@router.post("/handlekurv/frakt")
def choose_shipping(request: Request, method: str = Form(...)):
    if method in SHIPPING_METHODS:
        request.session["shipping_method"] = method
    return _back_to_cart()
