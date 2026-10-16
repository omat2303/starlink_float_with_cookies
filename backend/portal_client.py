"""Cliente HTTP contra el portal real de Starlink (``starlink.com``).

Para mirar OTRA cuenta hay que fijarla como activa: se pone la cookie
``starlink.com.account_number`` y se pide ``/api/auth/auth/user``, que reemite el
token de acceso (``Starlink.Com.Access.V1*``) ya scopeado a esa cuenta. La cookie
sola no basta: ``service-lines`` y el consumo responden según el token vigente
(la cuenta de otro cliente devuelve ``not_found`` o datos de la cuenta activa).
"""
from typing import Any

import httpx

from portal_parsers import (
    parse_accounts,
    parse_balance,
    parse_service_lines,
    parse_usage,
)

BASE_URL = "https://starlink.com"
ACCOUNT_COOKIE = "starlink.com.account_number"

HEADERS = {
    "accept": "*/*",
    "content-type": "application/json",
    "accept-language": "es-419",
    "referer": "https://starlink.com/account/subscriptions",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
    ),
}


class SessionExpired(RuntimeError):
    """La sesión del portal caducó o fue rotada."""


class PortalClient:
    def __init__(
        self,
        cookies: dict[str, str],
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=HEADERS,
            cookies=cookies,
            timeout=timeout,
            transport=transport,
        )
        self._active_account: str | None = None

    async def refresh(self) -> None:
        """Reemite el token de acceso.

        ``Starlink.Com.Access.V1`` caduca en minutos, pero ``/api/auth/auth/user``
        lo reemite con la sola cookie SSO: por eso se llama antes de listar cuentas.
        """
        await self._get("/api/auth/auth/user")

    async def _activate(self, account_number: str) -> None:
        """Fija la cuenta activa (cookie + reemisión del token). Se salta si ya lo está."""
        if account_number == self._active_account:
            return
        self._client.cookies.set(ACCOUNT_COOKIE, account_number)
        await self.refresh()
        self._active_account = account_number

    async def _get(
        self,
        path: str,
        account_number: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        if account_number:
            await self._activate(account_number)
        resp = await self._client.get(path, params=params)
        if resp.status_code in (401, 403):
            raise SessionExpired(resp.text[:200])
        try:
            data = resp.json()
        except ValueError:
            raise SessionExpired(f"respuesta no-JSON ({resp.status_code})")
        if "authenticated_user_required" in str(data):
            raise SessionExpired(str(data)[:200])
        return data

    async def accounts(self) -> list[dict]:
        await self.refresh()  # el token caduca en minutos: renovarlo antes de listar
        return parse_accounts(await self._get("/api/accounts/v3/accounts/contact"))

    async def service_lines(self, account_number: str) -> list[dict]:
        return parse_service_lines(
            await self._get(
                "/api/webagg/v2/accounts/service-lines",
                account_number,
                params={"limit": 100},  # evita paginar (el portal pagea de a 10)
            )
        )

    async def balance(self, account_number: str) -> tuple[float, str] | None:
        return parse_balance(
            await self._get("/api/webagg/v1/public/billing/payable-balances", account_number)
        )

    async def usage(self, account_number: str, service_line_number: str) -> dict:
        path = (
            f"/api/telemetryagg/v1/data-usage/account/{account_number}"
            f"/service-line/{service_line_number}/annotated"
        )
        return parse_usage(await self._get(path, account_number))

    async def aclose(self) -> None:
        await self._client.aclose()
