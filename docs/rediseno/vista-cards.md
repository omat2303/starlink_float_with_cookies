# Rediseño — Vista B: tarjetas con mini-gráficos

Fecha: 2026-10-30
Rama: `vista/cards`
Puerto de comparación: **http://localhost:3002**

## Qué se pidió

La segunda variante para comparar: mantener el panel en una sola pantalla pero
más vistoso, con tarjetas de métricas y mini-gráficos (referencia
[Statistics Card 10](https://21st.dev/@sean0205/components/statistics-card-10)),
funcionando contra el mismo backend.

## Qué se hizo

- **KPIs con ratio real** (`src/app/page.tsx`): 4 tarjetas con número grande,
  barra de progreso y detalle calculado con los datos del momento:
  - **Clientes** → `30 deben · 27 al día`, barra = % al día.
  - **Antenas** → `77 encendidas · 0 apagadas`, barra = % encendidas
    (`antenna.active`).
  - **Suspendidas** → `13% de las antenas`.
  - **Por vencer (7d)** → `2 en menos de 72 h`.
- **Histograma de vencimientos**: 7 barras, una por día desde hoy, contando los
  clientes cuyo `next_due_date` cae ese día. Es un conteo real, no una serie
  inventada; el tooltip dice la fecha y el total.
- **Tarjetas de cliente** (`ClientList.tsx`): misma tarjeta y misma tabla de
  datos, con borde izquierdo de color según lo urgente: rojo si debe o está
  suspendido, ámbar si vence en menos de 72 h, verde si está al día.
- **Estilo** (`globals.css`): fondo casi negro con dos halos (índigo/verde),
  tarjetas con degradado sutil y bordes `white/7%`, acento índigo en chips,
  botones y foco de inputs. Otra vez, los tokens viejos (`dark-*`, `accent-*`)
  se remapean en `tailwind.config.js` para no reescribir cada componente.
- **Buscador**: además de cliente, kit, nombre propio y SL, ahora encuentra por
  **número de cuenta** (`ACC-DF-…`) y por nombre de la cuenta.

## Por qué así

- Un histograma de vencimientos responde la pregunta que el panel no contestaba
  de un vistazo: *cuánto se cobra cada día de esta semana*. Se calcula en el
  servidor desde `/clientes`, sin endpoint nuevo ni consultas extra.
- El borde de color por tarjeta permite barrer la lista con el ojo: rojo = plata
  pendiente, ámbar = se viene, verde = tranquilo. No reemplaza los badges, los
  refuerza.
- Los ratios usan lo que ya viene en `/resumen` y `/clientes`; no se inventan
  tendencias ni comparaciones contra períodos que no tenemos.

## Verificación

- `npx tsc --noEmit`: sin errores.
- `npm run build`: ver commit de la rama.
- En Chrome/`localhost:3002`: 57 tarjetas de cliente, KPI con 57/77/10/15,
  histograma con 10 clientes en 7 días, sin errores de consola, y el filtro
  `Mixto` devuelve exactamente los 6 clientes mixtos.
- `/gestiones` sigue funcionando con el mismo estilo.
- Sin cambios de backend.

## Cómo levantarla

```powershell
# backend en :8000
cd frontend
npm install
npm run dev -- -p 3002
```

## Límites conocidos

- El histograma sólo mira `next_due_date` del cliente (el mínimo de sus cuentas):
  un cliente con dos cuentas que vencen en días distintos aparece una sola vez.
  Partirlo por cuenta requeriría decidir cuál se cobra primero; no se hizo.
- "Antenas encendidas" hoy da 100% porque todas reportan `active`; la barra queda
  llena y el dato pierde gracia, pero es el dato real.
