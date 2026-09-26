"""Kasse og ordrebekreftelse. Ingen ekte betaling."""
import re

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from .. import cart as cart_svc
from .. import orders
from ..auth import current_user
from ..pricing import SHIPPING_METHODS, delivery_estimate, is_blocked_postal, region_for_postal
from ..templating import flash, render

router = APIRouter()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _form_defaults(user: dict | None) -> dict:
    if not user:
        return {"name": "", "email": "", "street": "", "postal_code": "", "city": ""}
    return {k: user[k] for k in ("name", "email", "street", "postal_code", "city")}


@router.get("/kasse")
def checkout_page(request: Request):
    summary = cart_svc.summarize(request)
    if not summary["lines"]:
        flash(request, "Handlekurven er tom.", "info")
        return RedirectResponse("/handlekurv", status_code=303)
    return render(request, "checkout.html", cart=summary, form=_form_defaults(current_user(request)), errors=[])


@router.post("/kasse")
def place_order(request: Request, name: str = Form(""), email: str = Form(""), street: str = Form(""),
                postal_code: str = Form(""), city: str = Form(""), method: str = Form("hjemlevering")):
    summary = cart_svc.summarize(request)
    if not summary["lines"]:
        return RedirectResponse("/handlekurv", status_code=303)

    form = {"name": name.strip(), "email": email.strip(), "street": street.strip(),
            "postal_code": postal_code.strip(), "city": city.strip()}
    errors = []
    if not form["name"]:
        errors.append("Fyll inn navn.")
    if not EMAIL_RE.match(form["email"]):
        errors.append("Fyll inn en gyldig e-postadresse.")
    if not form["street"]:
        errors.append("Fyll inn gateadresse.")
    if not re.fullmatch(r"\d{4}", form["postal_code"]):
        errors.append("Postnummer må være fire siffer.")
    elif is_blocked_postal(form["postal_code"]):
        errors.append("Vi leverer ikke til Svalbard og Jan Mayen via nettbutikken. Kontakt kundeservice for et tilbud.")
    if not form["city"]:
        errors.append("Fyll inn poststed.")
    if method not in SHIPPING_METHODS:
        errors.append("Velg en fraktmetode.")
    else:
        request.session["shipping_method"] = method
        summary = cart_svc.summarize(request)
    for l in summary["stock_problems"]:
        errors.append(f"{l['name']} ({l['variant_label']}): du har {l['quantity']} i handlekurven, men vi har bare {l['stock']} på lager.")

    if errors:
        return render(request, "checkout.html", status_code=422, cart=summary, form=form, errors=errors)

    user = current_user(request)
    code = summary["code_str"] if summary["code"] and not summary["code_error"] else None
    try:
        number = orders.create_order(
            customer_id=user["id"] if user else None, email=form["email"], address=form, method=method,
            lines=summary["lines"], totals=summary, code=code)
    except orders.OrderError as exc:
        return render(request, "checkout.html", status_code=409, cart=summary, form=form, errors=[str(exc)])

    request.session["cart"] = {}
    request.session.pop("discount_code", None)
    request.session["last_order"] = number
    return RedirectResponse(f"/bestilling/{number}", status_code=303)


@router.get("/bestilling/{order_number}")
def confirmation(request: Request, order_number: str):
    user = current_user(request)
    order = orders.get_order(order_number)
    allowed = order and (request.session.get("last_order") == order_number
                         or (user and order["customer_id"] == user["id"]))
    if not allowed:
        return render(request, "error.html", status_code=404, title="Fant ikke bestillingen",
                      message="Vi finner ikke denne bestillingen. Bruk ordresporing med ordrenummer og e-post.")
    estimate = delivery_estimate(order["ship_postal_code"], order["shipping_method"])
    return render(request, "confirmation.html", order=order, estimate=estimate,
                  region=region_for_postal(order["ship_postal_code"]))
