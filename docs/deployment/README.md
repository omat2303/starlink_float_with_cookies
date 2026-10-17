# StarPanel — despliegue en VPS

Guía para dejar el panel en `https://panel.ejemplo.org` sin la puerta abierta.

> **Estado: sin desplegar.** No hay ninguna instancia pública en funcionamiento.
> Los comandos de abajo son la receta a seguir; sustituye `panel.ejemplo.org` por
> tu dominio real en cada paso (nginx, certbot, DNS y `PANEL_ORIGIN`).

## Arquitectura

```
navegador ──TLS──> nginx ──> Next.js  :3000   (páginas, detrás de auth_request)
                     │
                     ├──> FastAPI :8000       (API, detrás de auth_request)
                     └──> /api/auth/login      (extensión, X-Ingest-Token)

backend :8000 y frontend :3000 escuchan SÓLO en 127.0.0.1 (nunca expuestos).
```

Dos puertas independientes:
1. **Panel (OG)** — contraseña → cookie `sp_session` firmada (HMAC), httpOnly/Secure.
   nginx valida la cookie con `auth_request` en cada petición.
2. **Extensión** — sube la cookie de Starlink con `X-Ingest-Token`.

## 1. Requisitos

```bash
sudo apt update
sudo apt install -y nginx python3-venv python3-pip certbot python3-certbot-nginx fail2ban

# Node 20 desde NodeSource: el de apt en Ubuntu 22.04 es viejo y Next.js 16
# exige >= 20.9.
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

DNS: un registro `A` de `panel.ejemplo.org` apuntando a la IP del VPS.

## 2. Código y estructura

```bash
sudo mkdir -p /opt/starpanel
# copiar el repo a /opt/starpanel  (git clone o scp)
# el chown va DESPUÉS de copiar, si no los ficheros quedan de root y `npm ci` falla
sudo chown -R www-data:www-data /opt/starpanel
```

Backend:

```bash
cd /opt/starpanel/backend
sudo -u www-data python3 -m venv venv
sudo -u www-data venv/bin/pip install -r requirements.txt
```

Need: el backend usa SQLite (`starlink_fleet.db`) y la carpeta debe ser escribible
por `www-data` (la unidad ya le da `ReadWritePaths`).

Frontend:

```bash
cd /opt/starpanel/frontend
sudo -u www-data npm ci
sudo -u www-data npm run build        # el build NO necesita el backend
```

## 3. Secretos

```bash
cd /opt/starpanel/backend
sudo -u www-data venv/bin/python make_secrets.py 'TU_CONTRASEÑA_FUERTE'
```

Copia la salida a `/opt/starpanel/backend/.env` (plantilla: `deploy/backend.env.example`):

```bash
sudo cp deploy/backend.env.example /opt/starpanel/backend/.env
sudo nano /opt/starpanel/backend/.env      # pega los tres valores
sudo chown www-data:www-data /opt/starpanel/backend/.env
sudo chmod 600 /opt/starpanel/backend/.env
```

Frontend:

```bash
sudo cp deploy/frontend.env.example /opt/starpanel/frontend/.env.production
```

Con `APP_ENV=production`, el backend **no arranca** si falta alguno de los tres secretos.

## 4. systemd

```bash
sudo cp deploy/starpanel-backend.service.example  /etc/systemd/system/starpanel-backend.service
sudo cp deploy/starpanel-frontend.service.example /etc/systemd/system/starpanel-frontend.service
sudo systemctl daemon-reload
sudo systemctl enable --now starpanel-backend starpanel-frontend
systemctl status starpanel-backend starpanel-frontend --no-pager
```

## 5. nginx + TLS

El conf del repo ya trae el bloque 443 con `ssl_certificate`, así que **primero hay
que emitir el certificado**: si copias el conf final antes, `nginx -t` falla porque
el `.pem` todavía no existe. Orden correcto:

```bash
# 5a) Arranque mínimo por HTTP, sólo para responder el challenge de Let's Encrypt
sudo cp docs/deployment/nginx-starpanel-limits.conf /etc/nginx/conf.d/starpanel-limits.conf
sudo tee /etc/nginx/sites-available/starpanel > /dev/null <<'EOF'
server {
    listen 80;
    server_name panel.ejemplo.org;
    location / { return 200 "ok"; }
}
EOF
sudo ln -sf /etc/nginx/sites-available/starpanel /etc/nginx/sites-enabled/starpanel
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# 5b) Certificado (añade el bloque 443 y reescribe el 80 con el redirect)
sudo certbot --nginx -d panel.ejemplo.org

# 5c) Ahora sí, el conf definitivo del repo (ya encuentra los .pem)
sudo cp docs/deployment/nginx-starpanel.conf /etc/nginx/sites-available/starpanel
sudo nginx -t && sudo systemctl reload nginx
```

## 6. Firewall y fail2ban

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

fail2ban para el login (opcional pero recomendado): crea
`/etc/fail2ban/jail.d/starpanel.local`

```ini
[starpanel]
enabled = true
port = http,https
filter = starpanel
logpath = /var/log/nginx/access.log
maxretry = 10
findtime = 600
bantime = 3600
```

y `/etc/fail2ban/filter.d/starpanel.conf`

```ini
[Definition]
failregex = ^<HOST> .* "POST /api/panel/session HTTP/[0-9.]+" 401
ignoreregex =
```

```bash
sudo systemctl restart fail2ban
```

## 7. Extensión de Chrome

1. Carga `extension/` como extensión sin empaquetar (`chrome://extensions` → modo desarrollador).
2. Abre las opciones de la extensión y pega el `INGEST_TOKEN` del `.env`.
3. En el panel (`https://panel.ejemplo.org`), pulsa **Traer cookie y sincronizar**
   con la sesión de starlink.com abierta en el mismo perfil de Chrome.

## 8. Verificación

```bash
# Sin sesión: el panel redirige al login y la API responde 401.
curl -sI https://panel.ejemplo.org/          | head -1   # 302 → /login
curl -s  -o /dev/null -w '%{http_code}\n' https://panel.ejemplo.org/api/v1/clientes   # 401
curl -s  -o /dev/null -w '%{http_code}\n' https://panel.ejemplo.org/api/auth/login -X POST  # 401

# Tipos MIME y HSTS.
curl -sI https://panel.ejemplo.org/login | grep -Ei 'strict-transport|x-content-type|x-frame'

# El backend no está expuesto:
curl -s -o /dev/null -w '%{http_code}\n' http://<IP>:8000/api/v1/clientes   # timeout/refused
```

En el navegador: entra con la contraseña, el panel carga; `Salir` vuelve al login.

## Actualizar

```bash
cd /opt/starpanel && sudo -u www-data git pull
sudo -u www-data backend/venv/bin/pip install -r backend/requirements.txt
sudo -u www-data bash -c 'cd frontend && npm ci && npm run build'
sudo systemctl restart starpanel-backend starpanel-frontend
```
