from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from database import Base, get_db
from models import Account, Antenna
from portal_client import SessionExpired


def _seed(db):
    usd = Account(account_number="ACC-USD", account_name="Juan", client_name="Juan",
                  currency_code="USD", region_code="VE", status="Active",
                  is_billing_suspended=True, balance_due=50.0,
                  next_due_date=datetime(2026, 11, 2))
    uyu = Account(account_number="ACC-UYU", account_name="Juan", client_name="Juan",
                  currency_code="UYU", region_code="UY", status="Active",
                  is_billing_suspended=False, balance_due=1000.0,
                  next_due_date=datetime(2026, 11, 5))
    db.add_all([usd, uyu])
    db.flush()
    db.add(Antenna(kit_number="KIT4M001", account_id=usd.id, model="Mini",
                   service_line_number="SL-1",
                   plan="Residencial", data_total_gb=42.0, data_cycle_gb=6.0,
                   active=True, is_suspended=False,
                   activation_date=datetime(2026, 1, 1)))
    db.add(Antenna(kit_number="KIT400651113", account_id=uyu.id, model="Standard V4",
                   service_line_number="SL-2",
                   plan="Residencial", data_total_gb=None, data_cycle_gb=None,
                   active=False, is_suspended=True))
    db.commit()


@pytest.fixture
def seeded_client():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # una sola conexión: la DB en memoria no se pierde entre hilos
    )
    Base.metadata.create_all(eng)
    TestSession = sessionmaker(bind=eng)
    db = TestSession()
    _seed(db)
    db.close()

    def override():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    main.app.dependency_overrides[get_db] = override
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def test_clients_grouped_and_mixed_currency_not_summed(seeded_client):
    body = seeded_client.get("/api/v1/clientes").json()
    assert len(body) == 1
    c = body[0]
    assert c["client_name"] == "Juan"
    assert c["is_suspended"] is True                 # cuenta suspendida ⇒ grupo marcado
    assert set(c["currencies"]) == {"USD", "UYU"}     # por cuenta; nunca un total sumado
    assert "total" not in c
    assert c["accounts"][0]["antennas"][0]["model"] == "Mini"
    assert c["accounts"][0]["antennas"][0]["service_line_number"] == "SL-1"


def test_sync_status_reports_no_session(seeded_client, monkeypatch):
    monkeypatch.setattr("main.session_store.has_session", lambda: False)
    body = seeded_client.get("/api/v1/sync-status").json()
    assert body["has_session"] is False


def test_same_client_name_keeps_accounts_separate(seeded_client):
    body = seeded_client.get("/api/v1/clientes").json()
    assert len(body[0]["accounts"]) == 2       # no se fusionan las cuentas


def test_manual_sync_requires_session(seeded_client, monkeypatch):
    monkeypatch.setattr("main.session_store.load", lambda *a, **k: {})
    assert seeded_client.post("/api/v1/sync").status_code == 409


async def _session_expired(*args, **kwargs):
    raise SessionExpired("401")


def test_manual_sync_expired_session_returns_409(seeded_client, monkeypatch):
    """Cookie guardada pero vencida: 409 para que el panel pida pegar una nueva."""
    monkeypatch.setattr("main.session_store.load", lambda *a, **k: {"a": "b"})
    monkeypatch.setattr("main.sync_once", _session_expired)
    assert seeded_client.post("/api/v1/sync").status_code == 409


def test_antenna_transferable_after_90_days(seeded_client):
    body = seeded_client.get("/api/v1/clientes").json()
    antennas = [t for a in body[0]["accounts"] for t in a["antennas"]]
    mini = next(t for t in antennas if t["kit_number"] == "KIT4M001")
    otro = next(t for t in antennas if t["kit_number"] == "KIT400651113")
    assert mini["transferable"] is True          # activada hace >90 días
    assert otro["transferable"] is False         # sin fecha de activación


def test_rename_antenna_sets_custom_name(seeded_client):
    r = seeded_client.patch("/api/v1/antennas/KIT4M001", json={"custom_name": "nodo lagunilla"})
    assert r.status_code == 200
    assert r.json()["custom_name"] == "nodo lagunilla"
    assert seeded_client.patch("/api/v1/antennas/KITX", json={"custom_name": "x"}).status_code == 404


def test_upsert_gestion_computes_margin(seeded_client):
    r = seeded_client.put(
        "/api/v1/gestiones",
        json={"client_name": "Juan", "is_administered": True, "is_paid_by_us": True,
              "cost": 60, "price": 120, "currency": "USD"},
    )
    assert r.status_code == 200
    assert r.json()["margin"] == 60
    body = seeded_client.get("/api/v1/clientes").json()
    assert body[0]["gestion"]["price"] == 120
    # Actualizar el mismo cliente no duplica: sigue existiendo una sola gestión.
    seeded_client.put("/api/v1/gestiones", json={"client_name": "Juan", "cost": 70, "price": 120})
    body = seeded_client.get("/api/v1/clientes").json()
    assert body[0]["gestion"]["margin"] == 50
