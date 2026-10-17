# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y versionado [SemVer](https://semver.org/lang/es/).

Todavía no hay una instancia desplegada: ver [docs/deployment](docs/deployment/README.md).

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
