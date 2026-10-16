"""Probe desechable (spike): confirma si el endpoint REST real de Starlink
responde con tu cookie de sesion, y muestra la forma de los datos.

NO es produccion. Sin tests. Borrar al terminar.

Uso:
  1. Pega tu cookie (una sola linea, sin los ^ de cmd) en spike/cookie.txt
  2. python spike/probe.py
"""
import json
import time
from pathlib import Path

import requests

cookie = Path(__file__).with_name("cookie.txt").read_text(encoding="utf-8").strip()
if not cookie or cookie.startswith("#"):
    raise SystemExit("Pega tu cookie en spike/cookie.txt (una sola linea).")

s = requests.Session()
s.headers.update({
    "accept": "*/*",
    "content-type": "application/json",
    "accept-language": "es-419",
    "referer": "https://starlink.com/account/subscriptions",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
    ),
})
for part in cookie.split(";"):
    if "=" in part:
        k, v = part.strip().split("=", 1)
        s.cookies.set(k, v, domain="starlink.com")

# El primero esta confirmado por el cURL. Los demas son adivinanzas: si fallan,
# hay que sacar las rutas reales del HAR de /account/subscriptions.
PATHS = [
    "/api/auth/auth/user",
    "/api/auth/auth/accounts",
    "/api/auth/auth/subscriptions",
    "/api/account/subscriptions",
]

for path in PATHS:
    try:
        r = s.get("https://starlink.com" + path, timeout=20)
        ct = r.headers.get("content-type", "")
        print(f"\n=== {path} -> {r.status_code} ({ct[:40]})")
        if "json" in ct:
            print(json.dumps(r.json(), indent=2, ensure_ascii=False)[:3000])
        else:
            print(r.text[:300])
    except Exception as e:
        print(f"\n=== {path} -> ERROR {type(e).__name__}: {e}")
    time.sleep(1)
