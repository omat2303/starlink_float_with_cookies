from pathlib import Path

import httpx
import pytest

from portal_client import PortalClient, SessionExpired

FIX = Path(__file__).parent / "fixtures"
load = lambda n: (FIX / n).read_bytes()


def make_transport(seen):
    def handler(req: httpx.Request) -> httpx.Response:
        seen.append((req.url.path, req.headers.get("cookie", "")))
        if req.url.path == "/api/auth/auth/user":
            # el portal reemite Starlink.Com.Access.V1 al fijar la cuenta activa
            return httpx.Response(
                200, json={"content": {"accountId": "ACC-1"}},
                headers={"set-cookie": "Starlink.Com.Access.V1=rotado; Path=/"},
            )
        if "contact" in req.url.path:
            return httpx.Response(200, content=load("accounts.json"))
        if "service-lines" in req.url.path:
            return httpx.Response(200, content=load("service_lines.json"))
        if "payable-balances" in req.url.path:
            return httpx.Response(200, content=load("balance.json"))
        if "data-usage" in req.url.path:
            return httpx.Response(200, content=load("usage.json"))
        return httpx.Response(404, json={"isValid": False})

    return httpx.MockTransport(handler)


async def test_client_activates_account_once_and_parses():
    seen = []
    c = PortalClient({"Starlink.Com.Sso": "x"}, transport=make_transport(seen))
    accs = await c.accounts()
    lines = await c.service_lines("ACC-1")
    bal = await c.balance("ACC-1")
    uso = await c.usage("ACC-1", "SL-1")
    await c.aclose()

    assert accs[0]["account_name"] == "Juan Perez"
    assert lines[0]["terminals"][0]["kit_number"] == "KIT400651113"
    assert bal == (23797.44, "UYU")
    assert uso["total_gb"] == 42.0

    paths = [path for path, _ in seen]
    # el token de acceso caduca en minutos: se reemite antes de listar las cuentas
    assert paths[0] == "/api/auth/auth/user"
    assert paths[1] == "/api/accounts/v3/accounts/contact"
    # fijar ACC-1 = otra reemisión, y una sola para las 3 consultas por cuenta
    assert paths.count("/api/auth/auth/user") == 2
    # la cookie de la cuenta activa viaja en cada consulta por cuenta
    scoped = {path for path, cookies in seen if "account_number=ACC-1" in cookies}
    assert scoped >= {
        "/api/webagg/v2/accounts/service-lines",
        "/api/webagg/v1/public/billing/payable-balances",
        "/api/telemetryagg/v1/data-usage/account/ACC-1/service-line/SL-1/annotated",
    }


async def test_client_reactivates_when_account_changes():
    seen = []
    c = PortalClient({"Starlink.Com.Sso": "x"}, transport=make_transport(seen))
    await c.service_lines("ACC-1")
    await c.service_lines("ACC-2")
    await c.aclose()
    assert [path for path, _ in seen].count("/api/auth/auth/user") == 2


async def test_accounts_refreshes_expired_token_first():
    """El token guardado caduca: /api/auth/auth/user lo reemite con la sola cookie SSO."""
    state = {"refreshed": False}

    def handler(req):
        if req.url.path == "/api/auth/auth/user":
            state["refreshed"] = True
            return httpx.Response(200, json={"content": {"accountId": "ACC-1"}})
        if not state["refreshed"]:
            return httpx.Response(401, text="token_expired")
        return httpx.Response(200, content=load("accounts.json"))

    c = PortalClient({"Starlink.Com.Sso": "x"}, transport=httpx.MockTransport(handler))
    accs = await c.accounts()
    await c.aclose()
    assert accs[0]["account_number"] == "ACC-1"


async def test_session_expired_raises():
    def handler(req):
        return httpx.Response(401, json={"error": "authenticated_user_required"})

    c = PortalClient({}, transport=httpx.MockTransport(handler))
    with pytest.raises(SessionExpired):
        await c.accounts()


async def test_usage_not_found_returns_unknown():
    def handler(req):
        return httpx.Response(200, json={"isValid": False, "errors": [{"errorMessage": "not_found"}]})

    c = PortalClient({}, transport=httpx.MockTransport(handler))
    assert (await c.usage("ACC-1", "SL-1"))["unknown"] is True
