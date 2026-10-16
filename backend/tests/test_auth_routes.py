import pytest
from fastapi.testclient import TestClient

import main

SECRET = "SUPERSECRETTOKENVALUE"


@pytest.fixture
def client():
    return TestClient(main.app)


def test_login_saves_cookie_encrypted(client, tmp_path, monkeypatch):
    monkeypatch.setattr("session_store.SESSION_FILE", tmp_path / "s.enc")
    monkeypatch.setattr("session_store.KEY_FILE", tmp_path / "k.key")
    r = client.post(
        "/api/v1/auth/login",
        json={"cookie": f"Starlink.Com.Sso={SECRET}; starlink.com.account_number=ACC-1"},
    )
    assert r.json()["authenticated"] is True
    assert client.get("/api/v1/auth/status").json()["authenticated"] is True
    assert SECRET.encode() not in (tmp_path / "s.enc").read_bytes()  # cifrado, no texto plano


def test_logout_clears(client, tmp_path, monkeypatch):
    monkeypatch.setattr("session_store.SESSION_FILE", tmp_path / "s.enc")
    monkeypatch.setattr("session_store.KEY_FILE", tmp_path / "k.key")
    client.post("/api/v1/auth/login", json={"cookie": "a=b"})
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/status").json()["authenticated"] is False
