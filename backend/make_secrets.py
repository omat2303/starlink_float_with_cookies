"""Genera los secretos del panel.  Uso:  python make_secrets.py 'tu-contraseña'

La contraseña se hashea aquí (y sólo aquí) para que el formato scrypt$...$...
coincida exactamente con el que valida ``panel_auth.verify_password``.
"""
import secrets
import sys

from panel_auth import hash_password

print("PANEL_SESSION_SECRET=" + secrets.token_urlsafe(48))
print("INGEST_TOKEN=" + secrets.token_urlsafe(32))
if len(sys.argv) > 1:
    print("PANEL_PASSWORD_HASH=" + hash_password(sys.argv[1]))
else:
    print("# PANEL_PASSWORD_HASH: pasa la contraseña como argumento para generarlo")
