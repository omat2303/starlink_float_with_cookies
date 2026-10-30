# Filtros por país y por tipo de servicio

Fecha: 2026-10-30
Archivo tocado: `frontend/src/components/ClientList.tsx` (nada de backend)

## Qué se pidió

Separar por país (Venezuela, Uruguay, etc.) y por tipo de cuenta: sólo
residenciales, sólo itinerantes, y las que tienen ambas juntas. Lo que está en
espera o pausado va en un mismo grupo.

## Qué se hizo

Dos filas de chips nuevas, debajo de los filtros de estado (Todas, Deben, Al día,
Suspendidas, Pausadas, Vencen <72h). Se combinan entre sí y con los de arriba
(AND): "VE" + "Mixto" + "Deben" muestra los mixtos venezolanos que deben.

- **País**: `Todos` y un chip por cada `region_code` presente en los datos,
  ordenados por cantidad. Hoy: VE (42), UY (10), CO (3), PE (1), CL (1), AR (1).
  No hay países escritos a mano: si mañana aparece uno nuevo, sale solo.
- **Tipo**:
  - `Residencial` (24): todas sus antenas con plan `Residencial...`.
  - `Itinerante` (24): todas con plan `Itinerante...`.
  - `Mixto` (6): tiene antenas de las dos. Sigue siendo **una sola tarjeta** con
    sus cuentas juntas, como se pidió.
  - `En espera / pausadas` (3): clientes sin ninguna antena residencial ni
    itinerante, es decir con plan `Modo de espera` (pausadas/standby). Un cliente
    con una antena pausada **y** una residencial cuenta como residencial: la
    pausa no lo saca de su tipo real.

## Por qué así

- `region_code` está en la cuenta, `plan` en la antena: el filtro de país mira
  las cuentas y el de tipo mira las antenas del cliente completo. El saldo y el
  vencimiento ya se mostraban a nivel de cuenta, así que no hay que tocar el
  backend ni los parsers.
- "En espera / pausadas" junto, como se pidió: el portal devuelve `Modo de
  espera` como plan, que no dice si antes era res o iti, y partirlo en dos
  inventaría información que no tenemos.
- Un cliente con cuentas en dos países (hoy sólo Omar Graterol, UY+VE) aparece
  en los dos chips: esconderlo en uno haría que desapareciera al filtrar por el
  otro.

## Verificación

- `npx tsc --noEmit` en `frontend/`: sin errores.
- Contra los datos reales (`GET /clientes`, 2026-10-30), con las mismas reglas:
  24 residencial, 24 itinerante, 6 mixto, 3 en espera (suma 57); países por
  cliente: VE 42, UY 10, CO 3, PE 1, CL 1, AR 1 (Omar suma en VE y UY).
- En el panel real (`localhost:3000`, Chrome) se ven las dos filas con esos
  mismos números: `VE (42) UY (10) CO (3) PE (1) CL (1) AR (1)` y
  `Residencial (24) Itinerante (24) Mixto (6) En espera / pausadas (3)`.
- No se pudo confirmar el clic de cada chip (el equipo estaba en uso): el filtrado
  es el mismo patrón de los chips de estado, ya verificados.

## Límites conocidos

- Los contadores de país cuentan clientes que **tienen** ese país, así que un
  cliente con cuentas en dos países suma en dos chips (VE+UY = 42+10 > 57).
- El tipo es por cliente, no por cuenta: no se puede ver "sólo la cuenta
  itinerante" de un cliente mixto sin partir la tarjeta.
