"""Almacén de la sesión del portal Starlink, cifrada en disco.

Las cookies de sesión abren todas las cuentas del lote: nunca se guardan en
texto plano. Se cifran con Fernet y la llave vive en ``KEY_FILE``.

shortcut: llave y secreto en archivos locales; upgrade a KMS/secret manager
cuando el panel salga de la laptop.
"""
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

_BASE = Path(__file__).resolve().parent
# SESSION_DIR saca la bóveda del código para que viva en un volumen (Docker).
_DATA = Path(os.getenv("SESSION_DIR", str(_BASE)))
SESSION_FILE = _DATA / ".session.enc"
KEY_FILE = _DATA / ".session.key"


def _fernet(key_path: Path | None = None) -> Fernet:
    kp = key_path or KEY_FILE
    if not kp.exists():
        kp.write_bytes(Fernet.generate_key())
        try:
            os.chmod(kp, 0o600)
        except (OSError, NotImplementedError):
            pass
    return Fernet(kp.read_bytes())


def save(cookies: dict[str, str], path: Path | None = None, key_path: Path | None = None) -> None:
    """Cifra y guarda las cookies de sesión."""
    target = path or SESSION_FILE
    target.write_bytes(_fernet(key_path).encrypt(json.dumps(cookies).encode("utf-8")))
    try:
        os.chmod(target, 0o600)
    except (OSError, NotImplementedError):
        pass


def load(path: Path | None = None, key_path: Path | None = None) -> dict[str, str]:
    """Devuelve las cookies de sesión, o {} si no hay o no se pueden descifrar."""
    target = path or SESSION_FILE
    if not target.exists():
        return {}
    try:
        raw = _fernet(key_path).decrypt(target.read_bytes())
    except InvalidToken:
        return {}
    return json.loads(raw.decode("utf-8"))


def clear(path: Path | None = None) -> None:
    """Borra el archivo de sesión (no la llave)."""
    target = path or SESSION_FILE
    if target.exists():
        target.unlink()


def has_session() -> bool:
    """True si hay una sesión guardada y legible."""
    return bool(load())
