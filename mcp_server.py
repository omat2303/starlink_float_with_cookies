"""
MCP Server para Gestión de Flota Starlink
==========================================

Servidor FastMCP que expone herramientas para gestionar una flota de antenas Starlink.
Se conecta a la API backend local (http://localhost:8000) para obtener datos
y ejecutar comandos sobre las antenas.

Herramientas disponibles:
    - obtener_resumen_flota: Resumen general de la flota
    - buscar_antenas_cliente: Búsqueda de antenas por nombre de cliente
    - consultar_alertas_pago: Alertas de facturación y riesgo de corte
    - ejecutar_comando_antena: Enviar comandos a antenas (reboot/stow/unstow)
    - crear_sesion_campo: Crear sesiones de campo para técnicos
"""

import os
from typing import Literal

import httpx
from mcp.server.fastmcp import FastMCP

# ─── Configuración ───────────────────────────────────────────────────────────

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 30.0  # segundos

# ─── Inicialización del servidor ─────────────────────────────────────────────

mcp = FastMCP(
    name="Starlink Fleet Management",
    instructions=(
        "Servidor MCP para gestión de flota de antenas Starlink. "
        "Permite consultar el estado de la flota, buscar antenas por cliente, "
        "gestionar alertas de pago, ejecutar comandos remotos y crear sesiones de campo."
    ),
)


# ─── Cliente HTTP helper ──────────────────────────────────────────────────────

async def _get(path: str, params: dict | None = None) -> dict:
    """Realiza una petición GET al backend y retorna el JSON respuelta."""
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(path, params=params)
        response.raise_for_status()
        return response.json()


async def _post(path: str, payload: dict | None = None) -> dict:
    """Realiza una petición POST al backend y retorna el JSON resuelto."""
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(path, json=payload)
        response.raise_for_status()
        return response.json()


# ─── Herramientas MCP ─────────────────────────────────────────────────────────


@mcp.tool()
async def obtener_resumen_flota() -> dict:
    """
    Obtiene el resumen general de la flota de antenas Starlink.

    Retorna información consolidada que incluye:
        - Número total de antenas registradas
        - Cantidad de antenas en línea y fuera de línea
        - Resumen financiero (ingresos pendientes, facturación mensual)
        - Distribución por estado operativo

    Returns:
        dict: Resumen de la flota con conteos y datos financieros.

    Raises:
        Exception: Si el backend no está disponible o retorna un error.
    """
    try:
        data = await _get("/api/fleet/summary")
        return {
            "status": "ok",
            "data": data,
        }
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
        return {
            "status": "error",
            "error": f"Error inesperado: {exc}",
        }


@mcp.tool()
async def buscar_antenas_cliente(nombre_cliente: str) -> dict:
    """
    Busca antenas asociadas a un cliente por su nombre.

    Realiza una búsqueda parcial (case-insensitive) sobre el nombre del cliente
    y retorna todas las antenas que coincidan.

    Args:
        nombre_cliente: Nombre (o parte del nombre) del cliente a buscar.
                        Ejemplo: "Juan Pérez", "Comercial", "María"

    Returns:
        dict: Lista de antenas encontradas con su información básica
              (kit_number, modelo, estado, dirección de instalación).

    Raises:
        Exception: Si el backend no está disponible o retorna un error.
    """
    try:
        data = await _get("/api/antennas/search", params={"cliente": nombre_cliente})
        return {
            "status": "ok",
            "data": data,
        }
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
        return {
            "status": "error",
            "error": f"Error inesperado: {exc}",
        }


@mcp.tool()
async def consultar_alertas_pago() -> dict:
    """
    Consulta las alertas de facturación y riesgo de corte de servicio.

    Retorna información sobre:
        - Facturas pendientes de pago con días de atraso
        - Clientes en riesgo de corte por falta de pago
        - Montos vencidos y próximos a vencer
        - Historial de alertas generadas

    Returns:
        dict: Alertas de pago activas con detalle de cada una.

    Raises:
        Exception: Si el backend no está disponible o retorna un error.
    """
    try:
        data = await _get("/api/billing/alerts")
        return {
            "status": "ok",
            "data": data,
        }
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
        return {
            "status": "error",
            "error": f"Error inesperado: {exc}",
        }


@mcp.tool()
async def ejecutar_comando_antena(
    kit_number: str,
    comando: Literal["reboot", "stow", "unstow"],
) -> dict:
    """
    Ejecuta un comando remoto sobre una antena Starlink específica.

    Los comandos disponibles son:
        - reboot: Reinicia la antena (apaga y enciende el equipo)
        - stow: Plega la antena a su posición de transporte
        - unstow: Despliega la antena desde su posición de transporte

    Args:
        kit_number: Número de kit único de la antena (formato: "041234567890").
        comando: Tipo de comando a ejecutar. Debe ser uno de: reboot, stow, unstow.

    Returns:
        dict: Resultado de la ejecución del comando con estado y timestamp.

    Raises:
        Exception: Si el backend no está disponible o retorna un error.
    """
    try:
        data = await _post(
            f"/api/antennas/{kit_number}/command",
            payload={"comando": comando},
        )
        return {
            "status": "ok",
            "data": data,
        }
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
        return {
            "status": "error",
            "error": f"Error inesperado: {exc}",
        }


@mcp.tool()
async def crear_sesion_campo(
    kit_number: str,
    duracion_minutos: int,
) -> dict:
    """
    Crea una sesión de campo para un técnico sobre una antena específica.

    Las sesiones de campo permiten a los técnicos acceder remotamente a la
    antena para realizar diagnósticos, actualizaciones de firmware o
    resolución de problemas in situ.

    Args:
        kit_number: Número de kit único de la antena (formato: "041234567890").
        duracion_minutos: Duración de la sesión en minutos (mínimo 15, máximo 480).

    Returns:
        dict: Detalles de la sesión creada (ID, URL de acceso, tiempo de expiración).

    Raises:
        Exception: Si el backend no está disponible o retorna un error.
    """
    try:
        data = await _post(
            f"/api/antennas/{kit_number}/field-session",
            payload={"duracion_minutos": duracion_minutos},
        )
        return {
            "status": "ok",
            "data": data,
        }
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
        return {
            "status": "error",
            "error": f"Error inesperado: {exc}",
        }


# ─── Punto de entrada ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
