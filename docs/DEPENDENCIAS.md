# Revisión de dependencias (PRs de Dependabot)

**Fecha:** 2026-10-18 · **Base:** `0ec2e97`

Los PRs abiertos se revisaron contra su CI y su diff. Todos los que aparecen
como "merge" tienen los checks en verde (backend 3.10/3.12, frontend, Docker
build). **Fusionarlos requiere sesión de GitHub**: el agente no tiene
credenciales y no puede mergear ni comentar los PRs.

## Veredictos

| PR | Cambio | Veredicto | Motivo |
| --- | --- | --- | --- |
| 1 | `actions/setup-python` 5 → 7 | **Merge** | CI verde; action oficial |
| 2 | `actions/checkout` 4 → 7 | **Merge** | CI verde; action oficial |
| 3 | `actions/setup-node` 4 → 7 | **Merge** | CI verde; action oficial |
| 4 | `uvicorn` ≥0.54 | **Merge** | CI verde; sólo servidor |
| 5 | `mcp` 1.9.4 → **2.3.0** | **Cerrado** | 2.x eliminó `FastMCP`: `mcp.server.fastmcp` ahora lanza `ModuleNotFoundError`. Dependabot lo cerró solo al fijar `<2` y abrió #13 |
| 6 | `sqlalchemy` ≥2.1.4 | **Cerrado** | Reemplazado por #14 |
| 7 | `pytest` ≥9.1.1 | **Merge** | CI verde |
| 8 | `tailwindcss` 3.4 → **4.3** | **No mergear** | El check de frontend falla: Tailwind 4 cambia configuración y sintaxis CSS; migración propia |
| 9 | `pytest-asyncio` ≥1.4 | **Merge** | CI verde |
| 10 | `postcss` 8.5.30 | **Merge** | CI verde; patch |
| 11 | `@types/node` 20 → 26 | **Esperar** | Los tipos se adelantan al runtime real (Node 20 en CI, 24 local); sin beneficio y con riesgo de tipos que no existen en runtime |
| 12 | `typescript` 5.9 → 7.0.2 | **Merge con cautela** | CI de tipos y build en verde, pero es un salto major del compilador: probar `npm run build` local antes; revertir si aparece comportamiento raro |
| 13 | `mcp` ≥1.30.0,<2 | **Merge** | Es exactamente la versión probada localmente (1.30.0): los 3 tests de `test_mcp_server.py` pasan |
| 14 | `sqlalchemy` ≥2.1.5 | **No mergear** | Toda la línea 2.1 exige Python ≥3.11 y el CI/runbook mantienen 3.10; el check de 3.10 falla |

## Orden sugerido

1. Actions (1, 2, 3) — no tocan código.
2. Patch (10), luego runtime backend (4) y `mcp` 1.30 (13).
3. Herramientas de test (7, 9).
4. TypeScript (12), con build local previo.
5. Cerrar 8 con el motivo de arriba; 14 no se mergea mientras el runbook siga en 3.10; 11 queda en espera.

## Cambios hechos para que esto no vuelva a pasar

- `backend/requirements.txt`: `mcp>=1.9.4,<2`. Antes una instalación limpia
  resolvía 2.x y dejaba el servidor MCP opcional roto sin aviso.
- `backend/requirements.txt`: `sqlalchemy>=2.0.0,<2.1`. La línea 2.1 exige
  Python ≥3.11 y el runbook apunta a Ubuntu 22.04 (3.10).
- `.github/dependabot.yml`: ignora majors de `mcp` (el pin ya lo impide, esto
  evita el PR recurrente).
- `backend/tests/test_mcp_server.py`: importa `mcp_server.py` y verifica sus
  tres herramientas; con `mcp` 2.x falla en vez de romperse en silencio.
  Requiere `mcp` instalado (CI lo hace); si no está, el módulo se saltea.
