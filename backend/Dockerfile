# Backend StarPanel (FastAPI + uvicorn).
# Los datos (SQLite + boveda de sesion) viven en /data, que docker-compose
# monta como volumen para que sobrevivan a recrear el contenedor.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
# shortcut: requirements.txt usa rangos >=, asi que dos builds en fechas
# distintas pueden traer versiones distintas. Fijar cuando un build falle solo.
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data \
    && chown -R app:app /data

USER app

EXPOSE 8000

# --proxy-headers + --forwarded-allow-ips: el backend solo es alcanzable desde
# la red interna (nginx), nunca publicado en el host.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
