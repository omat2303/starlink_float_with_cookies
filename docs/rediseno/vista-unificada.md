# Vista unificada — AdminCN + gráficos de cards

Rama `vista/unificada`, puerto de desarrollo **3003**. No toca `main` ni las
otras dos variantes (`vista/admincn` en 3001, `vista/cards` en 3002).

## Por qué

Las dos variantes resolvían la mitad del problema cada una:

- **AdminCN**: sidebar fija, topbar, barra de sesión y tablas densas. Se navega
  bien, pero el estado del lote sólo se ve contando filas.
- **Cards**: KPIs con barra de proporción, histograma de vencimientos y acento
  por estado. Se lee de un golpe, pero sin sidebar se pierde la navegación.

Unificarlas no cuesta dependencias: en `vista/cards` los gráficos son `div`
con altura calculada y el logo es un SVG inline. No hay librería de charts que
importar. Se copia el marcado y se mantiene el `Shell` de AdminCN.

## Qué cambia

| Archivo | Cambio |
| --- | --- |
| `app/page.tsx` | 6 `Stat` planos → 4 `Kpi` con barra de ratio y detalle (deben/al día, encendidas/apagadas, % suspendidas, <72 h). Se agrega el histograma de vencimientos a 7 días. |
| `app/page.tsx` | Panel **Consumo del ciclo**: top 5 de antenas por % del plan usado. |
| `components/Donut.tsx` | Anillo SVG reutilizable (`stroke-dasharray`) con el % dentro. |
| `components/ClientList.tsx` | La celda "Ciclo" pasa de texto a anillo + GB consumidos / límite + acceso a los ciclos. |
| `lib/consumo.ts` | `cyclePct`, `isUnlimited`, `gb`: una sola definición de umbrales y formato. |

`Shell.tsx`, `layout.tsx` y `globals.css` no se tocan: la base visual sigue
siendo la de AdminCN.

## Por qué anillo y por qué no una línea histórica

El portal entrega **sólo la foto del ciclo actual** (`data_cycle_gb`,
`data_limit_gb`). Los 546 ciclos guardados en `cycles_json` tienen
`cycle_gb`/`limit_gb` en `null` en todos los casos. No hay serie temporal que
dibujar.

Con esos datos, un anillo de "% del plan usado" es honesto hoy. Una línea de
evolución mensual saldría vacía hasta acumular fotos propias; eso requiere una
tabla `consumo_snapshot` que el sync escriba en cada corrida y queda como fase 2,
fuera de esta rama.

## Umbrales (criterio propio, corregible)

| % usado | Color |
| --- | --- |
| < 70 % | indigo |
| 70–90 % | ámbar |
| > 90 % | rojo |
| ilimitado | indigo + `∞` |

Se considera ilimitado un `limit_gb` nulo o ≥ 100 000 GB, que es como Starlink
reporta los planes sin tope. Esos planes no entran al top 5: su porcentaje no
existe.

## Verificación

- `npx tsc --noEmit` → sin salida.
- `npm run build` → compilado, 4 rutas (`/`, `/_not-found`, `/gestiones`, `/login`).
- En `http://localhost:3003`: 4 KPIs con barra, histograma con 15 vencimientos,
  top 5 (98 %, 81 %, 69 %, 51 %, 39 %), 83 anillos (5 del panel + 78 filas),
  `/gestiones` carga y la consola no tiene errores.
- El buscador y los filtros son los mismos de AdminCN, sin cambios.

El anillo reporta el % que da el portal; con datos reales el primero marca 98 %
sobre 100 GB, que es exactamente el caso que antes había que abrir tarjeta por
tarjeta para encontrar.
