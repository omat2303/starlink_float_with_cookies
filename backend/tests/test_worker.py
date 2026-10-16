from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import worker
from database import Base
from models import Account, Antenna, ClientAlias


class FakePortal:
    def __init__(self, fail_usage=False):
        self.fail_usage = fail_usage

    async def accounts(self):
        return [dict(account_number="ACC-1", account_name="Juan", status="Active",
                     currency="USD", region="VE", is_billing_suspended=True,
                     next_due_date="2026-11-02T00:00:00Z")]

    async def service_lines(self, acc):
        return [dict(service_line_number="SL-1", nickname="Casa", plan="Residencial",
                     is_suspended=False, is_standby=False, address="Caracas",
                     latitude=10.4, longitude=-66.9,
                     activation_date="2026-01-01T00:00:00Z",
                     terminals=[dict(kit_number="KIT4M001", active=True,
                                     last_connected="2026-10-13T10:00:00Z")])]

    async def balance(self, acc):
        return (100.0, "USD")

    async def usage(self, acc, sl):
        return ({"unknown": True, "cycle_gb": None, "limit_gb": None, "total_gb": None}
                if self.fail_usage
                else {"cycle_gb": 6.0, "limit_gb": 100.0, "total_gb": 42.0,
                      "cycles": [{"start": "2026-10-01", "end": None, "gb": 6.0, "limit_gb": 100.0}]})

    async def aclose(self):
        pass


def make_db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


async def test_sync_creates_rows():
    db = make_db()
    stats = await worker.sync_once(FakePortal(), db)
    assert stats == {"accounts": 1, "antennas": 1, "errors": 0}
    a = db.query(Account).one()
    assert a.client_name == "Juan" and a.is_billing_suspended is True and a.balance_due == 100.0
    ant = db.query(Antenna).one()
    assert ant.model == "Mini" and ant.data_total_gb == 42.0
    assert ant.activation_date is not None                    # fecha de activación guardada
    assert '"gb": 6.0' in (ant.cycles_json or "")             # historial de ciclos guardado


async def test_sync_twice_updates_not_duplicates():
    db = make_db()
    await worker.sync_once(FakePortal(), db)
    await worker.sync_once(FakePortal(), db)
    assert db.query(Antenna).count() == 1


async def test_sync_preserves_custom_name():
    """El sync no debe pisar el nombre propio puesto a mano (campo paralelo a Starlink)."""
    db = make_db()
    await worker.sync_once(FakePortal(), db)
    db.query(Antenna).one().custom_name = "nodo lagunilla"
    db.commit()
    await worker.sync_once(FakePortal(), db)
    assert db.query(Antenna).one().custom_name == "nodo lagunilla"


async def test_unknown_usage_stored_as_null_and_counted():
    db = make_db()
    stats = await worker.sync_once(FakePortal(fail_usage=True), db)
    assert stats["errors"] == 1
    assert db.query(Antenna).one().data_total_gb is None


async def test_client_alias_overrides_name():
    db = make_db()
    db.add(ClientAlias(account_number="ACC-1", client_name="Cliente Real"))
    db.commit()
    await worker.sync_once(FakePortal(), db)
    assert db.query(Account).one().client_name == "Cliente Real"


class FakePortalLongHistory(FakePortal):
    """startDate = inicio del ciclo actual (nuevo); el historial arranca antes."""

    async def service_lines(self, acc):
        lines = await super().service_lines(acc)
        lines[0]["activation_date"] = "2026-10-01T00:00:00Z"
        return lines

    async def usage(self, acc, sl):
        return {
            "cycle_gb": 6.0, "limit_gb": 100.0, "total_gb": 42.0,
            "cycles": [
                {"start": "2026-03-01T00:00:00+00:00", "end": "2026-04-01T00:00:00+00:00",
                 "gb": 1.0, "limit_gb": 100.0},
                {"start": "2026-10-01T00:00:00+00:00", "end": None, "gb": 6.0, "limit_gb": 100.0},
            ],
        }


async def test_activation_uses_first_consumption_cycle():
    """Sin ``activeFrom``: cae al primer ciclo de consumo, no al ciclo actual."""
    db = make_db()
    await worker.sync_once(FakePortalLongHistory(), db)
    ant = db.query(Antenna).one()
    assert ant.activation_date is not None
    assert (ant.activation_date.year, ant.activation_date.month) == (2026, 3)


class FakePortalLandaeta(FakePortal):
    """Ciclos previos en 0 GB (ruido) y el primero con uso marca la activación."""

    async def service_lines(self, acc):
        lines = await super().service_lines(acc)
        lines[0]["activation_date"] = "2026-09-19T00:00:00Z"  # inicio del ciclo actual
        return lines

    async def usage(self, acc, sl):
        return {
            "cycle_gb": 45.25, "limit_gb": 100.0, "total_gb": 74.12,
            "cycles": [
                {"start": "2026-03-19T00:00:00+00:00", "end": "2026-06-19T00:00:00+00:00",
                 "gb": 0.0, "limit_gb": None, "active_from": None},
                {"start": "2026-06-19T00:00:00+00:00", "end": "2026-07-19T00:00:00+00:00",
                 "gb": 45.25, "limit_gb": None, "active_from": "2026-07-03T00:00:00+00:00"},
                {"start": "2026-07-19T00:00:00+00:00", "end": "2026-08-19T00:00:00+00:00",
                 "gb": 28.87, "limit_gb": None, "active_from": "2026-07-19T00:00:00+00:00"},
            ],
        }


async def test_activation_uses_idle_free_active_from():
    """La activación es el ``activeFrom`` del primer uso real, no el ciclo en 0."""
    db = make_db()
    await worker.sync_once(FakePortalLandaeta(), db)
    ant = db.query(Antenna).one()
    assert ant.activation_date is not None
    assert (ant.activation_date.year, ant.activation_date.month, ant.activation_date.day) == (
        2026, 7, 3,
    )
