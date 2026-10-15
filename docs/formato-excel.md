# Formato del Excel fuente

Documento de referencia sobre la estructura del Excel semanal que alimenta la app.
Extraído de `Planning de PickUp_ADR (2).xlsx` recibido el 2026-04-23.

## Metadatos

- **Archivo origen:** `Planning de PickUpADR.xlsx` (exportado desde el PMS del hotel).
- **Hoja:** `Planning de PickUpADR`
- **Tabla estructurada:** `Table1` (rango A1:ES185).
- **Filas de datos:** 184 (una por día de estancia).
- **Columnas:** 149.
- **Formato de fechas:** serial date de Excel (p. ej. `46135` → `2026-04-16`).

## Semántica general

- **Fecha Inicial / Fecha Final (A, B):** rango del snapshot (en el ejemplo, 2026-04-16 → 2026-10-16 ≈ 6 meses).
- **Tipo de Filtro / Filtro Código (C, D):** segmentación aplicada al snapshot (en el ejemplo, `Allotment`).
- **Fecha / Día (E, F):** fecha de estancia y nombre del día en español.
- Cada fila es la foto **on-the-books** de esa fecha de estancia a la fecha del snapshot.

## Bloques de columnas

### 1) Ocupación base (G–O)
Reservas, Reservas año anterior, Diferencia Reservas, Libres, %Ocup.Habitaciones,
Bloqueadas, Pax, Pax año anterior, Dif. Pax.

### 2) Pickup por ventana (P–W)
Pickup día anterior, Pickup semana anterior, Pickup 2 semanas anteriores,
Pickup saldo acum. 4 semanas (cada uno con su % correspondiente).

### 3) Producción / ADR / RevPAR por segmento

Para cada segmento se repite el tripleta **Producción**, **ADR**, **RevPAR**,
con comparativa año anterior y diferencia:

- **Alojamiento** (X–AF)
- **Pensión** (AG–AO)
- **F&B** (AP–AX)
- **Otros** (AY–BG)
- **Total** (BH–BP)

### 4) Importe medio por Pax (BQ–BS)
Importe Med. Pax, Importe Med. Pax año ant., Dif. Importe Med.

### 5) Bloque de medias agregadas (BT–EO)
Repetición de los mismos campos del bloque 1–4 pero con columnas `Media …`
(promedios sobre el rango seleccionado) y desgloses adicionales de personas:
- Personas excl. bebés (CD–CJ)
- Bebés (CK–CQ)

## Gráficos de referencia (del Excel `PLANNING PICKUP-ADR NEPTUNO.xlsx`)

El archivo del hotel con visualizaciones define 4 gráficos que sirven de guía:

1. **Libres CY vs LY** — área, diario.
2. **Reservas CY vs LY** — barras, por mes.
3. **Pickup por ventana** — área con series `día`, `semana`, `2 semanas`. **Es el gráfico clave.**
4. **Resumen por mes** — barras, 12 meses.

## Observaciones

- Hay nombres de columna duplicados con sufijo `1` (p. ej. `Reservas1`, `ADR Total1`). Indican el bloque de medias, no error.
- El PMS entrega todos los cálculos de pickup ya hechos: la app **no necesita recalcular** pickup, solo archivar y comparar entre snapshots.
- Si cambia el formato de exportación del PMS, este documento debe actualizarse.
