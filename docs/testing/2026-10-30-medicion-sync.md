# 2026-10-30 — Medición del sync (por qué tarda ~90 s)

Documento de **medición**, no de cambio. Nada de código tocado todavía: la
decisión de paralelizar (y con eso tocar `worker.py`) queda pendiente.

## Método

Script temporal (no queda en el repo) usando la sesión real y `PortalClient`,
midiendo cada llamada por separado con `time.perf_counter()`. Sólo GETs de
lectura: los mismos que ya hace el sync. Entorno: casa, TZ UTC-3.

## Línea base (2026-10-30)

`accounts()` → **0,71 s** para 58 cuentas.

Por cuenta (3 cuentas medidas, todas con 1 línea; tiempos estables):

| Paso | Tiempo | Veces | Total |
| --- | --- | --- | --- |
| `refresh()` al activar la cuenta (renueva `Starlink.Com.Access.V1`) | ~0,72 s | 1 por cuenta | **~40 s** |
| `service-lines` | ~0,38 s | 1 por cuenta | ~21 s |
| `balance` | ~0,33 s | 1 por cuenta | ~18 s |
| `usage` | ~0,18 s | 1 por línea | ~13 s |

Con 56 cuentas / 74 antenas: `56 × (0,72 + 0,38 + 0,33) + 74 × 0,18 + 0,71`
≈ **93 s**. El worker registra 82–90 s por ciclo (`_dev_logs/backend.err.log`,
cada 2 h, `errors: 0`). Coincide.

## Diagnóstico

**El 100 % del tiempo es latencia HTTPS en serie contra starlink.com**: ~219
peticiones, ~0,4 s cada una. No es la base (SQLite local, consultas indexadas),
no es el panel (un solo GET), no son reintentos (0 errores).

Detalle que explica por qué cada cuenta cuesta tanto: activar una cuenta exige
re-emitir el token (`refresh()`), ~0,72 s, y **eso se paga una vez por cuenta**
porque `service-lines` y `usage` responden según el token vigente.

## Optimización propuesta (sin aprobar)

Fase de red **concurrente**, escritura a la DB igual que hoy:

1. `asyncio.gather` sobre las cuentas con un `Semaphore(N)`.
2. Un `PortalClient` **por cuenta** (la cookie activa y el token son estado
   mutable del cliente: no se puede compartir entre cuentas en paralelo).
3. La fase de upsert sigue en un solo hilo/coroutine con la misma `Session` y el
   `commit()` por cuenta de hoy (SQLite tiene un solo escritor).

Ganancia esperada (aritmética sobre los mismos ~1,6 s por cuenta):

| Concurrencia | Tiempo estimado |
| --- | --- |
| 1 (hoy) | ~90 s |
| 3 | ~32 s |
| 5 | ~20 s |
| 8 | ~13 s |

## Riesgos a considerar antes de decidir

- **Anti-abuso de Starlink.** No expone cabeceras de rate-limit (`x-cache`,
  `cache-control` solamente). 5 sesiones concurrentes sobre la misma cookie SSO
  pueden devolver 429 o forzar la rotación de la sesión → habría que re-pegar la
  cookie. Mitigación: concurrencia conservadora (3–5), reintento con espera y
  bajar a 1 si aparecen 429.
- **Rotación de cookie.** Si `/api/auth/auth/user` emite `Set-Cookie` nuevo, cada
  cliente paralelo se queda con su copia; la sesión guardada podría quedar
  desincronizada. Hay que verificar con una prueba corta (3 cuentas) y comprobar
  que la sesión sigue viva después.
- **`worker.py` es intocable por regla del repo.** Paralelizar exige levantarla.
  Alternativa que NO lo toca: `POST /sync` responde 202 al instante y el panel
  hace polling de `sync-status` (la UI deja de colgarse 90 s, pero el sync sigue
  tardando lo mismo).
- **Memoria/ficheros:** N clientes httpx abiertos a la vez (trivial con N≤8).

## Cómo se verifica (si se decide hacer)

Misma medición, mismo script, antes y después; y `time POST /api/v1/sync`.
Se conserva sólo si baja ≥2× y `pytest` sigue verde. Si no, se revierte (un
cambio neutro no se queda).

## Registro de intentos

| Idea | Antes → Después | Veredicto | Motivo |
| --- | --- | --- | --- |
| (pendiente de aprobación) | 90 s → ? | — | — |
