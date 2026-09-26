"""Innlogging, Mine sider, ordresporing og ønskeliste."""
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from .. import auth, catalog, orders
from ..db import execute, query_all, query_one
from ..templating import flash, render

router = APIRouter()


@router.get("/logg-inn")
def login_page(request: Request, next: str = "/mine-sider"):
    if auth.current_user(request):
        return RedirectResponse("/mine-sider", status_code=303)
    demo_users = query_all("SELECT name, email FROM customers ORDER BY id")
    return render(request, "login.html", next=auth.safe_next(next, "/mine-sider"), demo_users=demo_users,
                  error=None, email="")


@router.post("/logg-inn")
def login(request: Request, email: str = Form(""), password: str = Form(""), next: str = Form("/mine-sider")):
    customer = auth.authenticate(email, password)
    if customer is None:
        demo_users = query_all("SELECT name, email FROM customers ORDER BY id")
        return render(request, "login.html", status_code=401, next=auth.safe_next(next, "/mine-sider"),
                      demo_users=demo_users, error="Feil e-post eller passord.", email=email)
    request.session["user_id"] = customer["id"]
    flash(request, f"Velkommen tilbake, {customer['name'].split()[0]}!", "success")
    return RedirectResponse(auth.safe_next(next, "/mine-sider"), status_code=303)


@router.post("/logg-ut")
def logout(request: Request):
    request.session.pop("user_id", None)
    flash(request, "Du er logget ut.", "info")
    return RedirectResponse("/", status_code=303)


@router.get("/mine-sider")
def my_pages(request: Request):
    user = auth.current_user(request)
    if not user:
        return auth.login_redirect(request)
    return render(request, "account.html", orders=orders.orders_for_customer(user["id"]))


@router.get("/mine-sider/ordre/{order_number}")
def my_order(request: Request, order_number: str):
    user = auth.current_user(request)
    if not user:
        return auth.login_redirect(request)
    order = orders.get_order(order_number)
    if not order or order["customer_id"] != user["id"]:
        return render(request, "error.html", status_code=404, title="Fant ikke ordren",
                      message="Ordren finnes ikke på din konto.")
    return render(request, "order_detail.html", order=order)


# ---- Ordresporing uten innlogging ----

@router.get("/sporing")
def tracking_page(request: Request):
    return render(request, "tracking.html", order=None, searched=False, order_number="", email="")


@router.post("/sporing")
def tracking_lookup(request: Request, order_number: str = Form(""), email: str = Form("")):
    order = orders.find_for_tracking(order_number, email)
    return render(request, "tracking.html", status_code=200 if order else 404, order=order, searched=True,
                  order_number=order_number, email=email)


# ---- Ønskeliste ----

@router.get("/onskeliste")
def wishlist_page(request: Request):
    user = auth.current_user(request)
    if not user:
        return auth.login_redirect(request)
    ids = [r["product_id"] for r in query_all(
        "SELECT product_id FROM wishlist WHERE customer_id = ? ORDER BY added_at DESC", (user["id"],))]
    by_id = {p["id"]: p for p in catalog.list_products()}
    return render(request, "wishlist.html", products=[by_id[i] for i in ids if i in by_id], wishlist=set(ids))


@router.post("/onskeliste/{product_id}")
def toggle_wishlist(request: Request, product_id: int, next: str = Form("")):
    user = auth.current_user(request)
    if not user:
        flash(request, "Logg inn for å bruke ønskelisten.", "info")
        return RedirectResponse(f"/logg-inn?next={auth.safe_next(next, '/onskeliste')}", status_code=303)
    if query_one("SELECT 1 FROM products WHERE id = ?", (product_id,)) is None:
        return RedirectResponse("/produkter", status_code=303)
    removed = execute("DELETE FROM wishlist WHERE customer_id = ? AND product_id = ?", (user["id"], product_id))
    if removed:
        flash(request, "Fjernet fra ønskelisten.", "info")
    else:
        execute("INSERT INTO wishlist (customer_id, product_id, added_at) VALUES (?,?,datetime('now'))",
                (user["id"], product_id))
        flash(request, "Lagt til i ønskelisten.", "success")
    return RedirectResponse(auth.safe_next(next, "/onskeliste"), status_code=303)
