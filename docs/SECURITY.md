# StarPanel — modelo de amenazas y controles

## Activos que protegemos

| Activo | Dónde vive | Impacto si se filtra |
|---|---|---|
| Cookie de sesión de starlink.com (todas las cuentas del lote) | `backend/.session.enc` cifrada | Acceso total a los clientes |
| Llave de cifrado | `backend/.session.key` | Descifra la cookie |
| Datos de clientes (nombres, saldos, direcciones) | SQLite `starlink_fleet.db` + API | Fuga de datos personales y comerciales |
| Contraseña del panel | hash scrypt en `.env` | Entrada al panel |

## Límites de confianza

```
navegador ──[1]──> nginx ──[2]──> backend (loopback)
extensión ──[3]──> nginx ──[2]──> backend
disco     ──[4]──> backend
```

1. **navegador → nginx**: hostil. TLS obligatorio; todo pasa por `auth_request`.
2. **nginx → backend**: loopback. El backend *confía* en lo que llega por `127.0.0.1`
   (por eso NO se expone más allá de localhost).
3. **extensión → nginx**: hostil. Autoriza con `X-Ingest-Token`.
4. **disco → backend**: la cookie se cifra con Fernet; la llave está fuera del repo.

## Controles implementados

| Amenaza (STRIDE) | Control |
|---|---|
| Spoofing: cualquiera abre el panel | Login con contraseña (scrypt) + cookie firmada HMAC; nginx la exige en cada ruta |
| Spoofing: cualquiera sube una cookie | `X-Ingest-Token` obligatorio en producción |
| Tampering: cookie de sesión falseada | Firma HMAC-SHA256, `compare_digest`, expiración de 30 días |
| Info disclosure: panel abierto | Backend y frontend en `127.0.0.1`; sólo nginx en 443 |
| Info disclosure: cookie en disco | Fernet; `.env` y `.session.*` en `.gitignore`, `chmod 600` |
| Info disclosure: XSS roba la cookie | `sp_session` es `httpOnly`, `Secure`, `SameSite=Lax` |
| Elevation: arrancar sin secretos | `APP_ENV=production` + `startup_check()` aborta el arranque |
| DoS: fuerza bruta / scraping | `limit_req` (login 10 r/min) + fail2ban + pausa de 300 ms en login fallido |
| CSRF | `SameSite=Lax` + cabecera `X-Requested-With: starpanel` en métodos de escritura (nginx) |
| Fuga por cabeceras | HSTS, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy` |

## Fuera de alcance (por ahora)

- **Multi-tenant**: hoy el panel tiene una sola puerta. La fase 2 (un `sub` por
  invitado en la cookie de sesión y filtrado por dueño) ya tiene la costura
  preparada en `panel_auth.make_token(sub=...)`.
- **El backend confía en el loopback**: un proceso local con acceso al VPS podría
  leer la API sin pasar por nginx. Mitigado con un VPS dedicado y `ufw`; si se
  endurece más, hay que firmar también las peticiones internas.
- La extensión no está firmada; se carga manualmente.

## Verificación de cada control

```bash
# 1. Fallo cerrado sin secretos (debe imprimir RuntimeError)
cd backend && APP_ENV=production python -c "import config; config.startup_check()"

# 2. Arranque con secretos válidos (debe imprimir "validada")
APP_ENV=production PANEL_SESSION_SECRET=x INGEST_TOKEN=y PANEL_PASSWORD_HASH=z \
  python -c "import config; config.startup_check()"

# 3. La API no se sirve sin sesión de panel
curl -s -o /dev/null -w '%{http_code}\n' https://star.ogtelecom.org/api/v1/clientes   # 401

# 4. La ingesta exige token
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://star.ogtelecom.org/api/auth/login \
     -H 'Content-Type: application/json' -d '{"cookie":"a=b"}'                        # 401

# 5. Cabeceras de seguridad presentes
curl -sI https://star.ogtelecom.org/login | grep -Ei 'strict-transport|x-content-type|x-frame'

# 6. El backend no escucha fuera de localhost
ss -ltnp | grep 8000      # debe mostrar 127.0.0.1:8000
```
