"""Configuración por entorno.

En producción el backend NO arranca si falta un secreto: preferimos un fallo
ruidoso al arrancar que un panel abierto por olvidar una variable.
"""
import logging
import os

logger = logging.getLogger(__name__)

REQUIRED_IN_PROD = ("PANEL_PASSWORD_HASH", "PANEL_SESSION_SECRET", "INGEST_TOKEN")


def is_prod() -> bool:
    return os.getenv("APP_ENV", "dev").lower() == "production"


def auth_disabled() -> bool:
    """Lee el env en cada llamada: no cachear, o el guard de prod se queda obsoleto."""
    return os.getenv("PANEL_AUTH_DISABLED", "false").lower() == "true"


def startup_check() -> None:
    if not is_prod():
        return
    if auth_disabled():
        raise RuntimeError("PANEL_AUTH_DISABLED cannot be enabled in production")
    missing = [name for name in REQUIRED_IN_PROD if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Faltan variables obligatorias en producción: " + ", ".join(missing)
        )
    logger.info("Configuración de producción validada")
