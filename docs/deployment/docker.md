# Despliegue con Docker (y Portainer)

Este repo incluye un `docker-compose.yml` pensado para que **cualquiera** pueda levantar StarPanel con HTTPS automático, sin reescribir la puerta que ya está auditada. El nombre del proyecto es `starpanel_docker`.

**Arquitectura:** `caddy` (único contenedor publicado en 80/443, pide y renueva el certificado Let's Encrypt solo) → `nginx` (guarda la puerta: `auth_request`, anti-CSRF, `limit_req`, CSP, deniega `/_next/image` y ficheros sensibles) → `frontend` y `backend` (solo visibles en la red interna). Los datos (SQLite + bóveda `.session.*`) van a un volumen (`starpanel_data`) para que sobrevivan a cualquier `down/up`.

## 1) Requisitos

- Docker Engine + Docker Compose (Docker Desktop, Portainer o Linux).
- Dominio público apuntando a la IP del VPS (registro A). Para probar **localmente** sin dominio, `DOMAIN=localhost` hace que Caddy use su CA interna (`curl -k`).
- Puertos `80` y `443` libres en el host.

## 2) Puesta en marcha (línea de comandos)

```bash
# 1. Clonar el repo en el VPS
git clone https://github.com/omat2303/starlink_float_with_cookies.git
cd starlink_float_with_cookies

# 2. Copiar el ejemplo de variables
cp deploy/docker.env.example .env

# 3. Editar .env: DOMAIN, ACME_EMAIL y generar los secretos
# Generar los 3 secretos con tu contraseña:
docker compose run --rm backend python make_secrets.py 'TU_CONTRASEÑA'

# 4. Construir e iniciar
docker compose up -d --build

# 5. Comprobar que solo se publican 80/443 (crítico)
docker compose ps --format "{{.Service}} {{.Ports}}"

# 6. Abrir https://TU-DOMINIO (o https://localhost con -k)
```

**Importante:** `backend` y `frontend` **no deben** tener puertos publicados. El hecho de que solo `caddy` exponga 80/443 es lo que impide saltarse la puerta de nginx.

### Extensión de Chrome (una sola vez)

La extensión es la única vía **automática** para traer la cookie de Starlink
(Chrome 136+ cifra las cookies en disco, así que leer el fichero `Cookies` no
sirve):

1. Descarga [`docs/downloads/starpanel-extension-v1.1.0.zip`](../downloads/starpanel-extension-v1.1.0.zip)
   y descomprime (botón *Download raw* de GitHub; no hace falta clonar el repo).
2. Pon tu dominio (el de `DOMAIN`) en `extension/manifest.json` y
   `extension/background.js`: el zip trae `panel.ejemplo.org` de ejemplo.
3. `chrome://extensions` → **Modo de desarrollador** → **Cargar descomprimida**
   → elige la carpeta `extension/`.
4. Abre sus opciones y pega el `INGEST_TOKEN` del `.env`.
5. Con starlink.com abierto en ese mismo Chrome, pulsa **Traer cookie y
   sincronizar** en el panel.

## 3) Portainer

Portainer sirve para gestionar Docker desde web. El compose incluye un perfil `portainer` (apagado por defecto). Para usarlo:

1. Tener Docker ya corriendo en el host.
2. Desde la terminal (o desde Portainer "Git Repo" stack) usar `--profile portainer`.
3. **Nunca** publicar el puerto 9000/9443 a internet. Lo más seguro: solo localhost (`127.0.0.1:9443:9443`) + túnel SSH, o detrás de otro proxy. Dar acceso a `/var/run/docker.sock` equivale a **root** del host.

## 4) Por qué este diseño

- **Reutilizamos lo auditado.** La lógica de `auth_request`, anti-CSRF, rate-limit y CSP vive exactamente en `deploy/docker/nginx.conf` (adaptado mínimamente). No reimplementamos la puerta: reducimos el riesgo de un desliz de seguridad.
- **TLS automático.** Caddy pide/renueva certificados sin `certbot`. En producción solo hace falta `DOMAIN` y `ACME_EMAIL`.
- **Sólo el borde publica.** Si alguien publica accidentalmente `backend:8000` en el host, la puerta se pierde. Por eso en este stack **sólo** `caddy` publica puertos.
- **Datos fuera del código.** `SESSION_DIR=/data` y `DATABASE_URL=sqlite:////data/starlink_fleet.db` mueven `.session.enc/.session.key` y `starlink_fleet.db` a un volumen nombrado (`starpanel_data`). Así el código puede actualizarse (`git pull && docker compose up -d --build`) sin tocar los datos.
- **Build reproducible para SSR.** `NEXT_PUBLIC_API_URL` se pasa como `build-arg` (`http://backend:8000/api/v1`). El SSR dentro de `frontend` apunta siempre al backend interno; si estuviera `localhost:8000` fallaría.

## 5) Actualizar y backups

```bash
# actualizar
git pull
docker compose up -d --build

# backup del volumen (SQLite + sesión cifrada)
docker run --rm -v starpanel_docker_starpanel_data:/data -v "$PWD/backups:/backup" alpine tar czf /backup/starpanel_data_$(date +%F_%H-%M-%S).tgz -C /data .
```

## 6) Resolución de problemas

- **No saca certificado:** `DOMAIN` debe resolver a la IP pública, 80 abierto a internet (Caddy usa HTTP-01) y `ACME_EMAIL` rellenado. Con `DOMAIN=localhost` usa CA interna.
- **Panel "vacío":** comprueba que el `build-arg` funcionó (ver T3 en el plan) y que nginx llega a `backend:8000`. El backend solo responde por red interna.
- **No puedo hacer login:** en producción `APP_ENV=production` exige los 3 secretos; revisa `.env`. El navegador debe poder acceder por HTTPS y el cookie es `Secure` (funciona con https://localhost).
- **Ports publicados erróneos:** `docker compose ps --format "{{.Service}} {{.Ports}}"` debe mostrar **sólo** `caddy` con `0.0.0.0:80->80`, `0.0.0.0:443->443`. Cualquier otro servicio con un `0.0.0.0:...` es una brecha.