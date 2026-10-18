"""Autenticación del panel.

Se pega la cookie de sesión de starlink.com y se guarda CIFRADA en disco
(``session_store``). Esa cookie abre todas las cuentas del lote.
"""
import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

import session_store

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class CookieLoginRequest(BaseModel):
    cookie: str


def parse_cookies(raw: str) -> dict[str, str]:
    """Convierte el string de cookies del navegador ('k=v; k=v') en un dict."""
    cookies: dict[str, str] = {}
    for part in (raw or "").split(";"):
        name, _, value = part.partition("=")
        name = name.strip()
        if name:
            cookies[name] = value.strip()
    return cookies


def require_ingest_token(x_ingest_token: str | None = Header(default=None)) -> None:
    """La cookie de Starlink sólo la sube la extensión (token). Sin INGEST_TOKEN (dev), abierto."""
    expected = os.getenv("INGEST_TOKEN")
    if expected and not hmac.compare_digest(x_ingest_token or "", expected):
        raise HTTPException(status_code=401, detail="Token de ingesta inválido")


@router.post("/login")
async def login(body: CookieLoginRequest, _: None = Depends(require_ingest_token)):
    cookies = parse_cookies(body.cookie)
    if not cookies:
        raise HTTPException(status_code=400, detail="Cookie vacía")
    if not any(cookies.values()):
        # Un solo "x=" de prueba llega como dict no vacío y pisaría la sesión
        # real guardada. Ninguna cookie real de Starlink viene sin valor.
        raise HTTPException(status_code=400, detail="Cookies sin valor: ¿copiaste bien la cookie de starlink.com?")
    session_store.save(cookies)
    return {"authenticated": True}


@router.get("/status")
async def status():
    return {"authenticated": session_store.has_session()}


@router.post("/logout")
async def logout():
    session_store.clear()
    return {"authenticated": False, "message": "Sesión cerrada"}


def get_cookies() -> dict[str, str]:
    """Compatibilidad: delega en el almacén cifrado."""
    return session_store.load()
