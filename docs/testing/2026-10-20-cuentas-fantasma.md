# 2026-10-20 — Cuentas borradas en Starlink que seguían apareciendo

## Síntoma

El panel mostraba **57 cuentas / 55 clientes**, pero la sesión del portal devolvía
**49**. Eran cuentas ya borradas en Starlink que seguían listadas.

## Causa

`worker.sync_once` sólo hace *upsert*: recorre lo que devuelve el portal y crea o
actualiza filas, pero **nunca mira lo que sobra en la base**. `GET /clientes` y
`GET /resumen` listan todas las filas de `accounts`, así que lo que desaparece
del portal queda visible para siempre.

Comprobado contra la base real: las 8 cuentas de más (Leida Jimenez, Jesus
Colon ×2, Julio Cesar Perez, Marcos Perez, MAIDELIS VASQUES, massimo muzzo,
daniel carpanzo) no venían en `/api/accounts/v3/accounts/contact` y no tenían
ninguna antena.

## Cambios

| Archivo | Cambio |
| --- | --- |
| `backend/models.py` | `Account.hidden_at` (nullable) |
| `backend/database.py` | `ensure_schema` agrega la columna en bases ya creadas |
| `backend/main.py` | `_reconcile_accounts`: oculta lo que el portal ya no devuelve y vuelve a mostrar lo que reaparece; `/clientes` y `/resumen` filtran `hidden_at IS NULL` |
| `backend/tests/test_api.py` | test de ocultar / reaparecer |

Por qué **ocultar y no borrar**: si el portal devuelve una lista incompleta (o se
pega una cookie de otra sesión) borrar filas perdería nombres propios,
`custom_name` y el historial. Ocultar es reversible. Además el sync exige
`len(live) >= stats["accounts"]`: si la segunda consulta trae menos cuentas que
las que acaba de sincronizar, no oculta nada.

## Límite conocido

La reconciliación va en `POST /api/v1/sync` (el botón *Sincronizar ahora*).
`worker.py` no se toca (regla del repo), así que el sync automático de cada 2 h
actualiza datos pero **no** limpia fantasmas: hay que pulsar el botón una vez.

## Verificación

```
POST http://127.0.0.1:3000/api/sync → 200 en 82 s {"accounts":49,...}
GET  /api/v1/resumen → {"clientes":48,"cuentas":49,"antenas":72,...}
Panel (Chrome real)  → CLIENTES 48 / CUENTAS 49 / ANTENAS 72
```

`pytest`: 51 passed, 1 skipped.
