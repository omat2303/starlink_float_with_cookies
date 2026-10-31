# Rediseño — Vista A: AdminCN (menú lateral)

Fecha: 2026-10-30
Rama: `vista/admincn`
Puerto de comparación: **http://localhost:3001**

## Qué se pidió

Una de las dos variantes para comparar el rediseño del panel: el look clásico de
los admin dashboards de shadcn (referencia
[AdminCN](https://21st.dev/community/templates/admincn-shadcn-admin-dashboard-template)),
aplicado al panel real, funcionando contra el mismo backend.

## Qué se hizo

- **Marco nuevo** (`src/components/Shell.tsx`): sidebar fija de 240 px con logo,
  navegación (Panel / Gestiones y costos) y "Salir" al pie; topbar sticky con el
  título de la sección y el `SessionBar` (cookie + sincronizar) a la derecha.
  El login queda fuera del marco, a pantalla completa.
- **`layout.tsx`**: envuelve todo en `Shell` y deja de renderizar `PanelMenu`
  (el botón flotante de salir se reemplazó por el del sidebar). `PanelMenu.tsx`
  sigue en el repo sin usar; no se borró para no romper otras ramas.
- **`page.tsx` / `gestiones/page.tsx`**: se les quitó el header propio (ahora lo
  pone `Shell`) y quedan sólo los KPIs y el contenido. Los 6 KPIs pasaron a
  tarjetas con etiqueta chica y número grande; Suspendidas y Vence <72h en rojo,
  Por vencer en ámbar.
- **`globals.css` + `tailwind.config.js`**: paleta zinc/shadcn. En vez de
  reescribir cada componente, los tokens viejos (`dark-*`, `accent-*`) apuntan a
  la escala zinc, así `ClientList`, `GestionTable` y `SessionBar` cambian de look
  sin tocarlos. Los chips de filtro y los bordes de tabla se ajustaron a mano en
  `ClientList`.

- **Buscador**: además de cliente, kit, nombre propio y SL, ahora encuentra por
  **número de cuenta** (`ACC-DF-…`) y por nombre de la cuenta.

## Por qué así

- La navegación actual era un link "Gestiones y costos" en el header y un botón
  "Salir" flotante abajo a la izquierda. Con sidebar, las dos cosas viven en su
  lugar y el panel gana una columna fija para crecer (más secciones) sin tocar
  el resto.
- Remapear los tokens en Tailwind es el cambio más barato que logra un rediseño
  coherente: cero dependencias nuevas, cero cambios de lógica, y si la variante
  no se elige, se descarta la rama completa.
- No se instaló shadcn ni Radix: el panel es chico (2 páginas) y sumar ese
  caudal de dependencias para el mismo resultado visual no se justifica.

## Verificación

- `npx tsc --noEmit`: sin errores.
- `npm run build`: ver commit de la rama.
- En Chrome/`localhost:3001`: renderiza con datos reales (57 clientes, 77
  antenas, 10 suspendidas), sin errores de consola, `/gestiones` carga la tabla
  de costos, y el filtro `Mixto` devuelve los 6 clientes correctos.
- Sin cambios de backend: mismos endpoints, misma cookie, mismo sync.

## Cómo levantarla

```powershell
# backend en :8000
cd frontend
npm install
npm run dev -- -p 3001
```

## Límites conocidos

- El sidebar es fijo de 240 px: en pantallas menores a ~900 px el contenido se
  angosta. No se agregó versión colapsable porque el panel es Web/PC.
- `PanelMenu.tsx` quedó sin uso en esta rama.
