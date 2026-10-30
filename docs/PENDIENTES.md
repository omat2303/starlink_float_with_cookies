# Actividades pendientes

Ideas aprobadas para hacer **más adelante**, con lo necesario para decidir sin
volver a investigar. No son bugs abiertos.

---

## P-01 · Sync en paralelo (bajar de ~90 s a ~20 s)

**Estado:** pendiente de aprobación. No hay código escrito.
**Medición y plan:** [docs/testing/2026-10-30-medicion-sync.md](testing/2026-10-30-medicion-sync.md)
**Fecha de la medición:** 2026-10-30 (56 cuentas / 74 antenas)

### Lo que se sabe

- El sync tarda ~90 s porque son ~219 peticiones HTTPS **en serie** a
  starlink.com (~0,4 s cada una). La base y el panel no pesan.
- El gasto por cuenta: `refresh()` del token 0,72 s + `service-lines` 0,38 s +
  `balance` 0,33 s + `usage` 0,18 s por línea.
- Pidiendo 5 cuentas a la vez la estimación es ~20 s (aritmética sobre los
  tiempos medidos, no probado aún).

### La decisión que falta

**¿Se toca `backend/worker.py`?** Es el único archivo donde vive el bucle
secuencial, y hoy está bajo la regla de no modificarlo. La alternativa sin
tocarlo (`POST /sync` → 202 + polling en el panel) no acelera nada: sólo evita
que la UI quede colgada 90 s.

### Si se aprueba: qué se hace (resumen)

1. `_fetch_account()` y `_fetch_all()` nuevas en `worker.py`: fase de red
   concurrente con `Semaphore(SYNC_CONCURRENCY)`, un `PortalClient` por cuenta
   (la cookie activa y el token son estado mutable del cliente).
2. `sync_once(client, db, concurrency=..., cookies=...)`: sin `cookies` se
   comporta exactamente como hoy (los tests de `test_worker.py` no se tocan).
3. La escritura a la DB queda igual: una sola coroutine, `commit()` por cuenta.
4. Activar desde `main.py:380` (botón) y `worker.py:148` (loop de 2 h).

### Riesgos y mitigación

| Riesgo | Mitigación |
| --- | --- |
| 429 / anti-abuso de Starlink (no expone cabeceras de rate-limit) | `SYNC_CONCURRENCY` por env; si aparece, `=1` sin tocar código |
| Rotación de la cookie SSO por `refresh()` concurrente | concurrencia 5; comprobar la sesión después de la primera corrida real |
| Un cliente TLS por cuenta | si molesta, pool de N clientes reusados (~10 líneas más) |
| Corte a mitad de sync | se pierde la corrida, no datos; el siguiente sync la rehace |

### Criterio de aceptación

- `time POST /api/v1/sync` baja ≥2× (de ~90 s a ≤45 s).
- `pytest` verde (51 + 2 tests nuevos del camino concurrente).
- La sesión guardada sigue viva después del primer sync concurrente.
- Si no baja, se revierte (un cambio neutro no se queda).

### Vuelta atrás

`worker.py` está trackeado: `git checkout -- backend/worker.py`. Además, dejar
copia en `_dev_logs\worker.py.bak` antes de editar.

### Cómo retomar

1. Releer la medición y volver a correr el mismo script (los tiempos del portal
   cambian).
2. Confirmar si se levanta o no la regla sobre `worker.py`.
3. Implementar, medir igual que la línea base, y anotar el resultado en el
   "Registro de intentos" del doc de medición.
