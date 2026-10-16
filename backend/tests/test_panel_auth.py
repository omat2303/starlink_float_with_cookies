import main
import panel_auth
from fastapi.testclient import TestClient


def test_password_hash_roundtrip():
    stored = panel_auth.hash_password("s3creta")
    assert stored.startswith("scrypt$")
    assert panel_auth.verify_password("s3creta", stored)
    assert not panel_auth.verify_password("otra", stored)
    assert not panel_auth.verify_password("s3creta", "basura")


def test_token_roundtrip_tamper_and_expiry(monkeypatch):
    monkeypatch.setenv("PANEL_SESSION_SECRET", "k" * 32)
    tok = panel_auth.make_token()
    assert panel_auth.read_token(tok) == "og"
    assert panel_auth.read_token(tok[:-2] + "aa") is None          # firma rota
    assert panel_auth.read_token(panel_auth.make_token(ttl=-1)) is None  # vencido
    assert panel_auth.read_token("no-es-un-token") is None


def test_login_sets_session_cookie(monkeypatch):
    monkeypatch.setenv("PANEL_SESSION_SECRET", "k" * 32)
    monkeypatch.setenv("PANEL_PASSWORD_HASH", panel_auth.hash_password("s3creta"))
    client = TestClient(main.app)

    assert client.get("/api/v1/panel/verify").status_code == 401
    assert client.post("/api/v1/panel/session", json={"password": "mala"}).status_code == 401

    r = client.post("/api/v1/panel/session", json={"password": "s3creta"})
    assert r.status_code == 200
    assert r.cookies.get(panel_auth.COOKIE_NAME)
    assert client.get("/api/v1/panel/verify").status_code == 200
