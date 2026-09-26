"""Vindhamar Friluft: demo-nettbutikk. Start: uvicorn app.main:app --reload"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from . import db
from .routes import account, api, cart, checkout, pages
from .templating import render

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not db.DB_PATH.exists():
        raise RuntimeError(f"Fant ikke databasen ({db.DB_PATH}). Kjør 'python seed.py' først.")
    yield


app = FastAPI(title="Vindhamar Friluft (demobutikk)", lifespan=lifespan)
# Sesjonscookie uten utløpsdato: handlekurven og innloggingen slettes når nettleseren lukkes (jf. personvern.md).
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", "demo-secret-endre-meg"),
                   max_age=None, same_site="lax")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

for module in (pages, cart, checkout, account, api):
    app.include_router(module.router)


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    if exc.status_code == 404:
        return render(request, "error.html", status_code=404, title="Fant ikke siden",
                      message="Siden du leter etter finnes ikke.")
    return render(request, "error.html", status_code=exc.status_code, title="Noe gikk galt", message=str(exc.detail))
