# StarPanel — Arquitectura

Cómo está armado el panel por dentro: componentes, flujo de datos, modelo de datos
y decisiones de diseño.

## Visión general

StarPanel agrupa **todas las cuentas de un lote Starlink** en una sola pantalla,
por cliente. Starlink no tiene API pública: el panel habla con los **mismos
endpoints privados** que usa la web de starlink.com, autenticándose con la cookie
de sesión del navegador.

```
                    ┌───────────────────────────────────────────────┐
   navegador ─TLS─► │ nginx                                          │
                    │  · auth_request → /api/v1/panel/verify         │
                    │  · X-Requested-With en escrituras (CSRF)       │
                    └───────┬───────────────────────┬───────────────┘
                            │                       │
              ┌─────────────▼────────┐   ┌──────────▼─────────────┐
              │ Next.js  :3000        │   │ FastAPI  :8000         │
              │ páginas + rewrites    │──►│ API + worker de sync   │
              │ /api/* → :8000        │   └──────┬─────────┬───────┘
              └──────────────────────┘          │         │
                                      ┌─────────▼──┐  ┌───▼──────────────┐
   extensión Chrome ──/api/auth/login─►│ SQLite     │  │ .session.enc     │
   (X-Ingest-Token)                    │ (flota)    │  │ cookie cifrada   │
                                       └────────────┘  └──────────────────┘
```

Backend y frontend escuchan **sólo en `127.0.0.1`**; nginx es la única puerta
hacia el exterior. Ver [SECURITY.md](SECURITY.md).

## Componentes

| Componente | Ruta | Rol |
|---|---|---|
| Backend | `backend/` | API FastAPI + worker de sincronización |
| Frontend | `frontend/` | UI Next.js (App Router) |
| Extensión | `extension/` | lee las cookies de starlink.com y las sube al backend |
| MCP | `mcp_server.py` | herramientas de sólo lectura (resumen, búsqueda, sync) para OpenCode, por stdio |
| Despliegue | `deploy/`, `docs/deployment/` | unidades systemd, nginx, guía de VPS |

## Backend (`backend/`)

| Módulo | Responsabilidad |
|---|---|
| `main.py` | app FastAPI, endpoints, CORS, `lifespan` (chequeo de config, creación de tablas, arranque del worker) |
| `config.py` | lectura de entorno y `startup_check()`: en producción aborta si falta un secreto |
| `panel_auth.py` | login del panel: contraseña (scrypt) → cookie de sesión firmada (HMAC-SHA256) |
| `auth_routes.py` | ingesta de la cookie de Starlink (exige `X-Ingest-Token`); estado y cierre de sesión |
| `session_store.py` | guarda/lee la cookie de Starlink **cifrada** (Fernet) en disco |
| `portal_client.py` | cliente `httpx` contra los endpoints privados del portal |
| `portal_parsers.py` | normaliza el JSON del portal a formas estables |
| `worker.py` | `sync_once()` + loop cada 2 h |
| `database.py` | engine/session SQLAlchemy (SQLite + WAL), `ensure_schema()` |
| `models.py` | modelos ORM |
| `kit_models.py` | deduce el modelo de antena desde el prefijo del kit |
| `make_secrets.py` | genera `PANEL_SESSION_SECRET`, `INGEST_TOKEN`, `PANEL_PASSWORD_HASH` |

### Sincronización

`worker.sync_once(client, db)` es el corazón del sistema:

1. `client.accounts()` → todas las cuentas del lote.
2. Por cada cuenta: `service_lines()`, `balance()` y `usage()` por línea.
3. Upsert de `Account` y `Antenna` (clave: `account_number` / `kit_number`).
4. **Commit por cuenta**: así un sync largo no mantiene el lock de SQLite y el
   panel puede seguir editando (nombre propio, gestión) mientras sincroniza.

Un error en una cuenta no detiene el sync (`try/except` por cuenta, se cuenta en
`stats["errors"]`). `start_sync_loop()` corre cada **2 h** y nunca muere por un
fallo de red. La sesión activa se elige con la cookie `starlink.com.account_number`
y el token de acceso caducado se reemite contra `/api/auth/auth/user`.

## Modelo de datos

SQLite (`starlink_fleet.db`), creado/actualizado por `database.py`.

```
Account (accounts)                     Antenna (antennas)
├── account_number  (uniq, idx)        ├── kit_number        (uniq, idx)
├── account_name                       ├── account_id  ───► Account
├── client_name     ← agrupador        ├── service_line_number
├── region_code / currency_code        ├── nickname  / custom_name
├── is_billing_suspended               ├── model  / plan
├── next_due_date                      ├── active / is_suspended / is_standby
├── balance_due                        ├── subscription_status
└── status                             ├── activation_date
      │                                ├── cycles_json           (historial de consumo)
      └──── 1:N ──► antennas           ├── data_cycle/limit/total_gb
                                       ├── address / lat / lon
                                       └── last_connected

ClientAlias (client_aliases)   reasigna una cuenta a otro cliente (manda sobre account_name)
Gestion (gestiones)            datos comerciales por cliente: administrada, quién paga, costo, precio, notas
SyncState (sync_state)         última sincronización (fecha, nº cuentas, nº antenas)
```

`Gestion` vive **aparte** de `accounts` a propósito: el sync del portal nunca la
pisa. Las monedas distintas **nunca** se suman (cada saldo va con su moneda).

## Autenticación (dos puertas independientes)

1. **Panel (OG)** — `panel_auth.py`. Se envía la contraseña a
   `POST /api/v1/panel/session`; si el hash scrypt coincide, se firma una cookie
   `sp_session` (HMAC-SHA256, `HttpOnly`, `Secure` en producción, `SameSite=Lax`,
   30 días). nginx la valida con `auth_request` contra
   `GET /api/v1/panel/verify` en cada petición. El token es autocontenido
   (`sub:exp` firmado); `sub` es la costura por donde entrará el multi-tenant.
   La cookie de Starlink pegada **a mano** en el panel entra por
   `POST /api/v1/panel/cookie` (misma bóveda que la extensión, pero detrás de la
   sesión de OG en vez del token de ingesta).
2. **Extensión** — `auth_routes.py`. La cookie de Starlink se sube a
   `POST /api/v1/auth/login` con la cabecera `X-Ingest-Token`.

## API

Todo bajo `/api/v1`:

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/clientes` | cuentas agrupadas por cliente (monedas separadas) |
| GET | `/resumen` | conteos de la tarjeta superior |
| GET | `/sync-status` | ¿hay sesión? ¿cuándo fue el último sync? |
| POST | `/sync` | sincroniza ahora (409 si no hay sesión) |
| PUT | `/gestiones` | crea/edita la gestión de un cliente |
| PATCH | `/antennas/{kit}` | renombra una antena (`custom_name`) |
| POST/GET/POST/POST | `/panel/session` · `/panel/verify` · `/panel/logout` · `/panel/cookie` | login del panel y guardado manual de la cookie de Starlink |
| POST/GET/POST | `/auth/login` · `/auth/status` · `/auth/logout` | ingesta y estado de la cookie de Starlink |

## Frontend (`frontend/`)

Next.js 14 (App Router). `next.config.js` reescribe `/api/*` a
`http://localhost:8000/api/v1/*`, así el navegador nunca habla directo con el
backend.

| Ruta | Pantalla |
|---|---|
| `/` | panel principal: tarjetas de resumen + clientes |
| `/gestiones` | tabla de gestiones/costos por cliente |
| `/login` | puerta de entrada (contraseña) |

Componentes: `ClientList`, `GestionTable`, `SessionBar` (estado del sync y botón
de sincronizar), `PanelMenu` (navegación y salir).

## Extensión de Chrome (`extension/`)

Es la **única vía automática** para leer la cookie: Chrome 136+ cifra las cookies
con app-bound encryption, así que leer el archivo `Cookies` del disco no sirve.
`background.js` usa el permiso `cookies`, arma el header `nombre=valor; …` y lo
POSTea a `/api/auth/login` con el `X-Ingest-Token` guardado en `chrome.storage`.
El token se pega una vez en `options.html`.

## Decisiones y límites

- **Sin API pública, a propósito**: todo depende de endpoints privados del portal.
  Si Starlink los cambia, hay que ajustar `portal_parsers.py`.
- **El backend confía en el loopback**: no tiene capa de auth propia para los
  endpoints de datos; la única puerta es nginx. Por eso backend y frontend se
  atan a `127.0.0.1` y el VPS debe ser dedicado. Ver `SECURITY.md`.
- **Single-tenant hoy**: una sola contraseña de panel. El multi-tenant (login por
  invitación, un `sub` por invitado, filtrado por dueño) es la fase 2.
- **La cookie es la llave de todo el lote**: se cifra en disco (Fernet) y la llave
  vive fuera del repo.
