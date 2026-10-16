"""Catálogo de modelos de antena Starlink derivado del prefijo del número de kit.

El portal entrega los kits como ``KIT`` + tipo + serie (p. ej. ``KIT400651113``).
El modelo se deriva del prefijo, verificado contra la guía de Starlink. El orden
importa: los prefijos más específicos van primero (``KIT4M`` antes que ``KIT4``).
"""

_KIT_PREFIXES = (
    ("KIT4M", "Mini"),
    ("KIT4P", "Performance Gen3"),
    ("KIT4", "Standard V4"),
    ("KIT3", "Standard V2"),
    ("KITP", "Performance Gen2"),
    ("KIT5", "Standard V5"),
)


def kit_model(kit_number: str) -> str:
    """Devuelve el modelo de la antena a partir del número de kit."""
    kit = (kit_number or "").upper()
    for prefix, label in _KIT_PREFIXES:
        if kit.startswith(prefix):
            return label
    return "Desconocido"
