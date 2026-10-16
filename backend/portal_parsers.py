"""Parsers de las respuestas REST del portal Starlink.

El portal envuelve casi todo en ``{"content": ...}``. Los parsers aceptan envuelto
y sin envolver para que un cambio de wrapper no rompa la sincronización completa.
"""
from typing import Any


def _content(payload: Any) -> Any:
    if isinstance(payload, dict) and "content" in payload:
        return payload["content"]
    return payload


def _items(payload: Any) -> list:
    """Lista de un payload: ``content`` puede ser la lista o un dict con ``results``."""
    content = _content(payload)
    if isinstance(content, dict):
        return content.get("results") or []
    return content or []


def _is_not_found(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("isValid") is False:
        return True
    for err in payload.get("errors") or []:
        if isinstance(err, dict) and "not_found" in str(err.get("errorMessage", "")).lower():
            return True
    return False


def parse_accounts(payload: Any) -> list[dict]:
    items = _content(payload) or []
    return [
        {
            "account_number": a.get("accountNumber"),
            "account_name": a.get("accountName"),
            "status": a.get("status"),
            "currency": a.get("currencyCode"),
            "region": a.get("regionCode"),
            "is_billing_suspended": bool(a.get("isBillingSuspended")),
            "next_due_date": a.get("nextDueDate"),
        }
        for a in items
    ]


def parse_service_lines(payload: Any) -> list[dict]:
    items = _items(payload)
    out = []
    for sl in items:
        sub = sl.get("subscription") or {}
        address = sl.get("serviceAddress") or {}
        geo = address.get("geoLocation") or {}
        terminals = [
            {
                "kit_number": t.get("serialNumber"),
                "active": bool(t.get("active")),
                "last_connected": t.get("lastConnected"),
            }
            for t in (sl.get("userTerminals") or [])
        ]
        first = terminals[0] if terminals else {}
        out.append(
            {
                "service_line_number": sl.get("serviceLineNumber"),
                "nickname": sl.get("nickname") or sl.get("displayName"),
                "plan": sub.get("productDescription"),
                "is_suspended": bool(sub.get("isSuspended")),
                "is_standby": bool(sub.get("isStandby")),
                "subscription_status": sub.get("status"),
                "activation_date": sub.get("startDate"),
                "region_code": address.get("regionCode"),
                "region": address.get("region"),
                "address": first.get("locationFormattedAddress") or address.get("formattedAddress"),
                "latitude": first.get("latitude") or geo.get("latitude"),
                "longitude": first.get("longitude") or geo.get("longitude"),
                "terminals": terminals,
            }
        )
    return out


def parse_balance(payload: Any) -> tuple[float, str] | None:
    content = _content(payload) or {}
    balances = content.get("balances") if isinstance(content, dict) else None
    if not balances:
        return None
    first = balances[0]
    return (first.get("dueAmount"), first.get("isoCurrencyCode"))


def _current_cycle(cycles: list[dict]) -> dict:
    """Ciclo abierto (sin endDate); si no, el de mayor endDate; si no hay fechas, el primero."""
    for c in cycles:
        if not c.get("endDate"):
            return c
    dated = [c for c in cycles if c.get("endDate")]
    if dated:
        return max(dated, key=lambda c: c["endDate"])
    return cycles[0]


def _earliest_active_from(lines: list[dict] | None) -> str | None:
    """``activeFrom`` más antiguo de un ciclo: el día en que la línea quedó activa.

    El portal no expone la fecha de activación: se deduce del primer uso real
    (los ciclos previos a la activación vienen en 0 GB y sin ``activeFrom``).
    """
    stamps = [ln.get("activeFrom") for ln in (lines or []) if ln.get("activeFrom")]
    return min(stamps) if stamps else None


def parse_usage(payload: Any) -> dict:
    unknown = {"unknown": True, "cycle_gb": None, "limit_gb": None, "total_gb": None}
    if _is_not_found(payload):
        return dict(unknown)

    content = _content(payload) or {}
    cycles = content.get("billingCyclesAnnotated") if isinstance(content, dict) else None
    if not cycles:
        return dict(unknown)

    total = sum((c.get("totalAmountGB") or 0.0) for c in cycles)
    current = _current_cycle(cycles)
    lines = current.get("dataUsageSummaryLines") or []
    plan = content.get("servicePlan") or {}
    limit = plan.get("usageLimitGB") or (lines[0].get("usageLimitGB") if lines else None)
    return {
        "unknown": False,
        "cycle_gb": current.get("totalAmountGB"),
        "limit_gb": limit or None,
        "total_gb": total,
        "cycles": [
            {
                "start": c.get("startDate"),
                "end": c.get("endDate"),
                "gb": c.get("totalAmountGB"),
                "limit_gb": c.get("usageLimitGB"),
                "active_from": _earliest_active_from(c.get("dataUsageSummaryLines")),
            }
            for c in cycles
        ],
    }
