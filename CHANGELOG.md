# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y versionado [SemVer](https://semver.org/lang/es/).

Todavía no hay una instancia desplegada: ver [docs/deployment](docs/deployment/README.md).

## [Sin publicar]

### Cambiado

- El CI del backend ahora prueba Python 3.10 y 3.12: el runbook asume Ubuntu 22.04, que trae 3.10, y antes sólo se validaba 3.12.
- El README tenía **dos** secciones de despliegue (una vieja que sólo apuntaba al runbook nativo y otra nueva al final). Ahora hay una sola, con Docker primero como camino recomendado.
- Las opciones de la extensión ya no mencionan a un operador concreto: explican que el `INGEST_TOKEN` está en el `.env` del panel o que hay que pedírselo a quien lo desplegó. El repo es público y cualquiera puede montar su propia instancia.
- Tildes en los nombres visibles del CI (`Frontend (tipos, build, auditoría)`, `Auditoría de dependencias de producción`), que se leen en la pestaña Actions de GitHub.
- La extensión deduplica las cookies por nombre y se queda con la más reciente, y sólo con las de `starlink.com` (no de subdominios). `parse_cookies` del backend es *last-wins*: una cookie huérfana de una sesión anterior podía tapar la recién iniciada, que era la causa de "toma una cookie vieja y no la nueva sesión". Versión de la extensión: 1.1.3.

### Añadido

- Despliegue Docker/Portainer: compose con Caddy (HTTPS automático) y nginx como puerta ya auditada; volumen para los datos; variables configurables con `SESSION_DIR`; documentación en [docs/deployment/docker.md](docs/deployment/docker.md).
- **Descarga de la extensión** empaquetada en el repo: [`docs/downloads/starpanel-extension-v1.1.3.zip`](docs/downloads/starpanel-extension-v1.1.3.zip) (carpeta `extension/` dentro, lista para *Cargar descomprimida*). Enlazada desde el README, desde [docker.md](docs/deployment/docker.md) y desde el runbook nativo, para instalarla sin clonar el repo entero. El zip se regenera con `Compress-Archive -Path extension/* -DestinationPath docs/downloads/starpanel-extension-v1.1.3.zip` cada vez que cambie la extensión.
- Si la extensión no tiene token guardado ya no manda una petición inútil que acaba en 401: el icono avisa directamente *Falta el token de ingesta: abre las Opciones de la extensión y pégalo*.
- `POST /api/v1/auth/login` rechaza cookies cuyo valor esté vacío (p. ej. un `x=` de prueba): antes ese dict casi vacío pisaba la sesión real guardada y el panel se quedaba con datos viejos hasta volver a enviar la cookie.

### Corregido

- La extensión de Chrome mandaba la cookie a `https://panel.ejemplo.org` (el dominio de ejemplo del repo) y no declaraba permiso para el backend local, así que la cookie nunca llegaba al panel en `localhost`. Ahora apunta a `http://localhost:8000/api/v1/auth/login`, declara ese host, y su botón aparece también en el panel (`localhost:3000`). `StarPanel.bat` carga `backend/.env` (`--env-file`) para que el `INGEST_TOKEN` sea determinista y coincida con el que se pega en las opciones.
- La extensión fallaba sin decir por qué: si la petición no llegaba (backend caído, permiso ausente) la promesa se rompía en silencio, y el badge rojo `!` no daba el motivo. Ahora todo error se reporta, el tooltip del icono dice la causa, y un `HTTP 401` avisa explícitamente que hay que revisar el token de ingesta en las Opciones.
- La última sección del README tenía dos caracteres rotos (`producci?n`, `autom?tico`): se había escrito con una redirección de PowerShell que pierde la codificación. Todo el README vuelve a estar en UTF-8 válido.

- El runbook copiaba el conf final de nginx antes de emitir el certificado, y `nginx -t` fallaba porque `fullchain.pem` todavía no existía (callejón sin salida en el paso 5). Ahora primero se emite con un `server` mínimo por HTTP y después se instala el conf del repo.
- El runbook hacía `chown` antes de copiar el repo: si clonabas como root, `npm ci` fallaba por permisos. El `chown` va después de copiar.
- La verificación final usaba `findstr`, que es de Windows, en una guía para Ubuntu. Ahora usa `grep -Ei`.

## [0.1.0] - 2026-10-16

Primera versión usable del panel.

### Añadido

- Panel web de gestión de flota: clientes, cuentas, antenas, suspensiones y gestiones.
- Login propio del panel (scrypt + cookie HMAC firmada), validado en nginx con `auth_request`.
- Extensión de Chrome que sube la cookie de sesión de starlink.com (`X-Ingest-Token`).
- `POST /api/v1/panel/cookie` para pegar la cookie a mano desde el panel.
- Servidor MCP opcional de solo lectura: resumen de flota, búsqueda de antenas por cliente y estado de sincronización.
- Cabecera `Content-Security-Policy` en la configuración de nginx.
- Integración continua (GitHub Actions): tests del backend, tipos y build del frontend, auditoría de dependencias de producción.
- Dependabot para pip, npm y GitHub Actions.

### Cambiado

- Next.js 14.1.0 → 16.4.2 y React 18 → 19 (React 18 ya está deprecado en Next 16).
- El dominio real se sustituye por `panel.ejemplo.org` en toda la documentación publicada.

### Corregido

- El cuadro "pegar cookie" del panel devolvía 401 en producción: apuntaba a la ruta de la extensión, que exige `X-Ingest-Token`. Ahora usa `POST /api/v1/panel/cookie`, detrás de la sesión del panel.
- El servidor MCP llamaba a endpoints que no existen. Ahora usa rutas reales del backend.
- El runbook instalaba Node desde apt, que en Ubuntu 22.04 es demasiado viejo para Next.js 16.

### Seguridad

- Next.js 14 arrastraba avisos sin parche (incluida ejecución remota de código y SSRF). Con 16.4.2 la auditoría de dependencias de producción queda en 0 vulnerabilidades.
- nginx deja de anunciar WebSocket upgrade al backend en producción.
- `mcp` se declara con una versión mínima parcheada.

### Eliminado

- Herramientas MCP inventadas (comandos de antenas y sesiones de campo) que llamaban a endpoints inexistentes.

### Limitaciones conocidas

- `requirements.txt` usa rangos `>=`: la instalación toma las versiones nuevas al instalar, no versiones fijas.
- La cookie de Starlink y su clave de cifrado viven en el mismo directorio (`session_store.py`): quien lea una, lee la otra.
