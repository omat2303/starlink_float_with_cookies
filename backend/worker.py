"""Sincronización periódica del portal Starlink hacia la base de datos.

``sync_once`` recibe el cliente y la sesión de DB inyectados para poder testearlo
sin red. ``start_sync_loop`` corre cada 2 h; un fallo de red no mata el loop.
"""
import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

import session_store
from database import SessionLocal
from kit_models import kit_model
from models import Account, Antenna, ClientAlias
from portal_client import PortalClient

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 7200  # 2 h

_UNKNOWN_USAGE = {"unknown": True, "cycle_gb": None, "limit_gb": None, "total_gb": None}


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def client_name_for(account_name: str, alias: ClientAlias | None) -> str:
    """Nombre del cliente: el alias manual manda sobre el nombre de la cuenta."""
    return alias.client_name if alias else account_name


async def sync_once(client, db: Session) -> dict:
    """Un ciclo: lee todas las cuentas del portal y hace upsert en la DB."""
    stats = {"accounts": 0, "antennas": 0, "errors": 0}

    for acc_data in await client.accounts():
        number = acc_data["account_number"]
        alias = db.query(ClientAlias).filter(ClientAlias.account_number == number).first()
        account = db.query(Account).filter(Account.account_number == number).first()
        if account is None:
            account = Account(account_number=number)
            db.add(account)

        account.account_name = acc_data.get("account_name") or number
        account.client_name = client_name_for(account.account_name, alias)
        account.region_code = acc_data.get("region")
        account.currency_code = acc_data.get("currency")
        account.is_billing_suspended = bool(acc_data.get("is_billing_suspended"))
        account.next_due_date = _parse_dt(acc_data.get("next_due_date"))
        account.status = acc_data.get("status") or "active"
        db.flush()
        stats["accounts"] += 1

        try:
            lines = await client.service_lines(number)
        except Exception as exc:  # noqa: BLE001 - una cuenta mala no debe parar el sync
            logger.warning("service-lines %s falló: %s", number, exc)
            stats["errors"] += 1
            continue

        try:
            balance = await client.balance(number)
        except Exception as exc:  # noqa: BLE001
            logger.warning("saldo %s falló: %s", number, exc)
            balance = None
            stats["errors"] += 1
        account.balance_due = balance[0] if balance else None

        for line in lines:
            try:
                usage = await client.usage(number, line["service_line_number"])
            except Exception as exc:  # noqa: BLE001
                logger.warning("consumo %s/%s falló: %s", number, line["service_line_number"], exc)
                usage = _UNKNOWN_USAGE
            if usage.get("unknown"):
                stats["errors"] += 1

            for terminal in line.get("terminals") or []:
                kit = terminal["kit_number"]
                antenna = db.query(Antenna).filter(Antenna.kit_number == kit).first()
                if antenna is None:
                    antenna = Antenna(kit_number=kit)
                    db.add(antenna)

                antenna.account_id = account.id
                antenna.service_line_number = line["service_line_number"]
                antenna.nickname = line.get("nickname")
                antenna.model = kit_model(kit)
                antenna.plan = line.get("plan")
                antenna.active = bool(terminal.get("active"))
                antenna.is_suspended = bool(line.get("is_suspended"))
                antenna.is_standby = bool(line.get("is_standby")) if line.get("is_standby") is not None else None
                try:
                    st = line.get("subscription_status")
                    antenna.subscription_status = int(st) if st is not None else None
                except Exception:
                    antenna.subscription_status = None
                # Activación real: el ``activeFrom`` del primer ciclo con consumo
                # (el portal no la expone en otro campo). Fallback: primer ciclo,
                # luego startDate. Nos quedamos con la más antigua.
                cycles = usage.get("cycles") or []
                actives = [c["active_from"] for c in cycles if c.get("active_from")]
                if actives:
                    first_used = _parse_dt(min(actives))
                else:
                    first_used = _parse_dt(
                        min((c["start"] for c in cycles if c.get("start")), default=None)
                    )
                stamps = [d for d in (first_used, _parse_dt(line.get("activation_date"))) if d]
                antenna.activation_date = (
                    min(stamps, key=lambda d: d.replace(tzinfo=None)) if stamps else None
                )
                antenna.cycles_json = json.dumps(cycles, ensure_ascii=False)
                antenna.data_cycle_gb = usage.get("cycle_gb")
                antenna.data_limit_gb = usage.get("limit_gb")
                antenna.data_total_gb = usage.get("total_gb")
                antenna.address = line.get("address")
                antenna.latitude = line.get("latitude")
                antenna.longitude = line.get("longitude")
                antenna.last_connected = _parse_dt(terminal.get("last_connected"))
                stats["antennas"] += 1

        # Commit por cuenta: sin esto el sync mantiene el lock de SQLite minutos y
        # bloquea cualquier edición (nombre propio, gestión) desde el panel.
        db.commit()

    db.commit()  # por si la última cuenta salteó el commit (fallo de service-lines)
    return stats


async def start_sync_loop() -> None:
    """Sincroniza cada ``SYNC_INTERVAL_SECONDS`` hasta que el proceso pare."""
    while True:
        db = SessionLocal()
        try:
            cookies = session_store.load()
            if cookies:
                client = PortalClient(cookies)
                try:
                    logger.info("sync: %s", await sync_once(client, db))
                finally:
                    await client.aclose()
            else:
                logger.info("sync: sin sesión guardada")
        except Exception:  # noqa: BLE001 - el loop nunca debe morir
            logger.exception("sync falló")
        finally:
            db.close()
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
