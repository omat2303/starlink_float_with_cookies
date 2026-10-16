"""StarPanel: panel web del lote Starlink, agrupado por cliente.

Sólo lectura salvo ``POST /sync`` (que consulta el portal y actualiza la DB).
Las cuentas se agrupan por ``client_name``; nunca se suman montos de monedas
distintas.
"""
import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

import session_store
from auth_routes import router as auth_router
from config import startup_check
from database import Base, engine, ensure_schema, get_db
from models import Account, Antenna, Gestion, SyncState
from panel_auth import router as panel_router
from portal_client import PortalClient, SessionExpired
from worker import start_sync_loop, sync_once

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_check()  # en producción, falla al arrancar si falta un secreto
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    task = asyncio.create_task(start_sync_loop())
    logger.info("StarPanel listo")
    yield
    task.cancel()
    logger.info("StarPanel detenido")


app = FastAPI(title="StarPanel API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("PANEL_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(panel_router)


# ---------------------------------------------------------------------- #
#  Schemas
# ---------------------------------------------------------------------- #

class AntennaOut(BaseModel):
    kit_number: str
    service_line_number: str | None
    nickname: str | None  # sobrenombre (ej. nodo lagunilla)
    custom_name: str | None = None  # nombre propio, paralelo a Starlink
    model: str
    plan: str | None
    active: bool  # antena encendida/conectada
    is_suspended: bool  # suscripción suspendida/pausada
    is_standby: bool | None = None  # standby/pausada
    subscription_status: int | None = None  # estado de la suscripción
    activation_date: datetime | None = None
    transferable: bool = False  # activa hace >90 días
    cycles: list[dict] = []
    data_cycle_gb: float | None
    data_limit_gb: float | None
    data_total_gb: float | None
    address: str | None
    latitude: float | None
    longitude: float | None
    last_connected: datetime | None


class AccountOut(BaseModel):
    account_number: str
    account_name: str
    currency_code: str | None
    region_code: str | None = None
    balance_due: float | None
    next_due_date: datetime | None
    is_billing_suspended: bool
    antennas: list[AntennaOut]


class GestionOut(BaseModel):
    is_administered: bool = True
    is_paid_by_us: bool = False
    cost: float | None = None
    price: float | None = None
    currency: str | None = None
    notes: str | None = None
    margin: float | None = None  # price - cost


class ClientOut(BaseModel):
    client_name: str
    is_suspended: bool
    currencies: list[str]
    next_due_date: datetime | None
    gestion: GestionOut
    accounts: list[AccountOut]


class SummaryOut(BaseModel):
    clientes: int
    cuentas: int
    antenas: int
    suspendidas: int
    por_vencer: int
    por_vencer_72h: int


class SyncStatusOut(BaseModel):
    has_session: bool
    last_sync: datetime | None
    accounts: int
    antennas: int


# ---------------------------------------------------------------------- #
#  Helpers
# ---------------------------------------------------------------------- #

def _lowest_due(accounts: list[Account]) -> datetime | None:
    dates = [a.next_due_date for a in accounts if a.next_due_date is not None]
    return min(dates) if dates else None


TRANSFERABLE_DAYS = 90


def _is_transferable(antenna: Antenna, now: datetime) -> bool:
    """>90 días de activada: candidata a transferible."""
    if antenna.activation_date is None:
        return False
    activated = antenna.activation_date.replace(tzinfo=None)
    return (now - activated).days > TRANSFERABLE_DAYS


def _cycles(antenna: Antenna) -> list[dict]:
    if not antenna.cycles_json:
        return []
    try:
        return json.loads(antenna.cycles_json)
    except (ValueError, TypeError):
        return []


def _to_antenna_out(antenna: Antenna, now: datetime) -> AntennaOut:
    return AntennaOut(
        kit_number=antenna.kit_number,
        service_line_number=antenna.service_line_number,
        nickname=antenna.nickname,
        custom_name=antenna.custom_name,
        model=antenna.model,
        plan=antenna.plan,
        active=antenna.active,
        is_suspended=antenna.is_suspended,
        is_standby=antenna.is_standby,
        subscription_status=antenna.subscription_status,
        activation_date=antenna.activation_date,
        transferable=_is_transferable(antenna, now),
        cycles=_cycles(antenna),
        data_cycle_gb=antenna.data_cycle_gb,
        data_limit_gb=antenna.data_limit_gb,
        data_total_gb=antenna.data_total_gb,
        address=antenna.address,
        latitude=antenna.latitude,
        longitude=antenna.longitude,
        last_connected=antenna.last_connected,
    )


def _to_account_out(account: Account, now: datetime) -> AccountOut:
    return AccountOut(
        account_number=account.account_number,
        account_name=account.account_name,
        currency_code=account.currency_code,
        region_code=account.region_code,
        balance_due=account.balance_due,
        next_due_date=account.next_due_date,
        is_billing_suspended=account.is_billing_suspended,
        antennas=[
            _to_antenna_out(a, now)
            for a in sorted(account.antennas, key=lambda a: a.kit_number)
        ],
    )


def _gestion_out(gestion: Gestion | None) -> GestionOut:
    if gestion is None:
        return GestionOut()
    margin = (
        gestion.price - gestion.cost
        if gestion.price is not None and gestion.cost is not None
        else None
    )
    return GestionOut(
        is_administered=gestion.is_administered,
        is_paid_by_us=gestion.is_paid_by_us,
        cost=gestion.cost,
        price=gestion.price,
        currency=gestion.currency,
        notes=gestion.notes,
        margin=margin,
    )


# ---------------------------------------------------------------------- #
#  Endpoints
# ---------------------------------------------------------------------- #

@app.get("/api/v1/clientes", response_model=list[ClientOut])
def list_clients(db: Session = Depends(get_db)):
    """Todas las cuentas agrupadas por cliente (monedas por separado, sin total)."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    groups: dict[str, list[Account]] = {}
    for account in db.query(Account).order_by(Account.account_number).all():
        groups.setdefault(account.client_name, []).append(account)

    gestiones = {g.client_name: g for g in db.query(Gestion).all()}

    return [
        ClientOut(
            client_name=client_name,
            is_suspended=any(a.is_billing_suspended for a in accounts),
            currencies=sorted({a.currency_code for a in accounts if a.currency_code}),
            next_due_date=_lowest_due(accounts),
            gestion=_gestion_out(gestiones.get(client_name)),
            accounts=[_to_account_out(a, now) for a in accounts],
        )
        for client_name, accounts in sorted(groups.items())
    ]


@app.get("/api/v1/resumen", response_model=SummaryOut)
def summary(db: Session = Depends(get_db)):
    """Conteos para la tarjeta superior del panel."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    in_a_week = now + timedelta(days=7)
    in_72h = now + timedelta(hours=72)
    accounts = db.query(Account).all()
    por_vencer_72h = 0
    for a in accounts:
        if a.next_due_date is not None:
            d = a.next_due_date.replace(tzinfo=None)
            if d >= now and d <= in_72h:
                por_vencer_72h += 1
    return SummaryOut(
        clientes=len({a.client_name for a in accounts}),
        cuentas=len(accounts),
        antenas=db.query(Antenna).count(),
        suspendidas=sum(1 for a in accounts if a.is_billing_suspended),
        por_vencer=sum(
            1
            for a in accounts
            if a.next_due_date is not None and now <= a.next_due_date.replace(tzinfo=None) <= in_a_week
        ),
        por_vencer_72h=por_vencer_72h,
    )


class GestionIn(BaseModel):
    """Cuerpo para crear/editar la gestión de un cliente."""

    client_name: str
    is_administered: bool = True
    is_paid_by_us: bool = False
    cost: float | None = None
    price: float | None = None
    currency: str | None = None
    notes: str | None = None


class AntennaNameIn(BaseModel):
    """Cuerpo para renombrar una antena (nombre propio)."""

    custom_name: str | None = None


@app.put("/api/v1/gestiones", response_model=GestionOut)
def upsert_gestion(payload: GestionIn, db: Session = Depends(get_db)):
    """Crea o actualiza la gestión de un cliente (administración, pago, costo/precio)."""
    gestion = db.query(Gestion).filter(Gestion.client_name == payload.client_name).first()
    if gestion is None:
        gestion = Gestion(client_name=payload.client_name)
        db.add(gestion)
    gestion.is_administered = payload.is_administered
    gestion.is_paid_by_us = payload.is_paid_by_us
    gestion.cost = payload.cost
    gestion.price = payload.price
    gestion.currency = payload.currency
    gestion.notes = payload.notes
    db.commit()
    db.refresh(gestion)
    return _gestion_out(gestion)


@app.patch("/api/v1/antennas/{kit_number}", response_model=AntennaOut)
def rename_antenna(kit_number: str, payload: AntennaNameIn, db: Session = Depends(get_db)):
    """Renombra una antena (nombre propio, paralelo al apodo de Starlink)."""
    antenna = db.query(Antenna).filter(Antenna.kit_number == kit_number).first()
    if antenna is None:
        raise HTTPException(status_code=404, detail="Antena no encontrada")
    antenna.custom_name = (payload.custom_name or "").strip() or None
    db.commit()
    db.refresh(antenna)
    return _to_antenna_out(antenna, datetime.now(timezone.utc).replace(tzinfo=None))


@app.get("/api/v1/sync-status", response_model=SyncStatusOut)
def sync_status(db: Session = Depends(get_db)):
    """Estado de la sesión y de la última sincronización."""
    state = db.query(SyncState).first()
    return SyncStatusOut(
        has_session=session_store.has_session(),
        last_sync=state.last_sync if state else None,
        accounts=state.accounts if state else 0,
        antennas=state.antennas if state else 0,
    )


@app.post("/api/v1/sync")
async def trigger_sync(db: Session = Depends(get_db)):
    """Sincroniza ahora mismo contra el portal (requiere sesión guardada)."""
    cookies = session_store.load()
    if not cookies:
        raise HTTPException(
            status_code=409,
            detail="No hay sesión. Pega la cookie de starlink.com en el panel.",
        )

    client = PortalClient(cookies)
    try:
        stats = await sync_once(client, db)
    except SessionExpired as exc:
        # Cookie guardada pero vencida: que el panel pida pegar una nueva, no un 500.
        raise HTTPException(
            status_code=409,
            detail="Sesión de Starlink vencida. Vuelve a pegar la cookie.",
        ) from exc
    finally:
        await client.aclose()

    state = db.query(SyncState).first()
    if state is None:
        state = SyncState()
        db.add(state)
    state.last_sync = datetime.now(timezone.utc).replace(tzinfo=None)
    state.accounts = stats["accounts"]
    state.antennas = stats["antennas"]
    db.commit()
    return stats


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
