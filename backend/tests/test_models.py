from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Account, Antenna, ClientAlias


def make_db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def test_account_and_antenna_roundtrip():
    db = make_db()
    a = Account(account_number="ACC-1", account_name="Juan", client_name="Juan",
                region_code="VE", currency_code="USD", is_billing_suspended=False,
                balance_due=None, status="Active")
    db.add(a)
    db.flush()
    db.add(Antenna(kit_number="KIT4M001", account_id=a.id, service_line_number="SL-1",
                   nickname="Casa", model="Mini", plan="Residencial", active=True,
                   is_suspended=False, data_cycle_gb=6.0, data_limit_gb=100.0,
                   data_total_gb=42.0))
    db.commit()
    got = db.query(Antenna).one()
    assert got.model == "Mini" and got.data_total_gb == 42.0


def test_client_alias_unique():
    db = make_db()
    db.add(ClientAlias(account_number="ACC-1", client_name="Cliente Real"))
    db.commit()
    assert db.query(ClientAlias).one().client_name == "Cliente Real"
