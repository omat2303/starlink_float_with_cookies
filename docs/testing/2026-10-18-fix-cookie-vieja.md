# Prueba manual — 2026-10-18 (fix cookie vieja, extensión 1.1.3)

Registro de la verificación end-to-end tras el fix de la extensión
(`ecaf448`). Servicios arrancados con el mismo comando canónico de
`StarPanel.bat`.

## Qué se probó

| Paso | Resultado |
| --- | --- |
| Backend `127.0.0.1:8000` (venv uvicorn, `--env-file .env`) | ✅ arrancó |
| `POST /api/v1/auth/login` con `x=` y token válido | ✅ **400** — el nuevo guard rechaza cookies sin valor (antes pisaba la sesión real) |
| `POST /api/v1/auth/login` sin `X-Ingest-Token` | ✅ **401** — el token es obligatorio |
| `GET /api/v1/auth/status` | ✅ `authenticated: true` — la extensión reenvió la sesión nueva con éxito |
| Extensión v1.1.3 en Chrome (badge OK, token en Opciones) | ✅ envió la cookie nueva |
| `sync_state` | ✅ 2026-10-18 20:34:44 UTC (17:34 local) — sync posterior al restart |
| Datos en panel | ✅ **57 cuentas / 72 antenas** (antes del fix: 54 congelados desde las 14:58) |
| Frontend `localhost:3000` | ✅ carga sin errores de consola |
| Filtro "Suspendidas (10)" | ✅ activa y filtra la lista |
| Botón Salir / búsqueda presentes | ✅ |

## Conclusión

El bug "toma una cookie vieja y no la nueva sesión" quedó cerrado: la
extensión 1.1.3 deduplica por nombre (gana la más reciente), el backend ya no
acepta payloads de prueba que borren la bóveda, y el panel muestra datos
sincronizados con la sesión recién iniciada.

Screenshot automático no disponible (la ventana de Chrome debe estar visible
en el escritorio); la verificación visual se hizo vía snapshot de
accesibilidad y evaluate JS.
