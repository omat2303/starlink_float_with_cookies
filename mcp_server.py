"""
MCP Server para Gestión de Flota Starlink
==========================================

Servidor FastMCP que expone el panel StarPanel como herramientas **de sólo
lectura** para un agente (OpenCode y compatibles).

Habla con la API del backend, que escucha únicamente en 127.0.0.1: no abre
ningún puerto propio (transporte stdio: el cliente MCP lo lanza como proceso
hijo) y no manda credenciales, porque el backend lo alcanza en local.

Herramientas:
    - obtener_resumen_flota: conteos de la tarjeta superior del panel
    - buscar_antenas_cliente: antenas de un cliente (búsqueda parcial)
    - estado_sincronizacion: última sync y si hay cookie guardada

El proyecto es de sólo lectura: no expone comandos sobre antenas.
"""

import os

import httpx
from mcp.server.fastmcp import FastMCP

# ─── Configuración ───────────────────────────────────────────────────────────

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 30.0  # segundos

# ─── Inicialización del servidor ─────────────────────────────────────────────

mcp = FastMCP(
    name="StarPanel",
    instructions=(
        "Herramientas de sólo lectura para el panel StarPanel: resumen de la "
        "flota, antenas de un cliente y estado de la sincronización."
    ),
)


# ─── Cliente HTTP helper ──────────────────────────────────────────────────────

async def _get(path: str, params: dict | None = None) -> dict:
    """GET al backend. Devuelve el error como dato en vez de lanzarlo: el agente lo lee."""
    try:
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return {"status": "ok", "data": response.json()}
    except httpx.HTTPStatusError as exc:
        return {
            "status": "error",
            "error": f"HTTP {exc.response.status_code}: {exc.response.text}",
        }
    except httpx.ConnectError:
        return {
            "status": "error",
            "error": (
                f"No se pudo conectar al backend en {BACKEND_URL}. "
                "Verifica que el servidor esté corriendo."
            ),
        }
    except Exception as exc:
        return {"status": "error", "error": f"Error inesperado: {exc}"}


# ─── Herramientas MCP ─────────────────────────────────────────────────────────


@mcp.tool()
async def obtener_resumen_flota() -> dict:
    """
    Obtiene el resumen general de la flota de antenas Starlink.

    Returns:
        dict: clientes, cuentas, antenas, suspendidas, por_vencer y
              por_vencer_72h (conteos).
    """
    return await _get("/api/v1/resumen")


@mcp.tool()
async def buscar_antenas_cliente(nombre_cliente: str) -> dict:
    """
    Busca las antenas de los clientes cuyo nombre coincide (parcial, sin
    distinguir mayúsculas).

    Args:
        nombre_cliente: Nombre (o parte) del cliente. Ej: "Juan Pérez", "Comercial".

    Returns:
        dict: por cada cliente, sus antenas (kit_number, apodo, nombre propio,
              modelo, encendida, suspendida, dirección).
    """
    res = await _get("/api/v1/clientes")
    if res["status"] == "error":
        return res

    needle = nombre_cliente.strip().lower()
    clientes = res["data"]
    if needle:
        clientes = [c for c in clientes if needle in c["client_name"].lower()]

    return {
        "status": "ok",
        "data": [
            {
                "client_name": c["client_name"],
                "is_suspended": c["is_suspended"],
                "antenas": [
                    {
                        "kit_number": a["kit_number"],
                        "nickname": a["nickname"],
                        "custom_name": a["custom_name"],
                        "model": a["model"],
                        "active": a["active"],
                        "is_suspended": a["is_suspended"],
                        "address": a["address"],
                    }
                    for account in c["accounts"]
                    for a in account["antennas"]
                ],
            }
            for c in clientes
        ],
    }


@mcp.tool()
async def estado_sincronizacion() -> dict:
    """
    Consulta si hay cookie de Starlink guardada y cuándo fue la última sync.

    Returns:
        dict: has_session, last_sync, accounts y antennas de la última sync.
    """
    return await _get("/api/v1/sync-status")


# ─── Punto de entrada ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
