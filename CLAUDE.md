# Aparthotel Neptuno Costa Adeje — Revenue Management App

> Documento vivo. Se actualiza en cada decisión o cambio de alcance.
> Última actualización: 2026-10-15.

## Objetivo

App que centraliza los Excel semanales de pickup/ADR del
**Aparthotel Neptuno Costa Adeje (Tenerife Sur, 95 unidades)**, los acumula
en un histórico y genera dashboards para el seguimiento de ocupación, ADR,
RevPAR, pickup por ventana y comparativas con el año anterior.

> Es la versión paralela del proyecto `revenue-neptuno` (Finca Vistabonita,
> 17 hab). Mismo código, paleta de marca diferente, capacidad 95, puerto 8502
> (8501 lo usa Vistabonita) y entry point `NeptunoCostaAdeje.bat`.

## Alcance actual (v0)

- Ingesta de **un Excel semanal** (los lunes) llamado `Planning de PickUpADR`.
- El Excel trae **un snapshot** con 184 días de estancia (≈ 6 meses) y 149 columnas
  con todos los KPIs del hotel ya calculados por el PMS.
- Archivado automático en `Excel-Lunes/<mes>/<semana>/`.
- Acumulación de snapshots en un Excel histórico maestro (`data/historico/`).
- Dashboards con los 4 gráficos de referencia (ver [docs/formato-excel.md](docs/formato-excel.md)).

## Fuera de alcance

- Integración directa con PMS / channel manager.
- Multi-usuario / multi-hotel.
- Despliegue en nube.
- Pricing dinámico / forecasting automático.

## Datos de entrada

Ver [docs/formato-excel.md](docs/formato-excel.md) para el esquema completo.
Resumen:

- **Fuente:** Excel exportado del PMS del hotel.
- **Frecuencia:** semanal (lunes).
- **Contenido:** un snapshot con una fila por día de estancia (6 meses hacia adelante)
  y 149 columnas con: ocupación, pickup a 1/7/14/28 días, ADR, RevPAR y producción
  por segmento (Alojamiento, Pensión, F&B, Otros, Total), más comparativa año anterior.
- **Formato fechas:** serial date de Excel.

## Histórico

- **Formato:** Excel maestro acumulado en `data/historico/historico_neptuno.xlsx`.
- **Granularidad mínima:** una fila por (fecha_snapshot, fecha_estancia).
- **Justificación:** el usuario trabaja cómodo con Excel y quiere inspeccionar el
  histórico directamente con su herramienta habitual. Se descartó SQLite por esto.

## Stack técnico (propuesta)

| Capa | Elección | Por qué |
|---|---|---|
| Lenguaje | Python 3.11+ | Estándar para trabajar con Excel y análisis de datos, mucha documentación. |
| Lectura/escritura Excel | pandas + openpyxl | Combinación probada para `.xlsx`. |
| UI / dashboards | Streamlit | Se escribe como un script Python y corre local en el navegador. |
| Gráficos | Plotly | Interactivos, integración nativa con Streamlit. |
| Config | PyYAML | Configuración legible en `config/settings.yaml`. |
| Entorno | uv o venv | Aislar dependencias del Python del sistema. |

Pendiente de confirmar `uv` vs `venv`.

## Estructura de carpetas

```
revenue-neptuno/
├── CLAUDE.md              ← este archivo
├── README.md
├── app.py                 Punto de entrada (placeholder)
├── requirements.txt
├── .gitignore
├── Excel-Lunes/           Excel semanales archivados por mes/semana
│   └── 2026-04-Abril/
│       └── Semana-01_2026-04-27/
├── data/
│   ├── raw/               Buzón de Excel pendientes de procesar
│   ├── processed/         Excel transformados intermedios
│   └── historico/
│       └── historico_neptuno.xlsx   (se crea en la primera carga)
├── src/
│   ├── ingest/            Lectura y validación del Excel semanal
│   ├── storage/           Lectura/escritura del Excel histórico
│   ├── analysis/          Cálculos adicionales y KPIs
│   └── ui/                Componentes de dashboard
├── config/
│   └── settings.yaml
└── docs/
    └── formato-excel.md
```

## Flujo de trabajo

**Setup inicial (una sola vez):**
- `powershell -File scripts\crear_accesos_directos.ps1` → crea en el escritorio
  los accesos directos "Neptuno Costa Adeje" y "BUZON Neptuno Costa Adeje".

**Cada lunes:**
1. Arrastras el Excel `Planning de PickUpADR (X).xlsx` al acceso directo
   **"BUZON Neptuno Costa Adeje"** del escritorio (apunta a `Excel-Lunes/BUZON/`).
2. Doble clic en el acceso directo **"Neptuno Costa Adeje"** del escritorio.
3. `NeptunoCostaAdeje.bat` ejecuta `scripts/procesar_buzon.py` que:
   - Valida el esquema (149 cols, Allotment, **95 hab**).
   - Lo añade al histórico maestro `data/historico/historico_costadeje.xlsx`
     (dedup por `(Snapshot, Fecha)`).
   - Lo mueve a `Excel-Lunes/<YYYY-MM-Mes>/Semana-XX_<fecha-snapshot>/`.
   - Excels inválidos se quedan en BUZON con motivo visible.
4. A continuación abre el dashboard en `http://localhost:8502` automáticamente.

> **Puerto 8502** (no 8501) para que pueda convivir con el dashboard de
> Vistabonita en paralelo.

## Decisiones pendientes

- [ ] ¿Importar también snapshots previos al 2026-04-23 si existen, o empezar
      el histórico desde la primera semana nueva?
- [ ] Patrón del nombre del archivo Excel para reconocerlo automáticamente.
- [ ] Formato de exportación de informes: ¿PDF, Excel, solo pantalla?
- [ ] Confirmar HEX exactos del logo Vistabonita (paleta actual deducida de la web).

## Notas de assets

- `assets/logo.png` — logo oficial descargado de neptunocostadeje.com.
- `assets/hero_piscina.jpg` — foto de la piscina principal usada en la cabecera del dashboard.
  Pesa 668 KB, se sirve embebida en base64 (carga local, sin pegar a internet).

## Decisiones tomadas

- **2026-04-23** — El histórico se guarda como Excel maestro, no SQLite. _Razón:_
  el usuario quiere poder abrir y revisar el histórico directamente con Excel.
- **2026-04-23** — `Excel-Lunes/` se mantiene en la raíz del proyecto (no dentro
  de `data/raw/`). _Razón:_ ya estaba creada con la estructura por mes/semana
  y es la carpeta a la que el usuario arrastra los Excel cada lunes.
- **2026-04-23** — Capacidad del hotel: **17 habitaciones**. Verificado con los
  datos del Excel (3 reservas + 14 libres = 17, coincide con `%Ocup = 17.65%`).
- **2026-04-23** — El formato del Excel fuente será **siempre** el del archivo
  `Planning de PickUp_ADR (2).xlsx`: hoja `Planning de PickUpADR`, tabla `Table1`
  con 149 columnas, filtrado por `Tipo de Filtro = Allotment`. La ingesta puede
  validar rígidamente el esquema sin preocuparse por variantes.
- **2026-04-23** — Stack instalado y validado:
  - Python 3.12.10 (vía `winget install Python.Python.3.12` en scope user).
  - Entorno virtual en `.venv/` (decisión: **venv**, no `uv`; más estándar y
    con cero dependencias externas).
  - Librerías: pandas 3.0.2, openpyxl 3.1.5, streamlit 1.56.0, plotly 6.7.0, pyyaml 6.0.3.
  - Confirmado end-to-end leyendo el Excel: 184 filas × 149 columnas, rango
    2026-04-23 → 2026-10-23, `Tipo de Filtro=Allotment`, 3 reservas + 14 libres = 17 hab.
  - Pandas interpreta las fechas automáticamente (no hacen falta conversiones
    de serial date).
  - La consola de Windows (CP1252) **no soporta caracteres Unicode**. Los scripts
    que impriman deben usar `PYTHONIOENCODING=utf-8` o evitar símbolos tipo `→`/`%`.
- **2026-04-25** — Pipeline de ingesta + histórico operativo:
  - `src/ingest/excel_reader.py` valida (149 cols, `Tipo de Filtro=Allotment`,
    Reservas+Libres=17) y añade `Snapshot` + `Archivo Origen`.
  - `src/storage/historico.py` deduplica por `(Snapshot, Fecha)` y reescribe
    `data/historico/historico_neptuno.xlsx` (hoja `Historico`).
  - CLI: `python scripts/cargar_semana.py "ruta/al/Excel.xlsx"`.
- **2026-04-25** — Stack del dashboard Streamlit + Plotly montado:
  - `app.py` arranca con `streamlit run app.py` (config en `.streamlit/config.toml`).
  - Lanzador con doble clic: `scripts/abrir_dashboard.bat`.
  - `src/analysis/series.py` produce los DataFrames; `src/ui/graficos.py` los
    pinta; `src/ui/tema.py` define paleta + plantilla Plotly.
- **2026-04-25** — Marca **Finca Vistabonita / Hotel Neptuno** (verde botánico
  `#3D6E47` + azul océano `#2E5C7E` + dorado arena `#C9A66B`, Inter font, deducido
  del logo verde+azul de finca-vistabonita.com). Verde = CY/positivo,
  rojo terracota = LY/negativo, gris = referencia.
- **2026-04-25** — Estructura del dashboard (orden definitivo aprobado):
  1. KPIs cabecera (8 métricas CY vs LY).
  2. 🚨 Disponibilidad próximos 30 días (línea con marcadores por umbral
     0-4/5-8/9-11/12-17 libres + sombras de finde).
  3. 📈 Pickup neto por mes (barras + selector ventana en sidebar).
  4. 💰 Producción mensual CY vs LY.
  5. 🛏️ **Combinado** Libres CY/LY + Pickup diario por mes (un único plot
     con doble eje Y; default "Horizonte completo" muestra solo libres anual,
     al elegir mes muestra ambos juntos con sombras de finde).
  6. 🌊 Pickup por ventana (área spline 3 series).
  7. 💶 ADR diario (línea CY + LY punteada + media).
  8. 📅 Reservas mensuales CY vs LY.
  9. 📊 Tabla mensual estilizada (Producción CY en negrita, Δ% en verde/rojo).
- **2026-04-25** — Eje X de gráficos categóricos por día: `DD/MM` en negrita
  solo en día 1 y cambios de mes; resto solo `DD`. Inicial del día semana
  (L M X J V S D) en gris pequeño debajo. Lunes en negrita. Sombras azules
  verticales (`AZUL_OCEANO` con opacidad 0.07) en bloques Vie-Sáb-Dom.
- **2026-04-25** — `add_vrect` no funciona en `make_subplots` con
  `secondary_y=True`; usar `add_shape(type="rect", xref="x", yref="y domain")`.
- **2026-04-29** — Marca **Aparthotel Neptuno Costa Adeje** (95 unidades, Tenerife Sur).
  Paleta extraída del logo de neptunocostadeje.com:
  - Azul cobalto `#240B80` (primario, color literal del logo).
  - Turquesa piscina `#0EA5C7` (secundario, agua de las piscinas).
  - Dorado sol `#F4B860` y coral `#E07856` (acentos cálidos canarios).
  - Crema arena `#F5EFE6` (fondo).
  Logo + foto hero (piscina) embebidos en base64 en la cabecera del dashboard.
  Banner de marca con gradiente azul cobalto → turquesa.
- **2026-04-29** — Umbrales de criticidad de libres (sobre 95 unidades):
  Excelente 0-19 · Bien 20-38 · Atención 39-60 · Crítico 61-95.
  (Vistabonita usaba 0-4/5-8/9-11/12-17 sobre 17 habitaciones).
- **2026-04-28** — Workflow semanal de "un gesto":
  - `Excel-Lunes/BUZON/` es la única drop zone. El usuario suelta el Excel ahí
    (vía acceso directo "BUZON Neptuno Costa Adeje" en el escritorio).
  - `scripts/procesar_buzon.py` recorre el buzón, valida cada Excel, añade al
    histórico `historico_costadeje.xlsx` y archiva en
    `Excel-Lunes/<mes>/Semana-XX_<fecha>/`. Si el
    formato es inválido, deja el archivo en BUZON y muestra el motivo.
  - `NeptunoCostaAdeje.bat` (raíz) procesa el buzón y arranca Streamlit en
    el puerto 8502 con `start "" http://localhost:8502` que abre el navegador
    automáticamente.
  - `scripts/crear_accesos_directos.ps1` crea los dos `.lnk` en el escritorio
    (Neptuno Costa Adeje + BUZON Neptuno Costa Adeje) con iconos del shell.
  - El nombre de mes/semana se deriva de la fecha del **snapshot** del Excel
    (no del sistema), robusto si se procesa con retraso. Semana ISO.
  - Entry point único: `NeptunoCostaAdeje.bat`. El `scripts/abrir_dashboard.bat`
    queda como lanzador "solo dashboard" sin procesar buzón (también en :8502).

- **2026-10-15** — **Apartamentos bloqueados + despliegue en la nube.** Portado desde
  `revenue-finca`, que iba por delante en estas dos cosas.
  - **Invariante real:** `Reservas + Libres + Bloqueadas = 95`, no `Reservas + Libres = 95`.
    Verificado en las **3.496 filas** del histórico, sin excepción. Antes se validaba
    solo `Reservas + Libres` y **solo en la primera fila**, así que un bloqueo el lunes
    rechazaba el Excel entero, y el día 30/04/2026 con **5 unidades bloqueadas** entró
    sin marcar. Ahora sale marcado retroactivamente.
  - `src/inventario.py` (nuevo) es la fuente única del 95 y de la aritmética.
  - Validación sobre **todas** las filas, con tolerancia ±2 (93–97). Sigue rechazando
    el Excel de la Finca Vistabonita (17), comprobado.
  - **Nube:** Streamlit Community Cloud + repo privado `revenue-neptuno-datos` como
    almacén (`src/storage/almacen.py`). **Dos repos separados**, porque Streamlit
    reinicia la app en cada push al repo desde el que publica.
  - El histórico (3.496 filas) supera el límite de 1 MB de lectura de la API de GitHub:
    hay que leerlo con `Accept: application/vnd.github.raw` o llega **vacío sin error**.
  - `src/ingest/pipeline.py` (nuevo) es la única ruta de ingesta, compartida por la
    subida web y el buzón local.
  - **El .gitignore tiene una excepción propia**: `assets/logo.png` y
    `assets/hero_piscina.jpg` SÍ se versionan, porque `app.py` las incrusta en la
    cabecera. En `revenue-finca` las imágenes se ignoran; aquí no.

- **2026-10-15** — **Este proyecto y `revenue-finca` comparten código pero divergen.**
  `src/ui/tema.py` de aquí define alias (`VERDE_BOTANICO = AZUL_COBALTO`,
  `DORADO_ARENA = DORADO_SOL`…) para que los módulos compartidos funcionen sin tocar.
  Pero **no son copias idénticas**: aquí hay un eje Y de % de ocupación y la producción
  de alojamiento que allí no están, y `app.py` tiene logo y cabecera con imagen.
  **Al portar algo entre proyectos, edita quirúrgicamente; no copies ficheros enteros.**

## Gráficos de referencia

Los 4 gráficos del Excel `PLANNING PICKUP-ADR NEPTUNO.xlsx` definen el v0
del dashboard:

1. **Ocupación CY vs LY** — área diaria de habitaciones libres actual vs año anterior.
2. **Reservas CY vs LY** — barras por mes.
3. **Pickup por ventana** — área con series día / semana / 2 semanas. **Gráfico clave.**
4. **Resumen mensual** — barras por mes (12 meses).

## Glosario

- **Pickup:** reservas netas captadas en una ventana (1/7/14/28 días).
- **On-the-books:** reservas confirmadas en el snapshot.
- **CY / LY:** Current Year / Last Year.
- **ADR:** Average Daily Rate — precio medio por habitación ocupada.
- **RevPAR:** Revenue Per Available Room.
- **Pax:** personas alojadas.
