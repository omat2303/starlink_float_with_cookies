# Filtros "Deben" y "Al día"

Fecha: 2026-10-30
Archivo tocado: `frontend/src/components/ClientList.tsx` (nada de backend)

## Qué se pidió

Ver de un vistazo quién debe plata, separado de quien está en 0, sin perder los
filtros que ya existían. Ejemplo del pedido: si debe 40 USD, que aparezca en la
lista de deudores; y que los que pagan el día 4 salgan primero.

## Qué se hizo

- Dos chips nuevos: **Deben (N)** y **Al día (N)**, con su contador, junto a
  Todas / Suspendidas / Pausadas / Vencen <72h. Son excluyentes, como los demás.
- `owes(cliente)` = alguna cuenta con `balance_due > 0`. El saldo vive en la
  **cuenta**, no en la antena, así que no se puede decir "esta antena debe 40":
  un cliente con 3 antenas y una cuenta que debe 40 entra entero, con sus 3
  antenas. Los `balance_due: null` cuentan como 0.
- En las dos vistas de saldo la lista se ordena por `next_due_date` ascendente
  (los que pagan antes van primero) y los clientes sin fecha de pago van al
  final. En Todas y en el resto de los filtros el orden no cambia.
- El buscador de siempre sigue funcionando combinado con el filtro.

## Por qué así

- Sin cambios de backend: `balance_due` y `next_due_date` ya vienen en
  `GET /clientes`. Un endpoint nuevo para esto habría sido código muerto.
- Ordenar por fecha y no por monto: el pedido fue "si se paga el 4, esas
  primero". Ordenar por monto no dice cuándo cobrar.
- Chips separados en vez de dos secciones en una misma vista: se pidió
  explícitamente "separados, botones diferentes", y así cada lista tiene su
  contador y se puede alternar con un clic.

## Verificación

- `npx tsc --noEmit` en `frontend/`: sin errores.
- Contra los datos reales (`GET /clientes`, 2026-10-30): 57 clientes →
  **30 Deben / 27 Al día**, y los primeros deudores por fecha son los del
  `2026-11-04` (100, 70, 80 y 60 en sus monedas), luego `2026-11-06` (40).
  Que Deben + Al día sume el total confirma que la clasificación no pierde
  clientes.
- Verificado en el panel real (`localhost:3000`, Chrome): los chips aparecen
  como `Deben (30)` y `Al día (27)`, y al activar Deben la lista empieza por los
  que vencen el `04/11/2026` (pedro romero, alber brito 70,00 USD, jesica tovar),
  no por orden alfabético ni de monto.

## Límites conocidos

- No hay total adeudado en el encabezado del panel: los saldos vienen en
  monedas distintas (USD/UYU) y sumarlos daría un número falso.
- "Deben" agrupa cuentas de distintas monedas sin convertir; el detalle por
  cuenta ya muestra moneda y saldo.
