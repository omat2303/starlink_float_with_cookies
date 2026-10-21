"""Smoke test del servidor MCP opcional (`mcp_server.py`, raíz del repo).

No levanta el servidor ni abre sockets: verifica que el módulo importe, que
las tres herramientas queden registradas y que el filtro de clientes funcione
con el backend simulado. Es lo que detecta si una actualización de `mcp`
(p. ej. el PR de dependabot a 2.x) rompe la importación en silencio.
"""

import pytest

pytest.importorskip("mcp")  # dependencia opcional: sólo quien usa el servidor MCP la instala

import mcp_server  # noqa: E402


async def test_registra_las_tres_herramientas():
    nombres = {t.name for t in await mcp_server.mcp.list_tools()}
    assert {"obtener_resumen_flota", "buscar_antenas_cliente", "estado_sincronizacion"} <= nombres


async def test_buscar_antenas_filtra_por_nombre(monkeypatch):
    async def fake_get(path, params=None):
        assert path == "/api/v1/clientes"
        return {"status": "ok", "data": [
            {"client_name": "Juan Pérez", "is_suspended": False, "accounts": [
                {"antennas": [{"kit_number": "KIT1", "nickname": "Casa",
                               "custom_name": None, "model": "Standard",
                               "active": True, "is_suspended": False,
                               "address": "Caracas"}]}]},
            {"client_name": "Comercial Sur", "is_suspended": True, "accounts": []},
        ]}

    monkeypatch.setattr(mcp_server, "_get", fake_get)
    res = await mcp_server.buscar_antenas_cliente("juan")
    assert res["status"] == "ok"
    assert [c["client_name"] for c in res["data"]] == ["Juan Pérez"]
    assert res["data"][0]["antenas"][0]["kit_number"] == "KIT1"


async def test_buscar_antenas_propaga_error_del_backend(monkeypatch):
    async def fake_get(path, params=None):
        return {"status": "error", "error": "No se pudo conectar"}

    monkeypatch.setattr(mcp_server, "_get", fake_get)
    res = await mcp_server.buscar_antenas_cliente("x")
    assert res == {"status": "error", "error": "No se pudo conectar"}
