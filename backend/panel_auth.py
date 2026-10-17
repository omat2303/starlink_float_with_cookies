"""Puerta de entrada del panel: login de OG con contraseña.

Sin dependencias nuevas: scrypt (stdlib) para la contraseña y HMAC-SHA256 para
la sesión firmada. En producción las variables son obligatorias y el backend no
arranca sin ellas (ver ``config.startup_check``).

El token es autocontenido (``sub:exp`` firmado) para no mantener estado en BD;
``sub`` es la costura por la que entra el multi-tenant (cada invitado su ``sub``).
"""
import base64
import hashlib
import hmac
import os
import secrets
import time

from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel

import session_store
from auth_routes import parse_cookies

router = APIRouter(prefix="/api/v1/panel", tags=["panel"])

COOKIE_NAME = "sp_session"
SESSION_TTL = 30 * 24 * 3600  # 30 días
_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}


def _auth_disabled() -> bool:
    return os.getenv("PANEL_AUTH_DISABLED", "false").lower() == "true"


def _is_prod() -> bool:
    return os.getenv("APP_ENV", "dev").lower() == "production"


# ----- contraseña (scrypt) -------------------------------------------------

def hash_password(password: str) -> str:
    """Devuelve ``scrypt$<salt_b64>$<hash_b64>`` (lo que va en PANEL_PASSWORD_HASH)."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return "scrypt${}${}".format(
        base64.b64encode(salt).decode(), base64.b64encode(digest).decode()
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_b64, hash_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except (ValueError, TypeError):
        return False
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return hmac.compare_digest(digest, expected)


# ----- sesión firmada (HMAC) ----------------------------------------------

def _secret() -> bytes:
    raw = os.getenv("PANEL_SESSION_SECRET", "")
    if not raw:
        raise HTTPException(status_code=503, detail="Panel sin secreto de sesión configurado")
    return raw.encode()


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_token(sub: str = "og", ttl: int = SESSION_TTL) -> str:
    payload = f"{sub}:{int(time.time()) + ttl}".encode()
    sig = hmac.new(_secret(), payload, hashlib.sha256).digest()
    return f"{_b64e(payload)}.{_b64e(sig)}"


def read_token(token: str) -> str | None:
    """Devuelve el ``sub`` si la firma es válida y no ha vencido; si no, ``None``."""
    try:
        payload_b64, sig_b64 = token.split(".")
        payload = _b64d(payload_b64)
        sig = _b64d(sig_b64)
        if not hmac.compare_digest(sig, hmac.new(_secret(), payload, hashlib.sha256).digest()):
            return None
        sub, _, exp = payload.decode().partition(":")
        if int(exp) < time.time():
            return None
        return sub or None
    except (ValueError, TypeError, UnicodeDecodeError):
        return None


# ----- endpoints -----------------------------------------------------------

class PanelLogin(BaseModel):
    password: str


@router.post("/session")
def panel_login(body: PanelLogin, response: Response):
    stored = os.getenv("PANEL_PASSWORD_HASH", "")
    if not stored or not verify_password(body.password, stored):
        time.sleep(0.3)  # frena la fuerza bruta (además de limit_req en nginx)
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    response.set_cookie(
        COOKIE_NAME,
        make_token(),
        max_age=SESSION_TTL,
        httponly=True,
        secure=_is_prod(),
        samesite="lax",
        path="/",
    )
    return {"authenticated": True}


@router.get("/verify")
def panel_verify(sp_session: str | None = Cookie(default=None)):
    """Lo consulta nginx (auth_request) y el propio panel: 200 si hay sesión."""
    if _auth_disabled():
        if _is_prod():
            raise HTTPException(status_code=503, detail="Auth bypass disabled in production")
        return {"ok": True}
    if not sp_session or read_token(sp_session) is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    return {"ok": True}


@router.post("/logout", status_code=204)
def panel_logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")


class PanelCookie(BaseModel):
    cookie: str


@router.post("/cookie")
def panel_save_cookie(body: PanelCookie):
    """Guarda la cookie de Starlink pegada a mano en el panel (misma bóveda que la extensión).

    Vive en el router del panel para quedar detrás de ``auth_request`` en nginx: la
    ruta de la extensión (``/api/auth/login``) exige ``X-Ingest-Token``, y el
    navegador no puede llevar ese token sin publicarlo.
    """
    cookies = parse_cookies(body.cookie)
    if not cookies:
        raise HTTPException(status_code=400, detail="Cookie vacía")
    session_store.save(cookies)
    return {"authenticated": True}
