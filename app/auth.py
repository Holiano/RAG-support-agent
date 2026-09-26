"""Innlogging med demobrukere (passord hashet med PBKDF2)."""
import hashlib
import hmac

from fastapi import Request
from fastapi.responses import RedirectResponse

from .db import query_one


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return hmac.compare_digest(check, digest)


def authenticate(email: str, password: str):
    row = query_one("SELECT * FROM customers WHERE lower(email) = ?", (email.strip().lower(),))
    if row and verify_password(password, row["password_hash"]):
        return row
    return None


def current_user(request: Request) -> dict | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    row = query_one("SELECT id, name, email, street, postal_code, city FROM customers WHERE id = ?", (user_id,))
    if row is None:
        request.session.pop("user_id", None)
        return None
    return dict(row)


def safe_next(target: str | None, default: str = "/") -> str:
    """Tillat bare interne stier som redirect-mål."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return default


def login_redirect(request: Request) -> RedirectResponse:
    return RedirectResponse(f"/logg-inn?next={request.url.path}", status_code=303)
