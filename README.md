# StarPanel

Panel web para administrar un lote de cuentas Starlink: **todas las cuentas en una
sola pantalla**, agrupadas por cliente, con plan, tipo de antena, consumo,
vencimiento, saldo y estado. Sincroniza contra el portal cada 2 horas, así no hay
que entrar cuenta por cuenta.

> Todo cuelga de endpoints **privados** del portal de Starlink (los mismos que usa
> su web). No hay API pública: si Starlink los cambia, hay que ajustar los parsers
> de `backend/portal_parsers.py`.

## Arranque local

```powershell
.\backend\run_local.ps1
```

Abre el panel en `http://localhost:3000` y el backend en `http://localhost:8000`.

A mano:

```powershell
# backend
cd backend
python -m venv venv
.\venv\Scripts\pip install -r ..\requirements.txt
.\venv\Scripts\python -m uvicorn main:app --port 8000

# frontend (otra terminal)
cd frontend
npm install
npm run dev
```

## Configuración

El backend lee variables de entorno (para desarrollo basta con un `backend/.env`,
que **no** se sube al repo):

| Variable | Qué es |
|---|---|
| `APP_ENV` | `dev` (por defecto) o `production`. En producción el backend **no arranca** si faltan secretos |
| `PANEL_PASSWORD_HASH` | hash scrypt de la contraseña del panel |
| `PANEL_SESSION_SECRET` | firma la cookie de sesión `sp_session` |
| `INGEST_TOKEN` | token que exige la extensión al subir la cookie |
| `PANEL_ORIGIN` | origen permitido por CORS (ej. `https://panel.ejemplo.org`) |
| `PANEL_AUTH_DISABLED` | **solo dev**: abre el panel sin login. En producción el backend se niega a arrancar con esto |

Los tres secretos se generan de una vez:

```bash
cd backend
python make_secrets.py 'TU_CONTRASEÑA'
```

Plantillas listas para copiar en `deploy/*.env.example`.

## Uso

1. Abre el panel e inicia sesión con la contraseña.
2. Con la sesión de starlink.com abierta en el mismo Chrome, trae la cookie con la
   **extensión** (botón flotante *Traer cookie y sincronizar*): el backend la
   sincroniza y recarga. Recorre las cuentas una por una.
3. Ya está. El worker resincroniza solo cada 2 horas.

### Extensión de Chrome (una sola vez)

**Descarga:** [`docs/downloads/starpanel-extension-v1.1.0.zip`](docs/downloads/starpanel-extension-v1.1.0.zip)
(botón *Download raw* en GitHub, 3 KB; no hace falta clonar el repo). Si
prefieres la fuente, está la carpeta `extension/` en el propio repo.

Antes de cargarla, pon tu dominio (el del panel) en `extension/manifest.json` y
`extension/background.js`: el repo trae `panel.ejemplo.org` de ejemplo.

`chrome://extensions` → activa **Modo de desarrollador** → **Cargar descomprimida**
→ descomprime el zip y elige la carpeta `extension/` → abre sus opciones y pega
el `INGEST_TOKEN` (en Docker sale del `.env`).

Sin extensión también se puede pegar la cookie a mano en el cuadro del panel
(DevTools → Application → Cookies, los pares `nombre=valor` unidos por `;`).
La extensión es la única vía automática: Chrome 136+ cifra las cookies con
app-bound encryption, así que leer el archivo `Cookies` del disco no funciona.

## Seguridad

La cookie de sesión **es la llave de todas las cuentas del lote**: quien la tenga
entra en todas. Por eso el panel tiene una puerta con contraseña (nginx +
`auth_request`), la cookie se guarda **cifrada** en `backend/.session.enc` (la
llave va en `backend/.session.key`) y ambos están fuera de git; en Docker viven
en el volumen `starpanel_data`.

Si la cookie llegó a salir de la máquina (chat, correo, captura), rótala: cierra
sesión en starlink.com, cambia la contraseña y vuelve a traer la cookie.

Detalles y modelo de amenazas: [`docs/SECURITY.md`](docs/SECURITY.md).

## API

Todo bajo `/api/v1`:

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/clientes` | cuentas agrupadas por cliente. Monedas distintas **no** se suman |
| GET | `/resumen` | totales del panel |
| GET | `/sync-status` | ¿hay sesión? ¿cuándo fue la última sincronización? |
| POST | `/sync` | sincroniza ahora (409 si no hay sesión guardada) |
| PUT | `/gestiones` | crea/edita la gestión de un cliente |
| PATCH | `/antennas/{kit}` | renombra una antena (nombre propio) |
| POST/GET/POST | `/panel/session` · `/panel/verify` · `/panel/logout` | login del panel |
| POST/GET/POST | `/auth/login` · `/auth/status` · `/auth/logout` | cookie de Starlink (extensión) |

## Tests

Desde la raíz del proyecto:

```powershell
.\backend\venv\Scripts\python.exe -m pytest -q
```

Los mismos tests corren en GitHub Actions junto con los tipos, el build y la
auditoría de dependencias del frontend (`.github/workflows/ci.yml`).

## Modelo de datos

- `Account` — una cuenta del portal: `client_name` (agrupador), moneda, saldo, vencimiento.
- `Antenna` — una antena de una cuenta; `model` sale del prefijo del kit (`kit_models.py`).
- `ClientAlias` — reasigna una cuenta a otro cliente sin tocar el portal.
- `Gestion` — datos comerciales por cliente (administrada, quién paga, costo, precio).
- `SyncState` — última sincronización, para la barra de estado.

Detalle completo y diagramas: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Servidor MCP (opcional)

`mcp_server.py` expone el panel como herramientas **de sólo lectura** para
agentes vía [MCP](https://modelcontextprotocol.io): resumen de flota, búsqueda de
antenas por cliente y estado de sincronización. Corre por stdio (no abre ningún
puerto) contra el backend en `127.0.0.1`. El proyecto ya trae
`.opencode/mcp.json`; con `opencode` abierto en la raíz, las herramientas
aparecen como `starlink-fleet`.

## Despliegue

Todavía **no hay instancia pública**. Dos caminos documentados:

- **[Docker](docs/deployment/docker.md) (recomendado):** `docker compose up -d`
  con HTTPS automático (Caddy + Let's Encrypt) y perfil opcional de Portainer.
  Es el camino más corto para que *cualquiera* lo levante en un VPS sin
  pelearse con certificados.
- **[Sistema nativo (systemd)](docs/deployment/README.md):** nginx en el host,
  certbot (Let's Encrypt), fail2ban y el runbook completo paso a paso.

## Aviso

Proyecto no oficial, sin relación con SpaceX/Starlink. Usa endpoints internos del
portal, que pueden cambiar sin aviso y cuyo uso está sujeto a los términos de
servicio de Starlink.

## Fuera de alcance (por ahora)

- Login multi-tenant por invitación (fase 2).
- Alertas por WhatsApp.
- Conversión de monedas: cada saldo va con su moneda, nunca se suma un total.

## Historial de cambios

Ver [`CHANGELOG.md`](CHANGELOG.md).

## Licencia

AGPL-3.0 — ver [`LICENSE`](LICENSE).

Copyright (C) 2026 omat2303

Puedes usar, modificar y desplegar este programa, incluso comercialmente y en
tu propio negocio. La única condición: si lo modificas y lo ofreces como
servicio a terceros (por ejemplo, tu propia versión del panel en la web), tienes
que publicar tu código fuente bajo esta misma licencia. Eso evita que alguien lo
cierre y lo revenda.
